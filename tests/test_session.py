from PySide6.QtCore import QObject, Signal

from privdicta.session import FINISHING, IDLE, LOADING, RECORDING, Session
from tests.conftest import process_events


class FakeEngine(QObject):
    loaded = Signal()
    load_failed = Signal(str)
    line_changed = Signal(object, str)
    line_completed = Signal(object, str)
    activity = Signal()
    finished = Signal()
    failed = Signal(str)
    mic_silent = Signal()

    def __init__(self):
        super().__init__()
        self.calls = []
        self.fail_start = False

    def start(self, device):
        if self.fail_start:
            raise OSError("no mic")
        self.calls.append(("start", device))

    def stop(self):
        self.calls.append(("stop",))


class FakeOverlay:
    def __init__(self):
        self.events = []

    def show_recording(self): self.events.append("show")
    def show_finishing(self): self.events.append("finishing")
    def set_partial(self, text): self.events.append(("partial", text))
    def commit(self, text): self.events.append(("commit", text))
    def hide(self): self.events.append("hide")


class FakeInserter:
    def __init__(self, live):
        self.live = live
        self.texts = []

    def insert(self, text):
        self.texts.append(text)


def make(live=False, replace=None):
    engine = FakeEngine()
    overlay = FakeOverlay()
    notes, sounds = [], []
    session = Session(engine, overlay, lambda m, e: notes.append(m), sounds.append)
    inserter = FakeInserter(live)
    session.configure(inserter, replace or {}, "mic", True, 60)
    return session, engine, overlay, inserter, notes, sounds


def test_toggle_while_loading_notifies(qapp):
    session, engine, *_, notes, _ = make()
    session.toggle()
    assert session.state == LOADING
    assert engine.calls == []
    assert "読み込んで" in notes[0]


def test_clipboard_mode_inserts_once_at_end(qapp):
    session, engine, overlay, inserter, _, sounds = make(replace={"でぃすこーど": "Discord"})
    engine.loaded.emit()
    session.toggle()
    assert session.state == RECORDING
    assert engine.calls == [("start", "mic")]
    engine.line_changed.emit(1, "今日は")
    engine.line_completed.emit(1, "今日は")
    engine.line_changed.emit(2, "でぃすこーどを")  # 確定前に終了した区切り
    assert inserter.texts == []
    session.toggle()
    assert session.state == FINISHING
    engine.finished.emit()
    assert inserter.texts == ["今日はDiscordを"]
    assert session.state == IDLE
    assert overlay.events[-1] == "hide"
    assert sounds == ["start", "stop"]


def test_live_mode_inserts_each_completed_line(qapp):
    session, engine, _, inserter, _, _ = make(live=True)
    engine.loaded.emit()
    session.start()
    engine.line_completed.emit(1, "一つ目。")
    assert inserter.texts == ["一つ目。"]
    engine.line_completed.emit(1, "一つ目。")  # 同じ区切りの重複通知は無視する
    engine.line_completed.emit(2, "二つ目。")
    session.stop()
    engine.finished.emit()
    assert inserter.texts == ["一つ目。", "二つ目。"]


def test_silence_timeout_stops(qapp):
    session, engine, *_ = make()
    engine.loaded.emit()
    session.set_silence_timeout(0.05)
    session.start()
    assert process_events(qapp, lambda: session.state == FINISHING, timeout=1.0)


def test_activity_resets_silence_timer(qapp):
    session, engine, *_ = make()
    engine.loaded.emit()
    session.set_silence_timeout(0.15)
    session.start()
    for _ in range(4):
        process_events(qapp, timeout=0.08)
        engine.activity.emit()
    assert session.state == RECORDING


def test_postprocess_applied_to_inserted_text(qapp):
    session, engine, _, inserter, _, _ = make()
    session.configure(inserter, {}, "mic", True, 60, "add")
    engine.loaded.emit()
    session.start()
    engine.line_completed.emit(1, "そ の 中 で")
    session.stop()
    engine.finished.emit()
    assert inserter.texts == ["その中で。"]
