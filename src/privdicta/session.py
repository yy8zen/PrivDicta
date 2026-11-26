"""録音の開始から挿入・終了までの流れ（要件 R3、R5）。

状態は loading → idle ⇄ recording → finishing → idle と移る。
UI・エンジン・挿入処理は引数で受け取り、テストでは偽物に差し替える。
"""

from __future__ import annotations

import logging
from typing import Callable, Protocol

from PySide6.QtCore import QObject, QTimer, Signal

from privdicta.text import join_lines, postprocess

log = logging.getLogger(__name__)

LOADING, IDLE, RECORDING, FINISHING, BROKEN = "loading", "idle", "recording", "finishing", "broken"


class Overlay(Protocol):
    def show_recording(self) -> None: ...
    def show_finishing(self) -> None: ...
    def set_partial(self, text: str) -> None: ...
    def commit(self, text: str) -> None: ...
    def hide(self) -> None: ...


class Session(QObject):
    state_changed = Signal(str)
    # マイクを使えない。引数はマイクを開けなかったときのエラーの内容で、無音だった場合は None（要件 R2.8）
    mic_blocked = Signal(object)

    def __init__(self, engine, overlay: Overlay, notify: Callable[[str, bool], None],
                 play_sound: Callable[[str], None]):
        super().__init__()
        self._engine = engine
        self._overlay = overlay
        self._notify = notify
        self._play_sound = play_sound
        self._inserter = None
        self._replace: dict[str, str] = {}
        self._punctuation = "keep"
        self._device = ""
        self._sound = True
        self._state = LOADING

        self._silence = QTimer(self)
        self._silence.setSingleShot(True)
        self._silence.timeout.connect(lambda: self.stop("無音が続いたため"))
        self.set_silence_timeout(60)

        # 1回の録音の中で見た区切り。line_id → 最新のテキスト（出てきた順）
        self._lines: dict[object, str] = {}
        self._completed: set = set()
        self._collected: list[str] = []

        engine.loaded.connect(self._on_loaded)
        engine.load_failed.connect(self._on_load_failed)
        engine.line_changed.connect(self._on_line_changed)
        engine.line_completed.connect(self._on_line_completed)
        engine.activity.connect(self._on_activity)
        engine.finished.connect(self._on_finished)
        if hasattr(engine, "mic_silent"):
            engine.mic_silent.connect(self._on_mic_silent)
        engine.failed.connect(lambda msg: self._notify(f"認識でエラーが起きました: {msg}", True))

    # ---- 設定 ----

    def configure(self, inserter, replace: dict[str, str], device: str, sound: bool,
                  silence_timeout_sec: int, punctuation: str = "keep") -> None:
        """設定を反映する。録音中に呼ばれた場合は、次の録音から効く項目がある。"""
        self._inserter = inserter
        self._replace = dict(replace)
        self._punctuation = punctuation
        self._device = device
        self._sound = sound
        self.set_silence_timeout(silence_timeout_sec)

    def set_silence_timeout(self, seconds: int) -> None:
        self._silence.setInterval(int(seconds * 1000))

    @property
    def state(self) -> str:
        return self._state

    # ---- 操作（要件 R3.2） ----

    def toggle(self) -> None:
        if self._state == RECORDING:
            self.stop("ホットキー")
        elif self._state == IDLE:
            self.start()
        elif self._state == LOADING:
            self._notify("モデルを読み込んでいます。少し待ってから押してください", False)
        elif self._state == BROKEN:
            self._notify("モデルを読み込めなかったため、音声入力を使えません", True)
        # FINISHING 中は無視する。残りの音声の認識はすぐに終わる

    def start(self) -> None:
        if self._state != IDLE:
            return
        try:
            self._engine.start(self._device)
        except Exception as e:
            log.exception("録音を開始できませんでした")
            self._beep("error")
            self.mic_blocked.emit(str(e) or type(e).__name__)
            return
        self._lines.clear()
        self._completed.clear()
        self._collected.clear()
        self._set_state(RECORDING)
        self._overlay.show_recording()
        self._beep("start")
        self._silence.start()

    def stop(self, reason: str = "") -> None:
        if self._state != RECORDING:
            return
        log.info("録音を終了します（%s）", reason or "指示")
        self._silence.stop()
        self._set_state(FINISHING)
        self._overlay.show_finishing()
        self._beep("stop")
        self._engine.stop()

    # ---- エンジンからの通知 ----

    def _on_loaded(self) -> None:
        if self._state in (LOADING, BROKEN):
            self._set_state(IDLE)

    def begin_loading(self) -> None:
        """モデルを読み込み直す間、録音を受け付けない。録音中なら、終わってから読み込み中になる。"""
        if self._state in (IDLE, BROKEN):
            self._set_state(LOADING)

    def _on_load_failed(self, message: str) -> None:
        if getattr(self._engine, "is_loaded", False):
            # 読み込み直しに失敗しても、前のモデルで使い続ける
            self._notify(f"モデルを読み込めなかったため、前のモデルを使います: {message}", True)
            if self._state == LOADING:
                self._set_state(IDLE)
            return
        self._set_state(BROKEN)
        self._notify(f"モデルを読み込めませんでした: {message}", True)

    def _on_mic_silent(self) -> None:
        if self._state == RECORDING:
            self.stop("マイクから音が届いていない")
            self._beep("error")
            self.mic_blocked.emit(None)

    def _on_activity(self) -> None:
        if self._state == RECORDING:
            self._silence.start()  # 計測をやり直す

    def _on_line_changed(self, line_id, text: str) -> None:
        if line_id in self._completed:
            return
        self._lines[line_id] = text
        self._overlay.set_partial(text)

    def _on_line_completed(self, line_id, text: str) -> None:
        if line_id in self._completed:
            return
        self._lines[line_id] = text
        self._complete(line_id, text)

    def _complete(self, line_id, text: str) -> None:
        self._completed.add(line_id)
        text = postprocess(text, self._punctuation, self._replace)
        if not text:
            return
        self._overlay.commit(text)
        if self._inserter is not None and self._inserter.live:
            self._insert(text)
        else:
            self._collected.append(text)

    def _on_finished(self) -> None:
        # 確定の通知が来ないまま終わった区切りも、最後のテキストで確定扱いにする
        for line_id, text in list(self._lines.items()):
            if line_id not in self._completed:
                self._complete(line_id, text)
        if self._inserter is not None and not self._inserter.live:
            self._insert(join_lines(self._collected))
        self._collected.clear()
        self._overlay.hide()
        if self._state in (RECORDING, FINISHING):
            if self._state == RECORDING:  # エンジン側の失敗で終わった
                self._silence.stop()
                self._engine.stop()
            self._set_state(IDLE)

    # ---- 内部 ----

    def _insert(self, text: str) -> None:
        if not text:
            return
        try:
            self._inserter.insert(text)
        except Exception as e:
            log.exception("テキストを入力できませんでした")
            self._notify(f"テキストを入力できませんでした: {e}", True)

    def _beep(self, kind: str) -> None:
        if self._sound:
            self._play_sound(kind)

    def _set_state(self, state: str) -> None:
        self._state = state
        self.state_changed.emit(state)
