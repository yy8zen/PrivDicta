"""録音ウィンドウがフォーカスを奪わないようにする OS ごとの処理（要件 R4.3）。

フォーカスを奪うと、テキストが元のアプリではなく録音ウィンドウに入ってしまう。
Qt のフラグ（Tool、WindowDoesNotAcceptFocus、WA_ShowWithoutActivating）に加えて、
Windows と macOS ではネイティブのウィンドウ属性を直接設定する。
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QWidget

from moonshine_dictate.platform_info import IS_MACOS, IS_WINDOWS

log = logging.getLogger(__name__)


def make_non_activating(widget: QWidget) -> None:
    """ネイティブのウィンドウを作り、クリックしても前面のアプリが切り替わらないようにする。"""
    handle = int(widget.winId())  # ここでネイティブのウィンドウが作られる
    try:
        if IS_WINDOWS:
            _windows(handle)
        elif IS_MACOS:
            _macos(handle)
    except Exception:  # pragma: no cover - OS 固有の失敗。Qt のフラグだけで動かす
        log.exception("録音ウィンドウのネイティブ設定に失敗しました")


def _windows(hwnd: int) -> None:
    import ctypes
    from ctypes import wintypes

    GWL_EXSTYLE = -20
    WS_EX_TOPMOST = 0x00000008
    WS_EX_TOOLWINDOW = 0x00000080  # タスクバーに出さない
    WS_EX_NOACTIVATE = 0x08000000  # クリックしてもアクティブにならない
    user32 = ctypes.windll.user32
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE,
                             style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)


def _macos(view_ptr: int) -> None:
    import objc
    from AppKit import (
        NSStatusWindowLevel,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
    )

    NS_NONACTIVATING_PANEL = 1 << 7
    view = objc.objc_object(c_void_p=view_ptr)
    window = view.window()
    # Qt は Qt.Tool のウィンドウを NSPanel で作る。非アクティブ化は NSPanel でだけ効く
    window.setStyleMask_(window.styleMask() | NS_NONACTIVATING_PANEL)
    window.setLevel_(NSStatusWindowLevel)
    window.setHidesOnDeactivate_(False)
    window.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                  | NSWindowCollectionBehaviorFullScreenAuxiliary)
    if hasattr(window, "setBecomesKeyOnlyIfNeeded_"):
        window.setBecomesKeyOnlyIfNeeded_(True)


def hide_dock_icon() -> None:
    """macOS で Dock にアイコンを出さず、メニューバーだけに常駐する。"""
    if not IS_MACOS:
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:  # pragma: no cover
        log.exception("Dock アイコンを隠せませんでした")


def activate_app() -> None:
    """設定画面を開くときに、アプリを前面に出す。macOS では Dock に出ないアプリでも前面にできる。"""
    if not IS_MACOS:
        return
    try:
        from AppKit import NSApplication

        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:  # pragma: no cover
        log.exception("アプリを前面に出せませんでした")
