"""常駐アプリの組み立て。"""

from __future__ import annotations

import dataclasses
import logging
import logging.handlers

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from ototype import autostart, config, insert, sound
from ototype.migrate import migrate_old_settings
from ototype.engine import BUNDLED_ARCH, Engine, resolve_model
from ototype.ipc import CommandServer
from ototype.platform_info import config_path, is_wayland, log_path
from ototype.session import FINISHING, IDLE, LOADING, RECORDING, Session
from ototype.ui.native import activate_app, hide_dock_icon
from ototype.ui.overlay import RecordingOverlay
from ototype.ui.tray import Tray

log = logging.getLogger(__name__)

LEVELS = {"error": logging.ERROR, "info": logging.INFO, "debug": logging.DEBUG}

TOOLTIPS = {
    LOADING: "OtoType: モデルを読み込んでいます",
    IDLE: "OtoType: 待機中",
    RECORDING: "OtoType: 録音中",
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
        # 録音中に設定でモデルが変わった場合、録音が終わってから読み込む
        self._pending_model = None
        self._settings_dialog = None
        self._server = CommandServer(self._handle_command)

        self._overlay.stop_requested.connect(lambda: self._session.stop("ボタン"))
        self._session.state_changed.connect(self._on_state)
        self._tray.toggle_requested.connect(self._session.toggle)
        self._tray.settings_requested.connect(self.open_settings)
        self._tray.help_requested.connect(self.show_welcome)
        self._tray.open_config_requested.connect(self._open_config)
        self._tray.reload_requested.connect(self.reload)
        self._tray.quit_requested.connect(self.quit)

    def start(self) -> bool:
        if not self._server.listen():
            return False
        hide_dock_icon()
        self._tray.show()
        first_run = not config_path().exists()  # 設定ファイルは初回の読み込みで作られる
        if first_run and migrate_old_settings():
            log.info("旧名 moonshine-dictate の設定を引き継ぎました")
        self.reload(initial=True)
        if first_run:
            QTimer.singleShot(0, self.show_welcome)
        return True

    def show_welcome(self) -> None:
        """使い方の画面を出す。画面で自動起動を切り替えたら、設定ファイルに保存する。"""
        from ototype.ui.welcome import WelcomeDialog

        cfg = config.load(config_path())
        dialog = WelcomeDialog(cfg.hotkey, cfg.autostart)
        wants_settings = []
        dialog.settings_requested.connect(lambda: wants_settings.append(True))
        activate_app()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec()
        if dialog.autostart.isChecked() != cfg.autostart:
            cfg = dataclasses.replace(cfg, autostart=dialog.autostart.isChecked(), errors=[])
            try:
                config.save(config_path(), cfg)
            except OSError as e:
                self._notify(f"設定を保存できませんでした: {e}", True)
            self.reload(quiet=True)
        if wants_settings:
            self.open_settings()

    # ---- 設定の反映（要件 R6.3） ----

    def reload(self, initial: bool = False, quiet: bool = False) -> None:
        cfg = config.load(config_path())
        logging.getLogger().setLevel(LEVELS[cfg.log_level])
        for message in cfg.errors:
            log.warning(message)
        if cfg.errors:
            self._notify("設定ファイルに誤りがあります:\n" + "\n".join(cfg.errors[:3]), True)

        inserter = insert.create(cfg.insert_method, cfg.restore_clipboard,
                                 self._wait_keys_released, lambda m: self._notify(m, False))
        self._session.configure(inserter, cfg.replace, cfg.input_device, cfg.sound,
                                cfg.silence_timeout_sec, cfg.punctuation)
        self._set_hotkey(cfg.hotkey)
        autostart.apply(cfg.autostart)

        model_key = (cfg.model_dir, cfg.model_arch)
        if model_key != self._model_key:
            self._model_key = model_key
            self._load_model(model_key)
        if not initial and not quiet and not cfg.errors:
            self._notify("設定を再読み込みしました", False)

    def _load_model(self, model_key) -> None:
        if self._session.state in (RECORDING, FINISHING):
            self._pending_model = model_key
            return
        self._pending_model = None
        spec = resolve_model(*model_key)
        model_dir, arch = model_key
        if not spec.path.is_dir() and not model_dir and arch != BUNDLED_ARCH:
            # v0.1.0 の設定ファイルには small-streaming が書かれているが、v0.2.0 からは同梱していない
            self._notify(f"モデル {arch} が見つからないため、{BUNDLED_ARCH} を使います。"
                         "設定画面でモデルを選び直してください", True)
            spec = resolve_model("", BUNDLED_ARCH)
        self._session.begin_loading()
        self._engine.load(spec)

    # ---- 設定画面 ----

    def open_settings(self) -> None:
        if self._settings_dialog is not None:
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        from ototype.engine import available_models, list_input_devices
        from ototype.ui.settings import SettingsDialog

        cfg = config.load(config_path())
        dialog = SettingsDialog(cfg, available_models(cfg.model_dir), list_input_devices())
        dialog.open_file_requested.connect(self._open_config)
        self._settings_dialog = dialog
        # 画面でホットキーを押して登録する間、録音が始まらないようにホットキーを止める
        if self._hotkey is not None:
            self._hotkey.stop()
            self._hotkey = None
        activate_app()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        try:
            accepted = dialog.exec() == dialog.DialogCode.Accepted
        finally:
            self._settings_dialog = None
        if accepted:
            new = dialog.result_config()
            try:
                config.save(config_path(), new)
            except OSError as e:
                self._notify(f"設定を保存できませんでした: {e}", True)
            else:
                self._notify("設定を保存しました", False)
        # 保存しなかった場合もホットキーを登録し直すため、読み込み直す
        self.reload(quiet=True)

    def _set_hotkey(self, combo: str) -> None:
        if self._hotkey is not None:
            self._hotkey.stop()
            self._hotkey = None
        if is_wayland():
            log.info("Wayland のため、ホットキーは登録しません。OS のショートカットに "
                     "`ototype toggle` を割り当ててください")
            return
        try:
            from ototype.hotkey import HotkeyListener

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
        if state == IDLE and self._pending_model is not None:
            self._load_model(self._pending_model)
            return
        tray_state = {RECORDING: "recording", IDLE: "idle"}.get(state, "busy")
        self._tray.set_state(tray_state, TOOLTIPS.get(state, "OtoType"))

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
