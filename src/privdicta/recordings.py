"""録音と認識結果を PC の中に保存する（要件 R2.10）。

認識の精度を、例文ではなく実際の使い方で測るためのもの。既定では保存しない。
保存したものはどこにも送らない。scripts/benchmark_accuracy.py で、エンジンや設定を比べるのに使う。

保存先のフォルダには、録音ごとの WAV（16kHz、モノラル）と、認識結果をまとめた recognized.json を置く。
recognized.json をコピーして references.json という名前にし、誤っている文を正しい文に直すと、
benchmark_accuracy.py でそのフォルダを測れる。
"""

from __future__ import annotations

import json
import logging
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from privdicta.platform_info import config_dir

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
RECOGNIZED = "recognized.json"


def default_dir() -> Path:
    return config_dir() / "recordings"


class RecordingStore:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or default_dir()

    def save(self, audio: np.ndarray, rate: int, text: str, now: datetime | None = None) -> Path:
        """録音を WAV で保存し、認識結果を recognized.json に足す。保存した WAV の場所を返す。"""
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        path = self.directory / f"{stamp}.wav"
        n = 1
        while path.exists():  # 同じ秒に2回録音した場合
            n += 1
            path = self.directory / f"{stamp}-{n}.wav"
        write_wav(path, resample(audio, rate))

        index = self.directory / RECOGNIZED
        try:
            entries = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {}
        except (OSError, ValueError):
            log.warning("%s を読めないため、作り直します", index)
            entries = {}
        entries[path.name] = text
        tmp = index.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(index)
        return path


def resample(audio: np.ndarray, rate: int) -> np.ndarray:
    """16kHz にそろえる。マイクが 16kHz を受け付けず、別のレートで録った場合に使う。"""
    if rate == SAMPLE_RATE or len(audio) == 0:
        return audio
    n = int(len(audio) * SAMPLE_RATE / rate)
    return np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
