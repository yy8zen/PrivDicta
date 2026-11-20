"""Unicode のキー入力として送る（要件 R5.3）。

pynput の type() は OS ごとに次の方法で文字を送る。
- Windows: SendInput の KEYEVENTF_UNICODE
- macOS: CGEventKeyboardSetUnicodeString

Linux（X11）では使わない。XTest で日本語を送ると文字が化けるため、
区切りごとのクリップボード貼り付けで代える（insert/__init__.py の create() を参照）。
"""

from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)


class LiveInserter:
    live = True

    def __init__(self, wait_keys_released: Callable[[], None]):
        from pynput.keyboard import Controller

        self._kb = Controller()
        self._wait_keys_released = wait_keys_released

    def insert(self, text: str) -> None:
        if not text:
            return
        self._wait_keys_released()
        self._kb.type(text)
        log.debug("%d 文字をキー入力で送りました", len(text))
