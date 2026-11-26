import numpy as np
import pytest

from privdicta.mic_permission import SilenceDetector, help_text, windows_access_denied
from privdicta.session import IDLE, RECORDING
from tests.test_session import make

CONSENT = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"


@pytest.mark.parametrize("values, denied", [
    ({}, False),  # 設定が見つからない（古い Windows など）
    ({("HKCU", CONSENT): "Allow", ("HKCU", CONSENT + r"\NonPackaged"): "Allow"}, False),
    ({("HKLM", CONSENT): "Deny"}, True),  # PC 全体でオフ
    ({("HKCU", CONSENT): "Deny"}, True),  # このユーザーでオフ
    ({("HKCU", CONSENT): "Allow", ("HKCU", CONSENT + r"\NonPackaged"): "Deny"}, True),  # デスクトップ アプリだけオフ
])
def test_windows_access_denied(values, denied):
    assert windows_access_denied(lambda root, path: values.get((root, path))) is denied


def test_windows_access_denied_ignores_read_errors():
    def broken(root, path):
        raise OSError("読めない")

    assert windows_access_denied(broken) is False


def test_silence_detector_reports_digital_silence_once():
    d = SilenceDetector(seconds=1.0)
    block = np.zeros(1600, dtype=np.float32)  # 16kHz で0.1秒
    results = [d.feed(block, 16000) for _ in range(15)]
    assert results.count(True) == 1
    assert results.index(True) == 9  # 1秒たった時点


def test_silence_detector_ignores_real_microphone_noise():
    d = SilenceDetector(seconds=1.0)
    rng = np.random.default_rng(0)
    noise = (rng.standard_normal(1600) * 1e-4).astype(np.float32)  # 静かな部屋の雑音程度
    assert not any(d.feed(noise, 16000) for _ in range(20))


def test_help_text_mentions_settings():
    assert "マイク" in help_text(True)
    assert "ミュート" in help_text(False)


def test_session_blocks_start_when_permission_denied(qapp):
    session, engine, _, _, _, sounds = make()
    blocked = []
    session.mic_blocked.connect(blocked.append)
    session.mic_denied = lambda: True
    engine.loaded.emit()
    session.toggle()
    assert session.state == IDLE
    assert engine.calls == []  # マイクを開かない
    assert blocked == [True]
    assert sounds == ["error"]


def test_session_stops_when_microphone_is_silent(qapp):
    session, engine, _, _, _, _ = make()
    blocked = []
    session.mic_blocked.connect(blocked.append)
    engine.loaded.emit()
    session.start()
    assert session.state == RECORDING
    engine.mic_silent.emit()
    assert blocked == [False]
    assert ("stop",) in engine.calls
