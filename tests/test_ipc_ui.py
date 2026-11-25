import os
import subprocess
import sys
from pathlib import Path

from privdicta import ipc
from tests.conftest import process_events

SRC = str(Path(__file__).resolve().parents[1] / "src")

CLIENT = """
from PySide6.QtCore import QCoreApplication
app = QCoreApplication([])
from privdicta import ipc
ipc.server_name = lambda: "privdicta-test"
print(ipc.send("toggle"))
"""


def test_command_roundtrip(qapp, monkeypatch):
    # 実際の使い方と同じく、別のプロセスから指示を送る
    monkeypatch.setattr(ipc, "server_name", lambda: "privdicta-test")
    received = []
    server = ipc.CommandServer(lambda c: (received.append(c), "ok idle")[1])
    assert server.listen()
    env = dict(os.environ, PYTHONPATH=SRC)
    proc = subprocess.Popen([sys.executable, "-c", CLIENT], env=env,
                            stdout=subprocess.PIPE, text=True)
    assert process_events(qapp, lambda: proc.poll() is not None, timeout=10.0)
    server.close()
    assert received == ["toggle"]
    assert proc.stdout.read().strip() == "ok idle"


def test_send_without_server(qapp, monkeypatch):
    monkeypatch.setattr(ipc, "server_name", lambda: "privdicta-nobody")
    assert ipc.send("toggle") is None


def test_overlay_and_tray_build(qapp):
    from privdicta.ui.overlay import RecordingOverlay
    from privdicta.ui.tray import Tray

    overlay = RecordingOverlay()
    overlay.show_recording()
    overlay.set_partial("こんにちは")
    overlay.commit("こんにちは。")
    overlay.show_finishing()
    assert overlay.isVisible()
    overlay.hide()
    tray = Tray()
    tray.set_state("recording", "録音中")
