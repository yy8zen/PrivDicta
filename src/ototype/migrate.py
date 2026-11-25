"""旧名 moonshine-dictate（v0.2.0 より前）からの引き継ぎ。

アプリ名を変えたのは、Moonshine AI Community License の第 IV 条 c(i) が、Moonshine AI の名前を
帰属表示以外で使うことを禁じているため（要件 R7.5）。
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from ototype.platform_info import IS_MACOS, IS_WINDOWS, config_dir

log = logging.getLogger(__name__)

OLD_NAME = "moonshine-dictate"


def old_config_dir() -> Path:
    return config_dir().parent / OLD_NAME


def migrate_old_settings() -> bool:
    """新しい設定フォルダがまだなく、旧名の設定フォルダがあれば、設定ファイルをコピーする。

    旧名で登録した自動起動は、旧アプリを指していて動かないので消す。引き継いだら True を返す。
    """
    new_dir, old_dir = config_dir(), old_config_dir()
    if (new_dir / "config.toml").exists() or not (old_dir / "config.toml").is_file():
        return False
    new_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_dir / "config.toml", new_dir / "config.toml")
    _remove_old_autostart()
    log.info("旧名 %s の設定を引き継ぎました: %s", OLD_NAME, old_dir)
    return True


def _remove_old_autostart() -> None:
    try:
        if IS_WINDOWS:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, OLD_NAME)
                except FileNotFoundError:
                    pass
        elif IS_MACOS:
            (Path.home() / "Library" / "LaunchAgents" / f"io.github.{OLD_NAME}.plist").unlink(missing_ok=True)
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
            (base / "autostart" / f"{OLD_NAME}.desktop").unlink(missing_ok=True)
    except Exception:
        log.exception("旧名の自動起動の登録を消せませんでした")
