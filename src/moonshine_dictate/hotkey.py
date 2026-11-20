"""グローバルホットキー（要件 R3.3）。

pynput を使う。Windows はキーボードフック、macOS はイベントタップ（アクセシビリティの許可が要る）、
Linux は X11 の XRecord で押されたキーを受け取る。Wayland では使えないため登録しない（要件 R1.2）。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

log = logging.getLogger(__name__)

# 設定ファイルの書き方 → pynput の書き方
_MODIFIERS = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "option": "<alt>",
    "opt": "<alt>",
    "shift": "<shift>",
    "cmd": "<cmd>",
    "command": "<cmd>",
    "win": "<cmd>",
    "super": "<cmd>",
    "meta": "<cmd>",
}
_NAMED_KEYS = {
    "space": "<space>",
    "enter": "<enter>",
    "return": "<enter>",
    "tab": "<tab>",
    "esc": "<esc>",
    "escape": "<esc>",
    "backspace": "<backspace>",
    "insert": "<insert>",
    "delete": "<delete>",
    "home": "<home>",
    "end": "<end>",
    "pageup": "<page_up>",
    "pagedown": "<page_down>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
    "pause": "<pause>",
    "scrolllock": "<scroll_lock>",
}
_NAMED_KEYS.update({f"f{i}": f"<f{i}>" for i in range(1, 21)})


def parse_hotkey(text: str) -> str:
    """"ctrl+alt+space" を pynput の "<ctrl>+<alt>+<space>" に変える。誤りは ValueError。"""
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    if not parts:
        raise ValueError("キーが指定されていません")
    *mods, key = parts
    out = []
    for m in mods:
        if m not in _MODIFIERS:
            raise ValueError(f"修飾キー {m!r} は使えません")
        if _MODIFIERS[m] not in out:
            out.append(_MODIFIERS[m])
    if key in _NAMED_KEYS:
        out.append(_NAMED_KEYS[key])
    elif len(key) == 1 and key.isprintable():
        out.append(key)
    else:
        raise ValueError(f"キー {key!r} は使えません")
    has_function_key = key.startswith("f") and key[1:].isdigit()
    if not mods and not has_function_key:
        # 修飾キーなしの通常キーを奪うと、そのキーで文字が打てなくなる
        raise ValueError("修飾キーなしで使えるのは F1〜F20 だけです")
    return "+".join(out)


class HotkeyListener:
    """ホットキーが押されたら `on_activate` を呼ぶ。呼び出しは pynput のスレッドから行われる。"""

    def __init__(self, hotkey: str, on_activate: Callable[[], None]):
        from pynput import keyboard

        self._keyboard = keyboard
        self._combo = parse_hotkey(hotkey)
        self._on_activate = on_activate
        self._hotkey = keyboard.HotKey(keyboard.HotKey.parse(self._combo), self._fire)
        self._pressed: set = set()
        self._lock = threading.Lock()
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)

    def start(self) -> None:
        self._listener.start()
        log.info("ホットキー %s を登録しました", self._combo)

    def stop(self) -> None:
        self._listener.stop()

    def modifiers_down(self) -> bool:
        """修飾キーがまだ押されているか。貼り付けキーを送る前に、離されるのを待つのに使う。"""
        k = self._keyboard.Key
        mods = {k.ctrl, k.ctrl_l, k.ctrl_r, k.alt, k.alt_l, k.alt_r, k.alt_gr,
                k.shift, k.shift_l, k.shift_r, k.cmd, k.cmd_l, k.cmd_r}
        with self._lock:
            return bool(self._pressed & mods)

    def wait_modifiers_released(self, timeout: float = 1.0) -> None:
        deadline = time.monotonic() + timeout
        while self.modifiers_down() and time.monotonic() < deadline:
            time.sleep(0.02)

    def _fire(self) -> None:
        try:
            self._on_activate()
        except Exception:  # pragma: no cover - 呼び出し先の例外でフックを止めない
            log.exception("ホットキーの処理で例外が起きました")

    def _press(self, key) -> None:
        with self._lock:
            self._pressed.add(key)
        self._hotkey.press(self._listener.canonical(key))

    def _release(self, key) -> None:
        with self._lock:
            self._pressed.discard(key)
        self._hotkey.release(self._listener.canonical(key))
