from privdicta.mic_permission import help_text
from privdicta.session import IDLE
from tests.test_session import make


def test_help_text():
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
