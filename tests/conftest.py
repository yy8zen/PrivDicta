import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def process_events(app, until=lambda: False, timeout=2.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if until():
            return True
        time.sleep(0.005)
    app.processEvents()
    return until()
