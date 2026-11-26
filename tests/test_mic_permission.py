import numpy as np

from privdicta.mic_permission import SilenceDetector, help_text
from privdicta.session import IDLE, RECORDING
from tests.test_session import make


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


def test_help_text():
    assert "音が届いていません" in help_text(None)
    text = help_text("Error opening InputStream")
    assert "マイクを使えませんでした" in text and "Error opening InputStream" in text


def test_session_shows_help_when_microphone_cannot_open(qapp):
    session, engine, _, _, _, sounds = make()
    blocked = []
    session.mic_blocked.connect(blocked.append)
    engine.loaded.emit()
    engine.fail_start = True
    session.toggle()
    assert session.state == IDLE
    assert blocked == ["no mic"]
    assert sounds == ["error"]


def test_session_stops_when_microphone_is_silent(qapp):
    session, engine, _, _, _, _ = make()
    blocked = []
    session.mic_blocked.connect(blocked.append)
    engine.loaded.emit()
    session.start()
    assert session.state == RECORDING
    engine.mic_silent.emit()
    assert blocked == [None]
    assert ("stop",) in engine.calls
