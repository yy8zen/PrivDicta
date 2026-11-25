"""アイコンをコードで描く。画像ファイルを同梱しなくて済むようにする。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

IDLE_COLOR = QColor("#8a8f98")
RECORDING_COLOR = QColor("#e5484d")
BUSY_COLOR = QColor("#f5a524")


def draw_microphone(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """rect の中にマイクの形を描く。"""
    w, h = rect.width(), rect.height()
    x, y = rect.x(), rect.y()
    pen = QPen(color, max(1.5, w * 0.08))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    # 本体
    body = QRectF(x + w * 0.36, y + h * 0.12, w * 0.28, h * 0.46)
    painter.setBrush(color)
    painter.drawRoundedRect(body, w * 0.14, w * 0.14)
    # 受け皿の弧
    painter.setBrush(Qt.NoBrush)
    arc = QPainterPath()
    arc.arcMoveTo(QRectF(x + w * 0.24, y + h * 0.22, w * 0.52, h * 0.5), 180)
    arc.arcTo(QRectF(x + w * 0.24, y + h * 0.22, w * 0.52, h * 0.5), 180, 180)
    painter.drawPath(arc)
    # 脚
    painter.drawLine(int(x + w * 0.5), int(y + h * 0.72), int(x + w * 0.5), int(y + h * 0.86))
    painter.drawLine(int(x + w * 0.36), int(y + h * 0.88), int(x + w * 0.64), int(y + h * 0.88))


def tray_icon(color: QColor) -> QIcon:
    icon = QIcon()
    for size in (16, 22, 32, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        draw_microphone(p, QRectF(0, 0, size, size), color)
        p.end()
        icon.addPixmap(pixmap)
    return icon
