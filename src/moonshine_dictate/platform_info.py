"""実行中の OS と、OS ごとのファイルの置き場所を返す。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from moonshine_dictate import APP_NAME

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def is_wayland() -> bool:
    """Linux の Wayland セッションで動いているかを返す（要件 R1.2）。"""
    if not IS_LINUX:
        return False
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return True
    return bool(os.environ.get("WAYLAND_DISPLAY")) and not os.environ.get("DISPLAY")


def config_dir() -> Path:
    """設定ファイルを置くディレクトリ（要件 R6.2）。"""
    if IS_WINDOWS:
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif IS_MACOS:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def log_path() -> Path:
    return config_dir() / "moonshine-dictate.log"


def resource_root() -> Path:
    """同梱リソース（モデルなど）の起点。PyInstaller で固めた場合は展開先を返す。"""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    # 開発時はリポジトリのルート（src/moonshine_dictate から2つ上）
    return Path(__file__).resolve().parents[2]
