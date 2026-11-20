"""OS へのログイン時の自動起動（設定項目 autostart）。"""

from __future__ import annotations

import logging
import shlex
import sys
from pathlib import Path

from moonshine_dictate.platform_info import IS_MACOS, IS_WINDOWS

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "moonshine-dictate"
MAC_LABEL = "io.github.moonshine-dictate"


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "moonshine_dictate"]


def apply(enabled: bool) -> None:
    try:
        if IS_WINDOWS:
            _windows(enabled)
        elif IS_MACOS:
            _macos(enabled)
        else:
            _linux(enabled)
    except Exception:
        log.exception("自動起動の設定に失敗しました")


def _windows(enabled: bool) -> None:
    import subprocess
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ,
                              subprocess.list2cmdline(launch_command()))
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def _macos(enabled: bool) -> None:
    import plistlib

    path = Path.home() / "Library" / "LaunchAgents" / f"{MAC_LABEL}.plist"
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            plistlib.dump({"Label": MAC_LABEL, "ProgramArguments": launch_command(),
                           "RunAtLoad": True}, f)
    else:
        path.unlink(missing_ok=True)


def _linux(enabled: bool) -> None:
    import os

    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = base / "autostart" / "moonshine-dictate.desktop"
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[Desktop Entry]\nType=Application\nName=moonshine-dictate\n"
            f"Exec={shlex.join(launch_command())}\nX-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
    else:
        path.unlink(missing_ok=True)
