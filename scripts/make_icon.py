"""配布物用のアイコン（PNG）を作る。トレイと同じ絵を大きく描く。

    python scripts/make_icon.py packaging/build/icon.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main(out: str) -> int:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap

    from moonshine_dictate.ui import icons

    _app = QGuiApplication([])
    size = 256
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#1c1e22"))
    p.drawRoundedRect(QRectF(8, 8, size - 16, size - 16), 48, 48)
    icons.draw_microphone(p, QRectF(48, 40, size - 96, size - 80), icons.RECORDING_COLOR)
    p.end()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    return 0 if pixmap.save(out) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
