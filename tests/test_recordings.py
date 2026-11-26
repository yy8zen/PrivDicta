import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from privdicta.recordings import RecordingStore, resample

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import benchmark_accuracy as b  # noqa: E402


def test_save_writes_wav_and_index(tmp_path):
    store = RecordingStore(tmp_path)
    audio = (np.sin(np.arange(16000) / 5) * 0.3).astype(np.float32)
    now = datetime(2026, 11, 26, 22, 7, 25)
    first = store.save(audio, 16000, "今日は晴れです。", now)
    second = store.save(audio, 16000, "二回目", now)  # 同じ秒でも上書きしない
    assert first.name == "20261126-220725.wav"
    assert second.name == "20261126-220725-2.wav"
    index = json.loads((tmp_path / "recognized.json").read_text(encoding="utf-8"))
    assert index == {first.name: "今日は晴れです。", second.name: "二回目"}
    # 精度の測定スクリプトでそのまま読める
    assert np.allclose(b.load_wav(first), audio, atol=1e-4)


def test_resample_to_16k():
    audio = np.zeros(48000, dtype=np.float32)
    assert len(resample(audio, 48000)) == 16000
    assert resample(audio, 16000) is audio


def test_broken_index_is_rebuilt(tmp_path):
    (tmp_path / "recognized.json").write_text("{壊れた", encoding="utf-8")
    path = RecordingStore(tmp_path).save(np.zeros(160, dtype=np.float32), 16000, "a")
    assert json.loads((tmp_path / "recognized.json").read_text(encoding="utf-8")) == {path.name: "a"}
