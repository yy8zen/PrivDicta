import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import benchmark_accuracy as b  # noqa: E402


@pytest.mark.parametrize("ref, hyp, expected", [
    ("今日は晴れです。", "今日は晴れです", 0.0),        # 句読点の有無は誤りにしない
    ("今日は晴れです。", "今日は 晴れ です。", 0.0),    # 空白も誤りにしない
    ("資料を作成してください", "資料を作成して", 4 / 11),  # 脱落4文字（ください）
    ("機能を追加する", "昨日を追加する", 2 / 7),         # 置換2文字
    ("確認してください", "確認してくださいください", 4 / 8),  # 挿入4文字
    ("ＡＢＣ１２３", "ABC123", 0.0),                      # 全角と半角は同じとみなす
])
def test_cer(ref, hyp, expected):
    assert b.cer(ref, hyp) == pytest.approx(expected)


def test_wav_round_trip(tmp_path):
    audio = (np.sin(np.arange(1600) / 7) * 0.5).astype(np.float32)
    b.save_wav(tmp_path / "a.wav", audio)
    assert np.allclose(b.load_wav(tmp_path / "a.wav"), audio, atol=1e-4)


def test_settings_use_app_options():
    from privdicta.engine import TRANSCRIBER_OPTIONS

    by_key = {s.key: s for s in b.SETTINGS}
    assert by_key["A"].options == {}
    assert by_key["B"].options == TRANSCRIBER_OPTIONS
    assert by_key["D"].whole and by_key["D"].options["vad_threshold"] == "0"
