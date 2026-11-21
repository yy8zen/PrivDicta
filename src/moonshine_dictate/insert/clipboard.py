"""クリップボード経由の貼り付け（要件 R5.1、R5.2）。"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QMimeData, QTimer
from PySide6.QtGui import QGuiApplication

from moonshine_dictate.platform_info import IS_MACOS

log = logging.getLogger(__name__)

# 貼り付けキーを送ってから元の内容に戻すまでの時間。短いと、相手のアプリが読む前に戻ってしまう
RESTORE_DELAY_MS = 600


def _copy_mime(src: QMimeData | None) -> QMimeData | None:
    """クリップボードの全形式を複製する。テキスト以外（画像など）も戻せるようにする。"""
    if src is None or not src.formats():
        return None
    dst = QMimeData()
    for fmt in src.formats():
        dst.setData(fmt, src.data(fmt))
    return dst


def send_paste_shortcut() -> None:
    from pynput.keyboard import Controller, Key

    kb = Controller()
    modifier = Key.cmd if IS_MACOS else Key.ctrl
    with kb.pressed(modifier):
        kb.press("v")
        kb.release("v")


class ClipboardInserter:
    """live=True にすると、確定した区切りごとに貼り付ける（Linux の X11 でのライブ入力に使う）。"""

    def __init__(self, restore: bool, wait_keys_released: Callable[[], None], live: bool = False):
        self.live = live
        self._restore = restore
        self._wait_keys_released = wait_keys_released
        # 退避した元の内容。続けて貼り付けるときは最初の退避分を保ち、最後に1回だけ戻す
        self._saved: QMimeData | None = None
        self._last_text = ""
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(RESTORE_DELAY_MS)
        self._timer.timeout.connect(self._restore_now)

    def insert(self, text: str) -> None:
        if not text:
            return
        clipboard = QGuiApplication.clipboard()
        if self._restore and not self._timer.isActive():
            self._saved = _copy_mime(clipboard.mimeData())
        clipboard.setText(text)
        self._last_text = text
        self._wait_keys_released()
        send_paste_shortcut()
        log.debug("%d 文字を貼り付けました", len(text))
        if self._restore:
            self._timer.start()

    def _restore_now(self) -> None:
        clipboard = QGuiApplication.clipboard()
        # 待っている間に利用者が別の内容をコピーしていたら、上書きしない
        if self._saved is not None and clipboard.text() == self._last_text:
            clipboard.setMimeData(self._saved)
        self._saved = None
