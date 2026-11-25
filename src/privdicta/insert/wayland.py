"""Wayland での挿入（要件 R1.2）。

wl-copy でクリップボードに入れ、ydotool で Ctrl+V を送る。ydotool が使えなければ、
クリップボードに入れたことを通知し、貼り付けは利用者に任せる。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Callable

log = logging.getLogger(__name__)

# Linux の入力イベントのキーコード（linux/input-event-codes.h）
KEY_LEFTCTRL = 29
KEY_V = 47


class WaylandInserter:
    live = False

    def __init__(self, notify: Callable[[str], None]):
        self._notify = notify

    def insert(self, text: str) -> None:
        if not text:
            return
        if not shutil.which("wl-copy"):
            self._notify("wl-copy が見つかりません。wl-clipboard をインストールしてください")
            return
        subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=False, timeout=5)
        if shutil.which("ydotool"):
            result = subprocess.run(
                ["ydotool", "key", f"{KEY_LEFTCTRL}:1", f"{KEY_V}:1", f"{KEY_V}:0", f"{KEY_LEFTCTRL}:0"],
                check=False, timeout=5, capture_output=True,
            )
            if result.returncode == 0:
                return
            log.warning("ydotool が失敗しました: %s", result.stderr.decode(errors="replace"))
        self._notify("認識したテキストをクリップボードに入れました。Ctrl+V で貼り付けてください")
