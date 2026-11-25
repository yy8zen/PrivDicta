"""録音中に画面下部の中央に出す小さなウィンドウ（要件 R4.1〜R4.4）。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QWidget

from privdicta.ui import icons
from privdicta.ui.native import make_non_activating

TEXT_WIDTH = 420
MARGIN_BOTTOM = 72


class MicButton(QAbstractButton):
    """丸いマイクボタン。録音中は赤く点灯する。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip("クリックすると録音を終了します")

    def sizeHint(self) -> QSize:
        return QSize(44, 44)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        p.setPen(Qt.NoPen)
        p.setBrush(icons.RECORDING_COLOR if on else QColor("#3a3f47"))
        p.drawEllipse(QRectF(2, 2, 40, 40))
        icons.draw_microphone(p, QRectF(10, 9, 24, 26), QColor("white"))


class RecordingOverlay(QWidget):
    stop_requested = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

        self._button = MicButton(self)
        self._button.clicked.connect(self._on_click)
        self._label = QLabel(self)
        self._label.setFixedWidth(TEXT_WIDTH)
        self._label.setStyleSheet("color: #f2f3f5; font-size: 15px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 18, 8)
        layout.setSpacing(12)
        layout.addWidget(self._button)
        layout.addWidget(self._label)
        self._native_ready = False
        self._committed = ""
        self._pending = ""

    # ---- 状態の表示 ----

    def show_recording(self) -> None:
        self._committed = ""
        self._pending = ""
        self._button.setChecked(True)
        self._set_text("お話しください…", dim=True)
        if not self._native_ready:
            make_non_activating(self)
            self._native_ready = True
        self.adjustSize()
        self._move_to_bottom_center()
        self.show()
        self.raise_()

    def show_finishing(self) -> None:
        self._button.setChecked(False)
        if not (self._committed or self._pending):
            self._set_text("認識しています…", dim=True)

    def set_partial(self, text: str) -> None:
        """認識中の区切りの途中結果を表示する（要件 R4.4）。"""
        self._pending = text
        self._refresh()

    def commit(self, text: str) -> None:
        """区切りが確定した。表示は直近の確定分とつなげて見せる。"""
        self._committed = (self._committed + text)[-200:]
        self._pending = ""
        self._refresh()

    # ---- 内部 ----

    def _refresh(self) -> None:
        text = self._committed + self._pending
        if text:
            self._set_text(text, dim=False)

    def _set_text(self, text: str, dim: bool) -> None:
        # 長い文は末尾（いま話している部分）を見せる
        metrics = QFontMetrics(self._label.font())
        shown = metrics.elidedText(text, Qt.ElideLeft, TEXT_WIDTH)
        color = "#9aa0a8" if dim else "#f2f3f5"
        self._label.setStyleSheet(f"color: {color}; font-size: 15px;")
        self._label.setText(shown)

    def _on_click(self) -> None:
        # クリックで checked が反転するので、表示は呼び出し側の状態に任せる
        self._button.setChecked(True)
        self.stop_requested.emit()

    def _move_to_bottom_center(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x = area.x() + (area.width() - self.width()) // 2
        y = area.y() + area.height() - self.height() - MARGIN_BOTTOM
        self.move(QPoint(x, y))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(28, 30, 34, 235))
        r = self.rect().adjusted(0, 0, -1, -1)
        p.drawRoundedRect(QRectF(r), r.height() / 2, r.height() / 2)
