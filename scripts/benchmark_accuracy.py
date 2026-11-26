"""認識の設定ごとに、文字の誤り率と、録音を終えてから結果が出るまでの時間を測る（要件 R2.9）。

    python scripts/benchmark_accuracy.py                 # 例文を読み上げて録音し、測る
    python scripts/benchmark_accuracy.py recordings/benchmark-20261126-101500   # 前に録音した例文で測り直す

録音は recordings/benchmark-<日時>/ に WAV と正解の文（references.json）で保存する。
同じ録音で、設定を変えて何度でも測り直せる。モデルが models/ になければダウンロードする。

比べる設定
  A  今までの設定（max_tokens_per_second が既定値の 6.5）
  B  max_tokens_per_second=13.0（アプリの今の設定）
  C  B に加えて vad_threshold=0.3（話の区切りを長めにとる）
  D  B の設定で、区切らずに録音全体を一度に認識する

待ち時間の測り方
  A〜C は、アプリと同じく音声を少しずつ渡して認識し、録音の終わり（stop）からの時間を測る。
  音声は実際の速さより速く渡すので、「処理時間/音声の長さ」も出す。これが 1 を超える設定は、
  実際に話している間に処理が追いつかず、録音を終えてからの待ち時間が表の値より長くなる。
  D は、録音全体を認識するのにかかった時間を、そのまま録音を終えてからの待ち時間とする。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import unicodedata
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_model import fetch  # noqa: E402
from privdicta.engine import BLOCK_FRAMES, MODEL_DIRS, SAMPLE_RATE, TRANSCRIBER_OPTIONS  # noqa: E402
from privdicta.text import normalize_spaces  # noqa: E402

# 短い文から長い文まで。長さによって待ち時間がどう変わるかも見るため
SENTENCES = [
    "今日は天気がいいので、午後から散歩に出かけます。",
    "明日の会議の資料を、今日の夕方までに作成してください。",
    "新しい機能を追加したので、動作確認をお願いします。",
    "この件については、来週の打ち合わせで改めて相談しましょう。",
    "音声入力を使うと、キーボードで打つよりも速く文章を書けることがあります。",
    "先月から始めたプロジェクトは順調に進んでいますが、来月の締め切りに間に合わせるためには、"
    "もう一人担当者を増やす必要があるかもしれません。",
    "お客様から問い合わせがあった件について、担当の部署に確認したところ、来週の水曜日までには"
    "回答できるとのことでした。決まり次第、改めてご連絡いたします。",
]


@dataclass
class Setting:
    key: str
    label: str
    options: dict
    whole: bool  # True なら録音全体を一度に認識する


SETTINGS = [
    Setting("A", "今までの設定（6.5）", {}, False),
    Setting("B", "max_tokens_per_second=13.0", dict(TRANSCRIBER_OPTIONS), False),
    Setting("C", "13.0 + vad_threshold=0.3", {**TRANSCRIBER_OPTIONS, "vad_threshold": "0.3"}, False),
    Setting("D", "13.0 + 録音全体を一度に認識",
            {**TRANSCRIBER_OPTIONS, "vad_threshold": "0", "vad_max_segment_duration": "60"}, True),
]


# ---- 録音 ----

def record_until_enter(device) -> np.ndarray:
    import sounddevice as sd

    chunks: list[np.ndarray] = []
    lock = threading.Lock()

    def callback(indata, frames, time_info, status):
        with lock:
            chunks.append(indata[:, 0].copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        device=device, callback=callback):
        input("  録音中…（読み終えたら Enter）")
    with lock:
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


def record_all(out_dir: Path, device_name: str) -> None:
    from privdicta.engine import find_input_device

    device = find_input_device(device_name)
    out_dir.mkdir(parents=True)
    refs = {}
    print(f"{len(SENTENCES)} 個の文を読み上げてもらいます。普段の話し方で読んでください。\n")
    for i, sentence in enumerate(SENTENCES, 1):
        print(f"[{i}/{len(SENTENCES)}] {sentence}")
        input("  Enter で録音を始めます")
        audio = record_until_enter(device)
        name = f"{i:02d}.wav"
        save_wav(out_dir / name, audio)
        refs[name] = sentence
        print(f"  {len(audio) / SAMPLE_RATE:.1f}秒 録音しました\n")
    (out_dir / "references.json").write_text(json.dumps(refs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"録音を保存しました: {out_dir}\n")


def save_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return pcm.astype(np.float32) / 32768


# ---- 評価 ----

_DROP = re.compile(r"[\s、。，．,.！？!?「」『』（）()・…ー〜~]")


def normalize_for_cer(text: str) -> str:
    """句読点と空白を除き、全角・半角をそろえて比べる。句読点の有無は誤りに数えない。"""
    return _DROP.sub("", unicodedata.normalize("NFKC", text))


def cer(reference: str, hypothesis: str) -> float:
    """文字の誤り率（置換・挿入・脱落の数 ÷ 正解の文字数）。"""
    ref, hyp = normalize_for_cer(reference), normalize_for_cer(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def run_setting(setting: Setting, model_path: Path, arch_name: str, audio: np.ndarray) -> tuple[str, float, float]:
    """(認識結果, 録音を終えてからの秒数, 処理時間/音声の長さ) を返す。"""
    from moonshine_voice import ModelArch, Transcriber

    transcriber = Transcriber(str(model_path), ModelArch[arch_name], options=dict(setting.options))
    length = len(audio) / SAMPLE_RATE
    try:
        if setting.whole:
            t0 = time.monotonic()
            transcript = transcriber.transcribe_without_streaming(audio.tolist(), SAMPLE_RATE)
            latency = time.monotonic() - t0
            text = "".join(line.text for line in transcript.lines if line.text)
            return normalize_spaces(text), latency, latency / max(length, 1e-6)
        lines: dict = {}
        stream = transcriber.create_stream()
        stream.add_listener(lambda e: getattr(e, "line", None) and lines.__setitem__(e.line.line_id, e.line.text))
        stream.start()
        t0 = time.monotonic()
        for i in range(0, len(audio), BLOCK_FRAMES):
            stream.add_audio(audio[i:i + BLOCK_FRAMES].tolist(), SAMPLE_RATE)
        feed = time.monotonic() - t0
        t1 = time.monotonic()
        stream.stop()
        latency = time.monotonic() - t1
        stream.close()
        text = "".join(t for t in lines.values() if t)
        return normalize_spaces(text), latency, (feed + latency) / max(length, 1e-6)
    finally:
        transcriber.close()


def evaluate(rec_dir: Path, arch_key: str, keys: str) -> None:
    refs = json.loads((rec_dir / "references.json").read_text(encoding="utf-8"))
    model_path = fetch(arch_key, force=False)
    arch_name = MODEL_DIRS[arch_key][1]
    settings = [s for s in SETTINGS if s.key in keys]
    summary = {s.key: {"errors": 0.0, "chars": 0, "latencies": [], "rtf": []} for s in settings}

    for name, reference in refs.items():
        audio = load_wav(rec_dir / name)
        length = len(audio) / SAMPLE_RATE
        print(f"■ {name}（{length:.1f}秒）正解：{reference}")
        n = len(normalize_for_cer(reference))
        for s in settings:
            text, latency, rtf = run_setting(s, model_path, arch_name, audio)
            e = cer(reference, text)
            summary[s.key]["errors"] += e * n
            summary[s.key]["chars"] += n
            summary[s.key]["latencies"].append((length, latency))
            summary[s.key]["rtf"].append(rtf)
            print(f"  {s.key} 誤り率 {e * 100:5.1f}%  待ち {latency:4.2f}秒  処理/長さ {rtf:4.2f}  {text}")
        print()

    print("=" * 60)
    print(f"モデル：{arch_key}　録音：{rec_dir}")
    print("設定                                 誤り率   待ち時間（最大）  処理/長さ（最大）")
    for s in settings:
        r = summary[s.key]
        rate = r["errors"] / max(r["chars"], 1) * 100
        worst = max(lat for _, lat in r["latencies"])
        print(f"{s.key} {s.label:<32} {rate:5.1f}%   {worst:5.2f}秒          {max(r['rtf']):4.2f}")
    d = summary.get("D")
    if d:
        ok = [length for length, lat in d["latencies"] if lat <= 1.0]
        print(f"\nD で待ち時間が1秒以内に収まった最も長い録音：{max(ok):.1f}秒" if ok
              else "\nD はどの録音でも待ち時間が1秒を超えました")


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("recordings", nargs="?", type=Path, help="前に録音したフォルダ。省略すると録音から始める")
    parser.add_argument("--model", default="base", help=f"モデル（{', '.join(MODEL_DIRS)}）")
    parser.add_argument("--settings", default="ABCD", help="比べる設定（例：BD）")
    parser.add_argument("--device", default="", help="マイクのデバイス名（一部でも可）")
    args = parser.parse_args()

    rec_dir = args.recordings
    if rec_dir is None:
        rec_dir = ROOT / "recordings" / f"benchmark-{datetime.now():%Y%m%d-%H%M%S}"
        record_all(rec_dir, args.device)
    evaluate(rec_dir, args.model, args.settings.upper())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
