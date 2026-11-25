"""タスクトレイ（macOS ではメニューバー）のアイコンとメニュー（要件 R4.6）。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from privdicta.ui import icons


class Tray(QObject):
    toggle_requested = Signal()
    settings_requested = Signal()
    help_requested = Signal()
    open_config_requested = Signal()
    reload_requested = Signal()
    quit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._icons = {
            "idle": icons.tray_icon(icons.IDLE_COLOR),
            "recording": icons.tray_icon(icons.RECORDING_COLOR),
            "busy": icons.tray_icon(icons.BUSY_COLOR),
        }
        self._tray = QSystemTrayIcon(self._icons["busy"])
        self._menu = QMenu()
        self._toggle = QAction("録音を開始", self._menu)
        self._toggle.triggered.connect(self.toggle_requested)
        self._menu.addAction(self._toggle)
        self._menu.addSeparator()
        settings = QAction("設定…", self._menu)
        settings.triggered.connect(self.settings_requested)
        self._menu.addAction(settings)
        help_action = QAction("使い方", self._menu)
        help_action.triggered.connect(self.help_requested)
        self._menu.addAction(help_action)
        open_cfg = QAction("設定ファイルを開く", self._menu)
        open_cfg.triggered.connect(self.open_config_requested)
        self._menu.addAction(open_cfg)
        reload_cfg = QAction("設定の再読み込み", self._menu)
        reload_cfg.triggered.connect(self.reload_requested)
        self._menu.addAction(reload_cfg)
        self._menu.addSeparator()
        quit_action = QAction("終了", self._menu)
        quit_action.triggered.connect(self.quit_requested)
        self._menu.addAction(quit_action)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        self.set_state("busy", "PrivDicta: モデルを読み込んでいます")

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def set_state(self, state: str, tooltip: str) -> None:
        self._tray.setIcon(self._icons[state])
        self._tray.setToolTip(tooltip)
        self._toggle.setText("録音を終了" if state == "recording" else "録音を開始")
        self._toggle.setEnabled(state != "busy")

    def notify(self, message: str, error: bool = False) -> None:
        icon = QSystemTrayIcon.Warning if error else QSystemTrayIcon.Information
        self._tray.showMessage("PrivDicta", message, icon, 6000)

    def _on_activated(self, reason) -> None:
        # Windows と Linux では左クリックで録音を切り替える。macOS はクリックでメニューが開く
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_requested.emit()
