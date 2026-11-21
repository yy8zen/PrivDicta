"""常駐アプリの組み立て。"""

from __future__ import annotations

import logging
import logging.handlers

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from moonshine_dictate import autostart, config, insert, sound
from moonshine_dictate.engine import Engine, resolve_model
from moonshine_dictate.ipc import CommandServer
from moonshine_dictate.platform_info import config_path, is_wayland, log_path
from moonshine_dictate.session import IDLE, LOADING, RECORDING, Session
from moonshine_dictate.ui.native import hide_dock_icon
from moonshine_dictate.ui.overlay import RecordingOverlay
from moonshine_dictate.ui.tray import Tray

log = logging.getLogger(__name__)

LEVELS = {"error": logging.ERROR, "info": logging.INFO, "debug": logging.DEBUG}

TOOLTIPS = {
    LOADING: "moonshine-dictate: モデルを読み込んでいます",
    IDLE: "moonshine-dictate: 待機中",
    RECORDING: "moonshine-dictate: 録音中",
}


def setup_logging() -> None:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler())
    root.setLevel(logging.INFO)


class _Bridge(QObject):
    """pynput のスレッドから UI スレッドへ、ホットキーの通知を渡す。"""

    hotkey = Signal()


class DictateApp:
    def __init__(self, qt_app: QApplication):
        self._qt = qt_app
        self._tray = Tray()
        self._overlay = RecordingOverlay()
        self._engine = Engine()
        self._session = Session(self._engine, self._overlay, self._notify, sound.play)
        self._bridge = _Bridge()
        self._bridge.hotkey.connect(self._session.toggle)
        self._hotkey = None
        self._model_key = None
        self._server = CommandServer(self._handle_command)

        self._overlay.stop_requested.connect(lambda: self._session.stop("ボタン"))
        self._session.state_changed.connect(self._on_state)
        self._tray.toggle_requested.connect(self._session.toggle)
        self._tray.open_config_requested.connect(self._open_config)
        self._tray.reload_requested.connect(self.reload)
        self._tray.quit_requested.connect(self.quit)

    def start(self) -> bool:
        if not self._server.listen():
            return False
        hide_dock_icon()
        self._tray.show()
        self.reload(initial=True)
        return True

    # ---- 設定の反映（要件 R6.3） ----

    def reload(self, initial: bool = False) -> None:
        cfg = config.load(config_path())
        logging.getLogger().setLevel(LEVELS[cfg.log_level])
        for message in cfg.errors:
            log.warning(message)
        if cfg.errors:
            self._notify("設定ファイルに誤りがあります:\n" + "\n".join(cfg.errors[:3]), True)

        inserter = insert.create(cfg.insert_method, cfg.restore_clipboard,
                                 self._wait_keys_released, lambda m: self._notify(m, False))
        self._session.configure(inserter, cfg.replace, cfg.input_device, cfg.sound,
                                cfg.silence_timeout_sec)
        self._set_hotkey(cfg.hotkey)
        autostart.apply(cfg.autostart)

        model_key = (cfg.model_dir, cfg.model_arch)
        if model_key != self._model_key:
            if self._model_key is not None:
                self._notify("モデルの変更は、アプリを再起動すると反映されます", False)
            else:
                self._model_key = model_key
                self._engine.load(resolve_model(cfg.model_dir, cfg.model_arch))
        if not initial and not cfg.errors:
            self._notify("設定を再読み込みしました", False)

    def _set_hotkey(self, combo: str) -> None:
        if self._hotkey is not None:
            self._hotkey.stop()
            self._hotkey = None
        if is_wayland():
            log.info("Wayland のため、ホットキーは登録しません。OS のショートカットに "
                     "`moonshine-dictate toggle` を割り当ててください")
            return
        try:
            from moonshine_dictate.hotkey import HotkeyListener

            self._hotkey = HotkeyListener(combo, self._bridge.hotkey.emit)
            self._hotkey.start()
        except Exception as e:
            log.exception("ホットキーを登録できませんでした")
            self._notify(f"ホットキー {combo} を登録できませんでした: {e}", True)

    def _wait_keys_released(self) -> None:
        if self._hotkey is not None:
            self._hotkey.wait_modifiers_released()

    # ---- コマンド（要件 R3.4） ----

    def _handle_command(self, command: str) -> str:
        if command == "toggle":
            self._session.toggle()
        elif command == "start":
            self._session.start()
        elif command == "stop":
            self._session.stop("コマンド")
        elif command == "reload":
            self.reload()
        elif command == "quit":
            self.quit()
        return f"ok {self._session.state}"

    # ---- その他 ----

    def _on_state(self, state: str) -> None:
        tray_state = {RECORDING: "recording", IDLE: "idle"}.get(state, "busy")
        self._tray.set_state(tray_state, TOOLTIPS.get(state, "moonshine-dictate"))

    def _notify(self, message: str, error: bool = False) -> None:
        (log.warning if error else log.info)(message)
        self._tray.notify(message, error)

    def _open_config(self) -> None:
        path = config_path()
        if not path.exists():
            config.write_default(path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def quit(self) -> None:
        self._session.stop("終了")
        if self._hotkey is not None:
            self._hotkey.stop()
        self._engine.shutdown()
        self._server.close()
        self._tray.hide()
        self._qt.quit()
