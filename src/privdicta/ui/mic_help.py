"""マイクの権限がオフのときの案内の画面（要件 R2.8）。

Qt の QMessageBox は日本語の文を細かく折り返し、幅を広げると右端が切れるため、自前で作る。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QStyle, QVBoxLayout, QWidget

from privdicta import mic_permission


class MicHelpDialog(QDialog):
    def __init__(self, confirmed_denied: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("PrivDicta：マイクを使えません")

        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(48, 48))
        icon.setAlignment(Qt.AlignTop)
        text = QLabel(mic_permission.help_text(confirmed_denied))
        text.setWordWrap(True)
        text.setFixedWidth(440)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(icon)
        body.addWidget(text, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self._url = mic_permission.settings_url()
        if self._url:
            open_settings = QPushButton("マイクの設定を開く")
            open_settings.setDefault(True)
            open_settings.clicked.connect(self._open_settings)
            buttons.addWidget(open_settings)
        close = QPushButton("閉じる")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)
        layout.addLayout(body)
        layout.addLayout(buttons)

    def _open_settings(self) -> None:
        QDesktopServices.openUrl(QUrl(self._url))
        self.accept()
