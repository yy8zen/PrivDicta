"""マイクの権限がオフのときに、利用者を OS の設定画面へ案内する（要件 R2.8）。

OS のマイクの権限は、アプリからは変えない。利用者のプライバシーの選択を上書きすることになるうえ、
Windows では PC 全体の設定に管理者権限が要り、組織のポリシーで固定されていることもあるため。

権限がオフかどうかは、次の2つで判断する。
- Windows：レジストリの「マイクへのアクセス」の設定を読む
- 全 OS：録音を始めてから一定時間、マイクから完全な無音（0）しか届かない。
  権限がオフのとき、OS はアプリに無音を渡す。静かな部屋でも、実際のマイクには小さな雑音が入る
"""

from __future__ import annotations

import logging
from typing import Callable

import numpy as np

from privdicta.platform_info import IS_MACOS, IS_WINDOWS

log = logging.getLogger(__name__)

# 録音を始めてから、この秒数だけ完全な無音が続いたら、権限がオフかミュートと判断する
SILENT_CHECK_SEC = 1.5
# これより小さい振幅しかなければ「完全な無音」とみなす（16bit の1段階は約 3e-5）
SILENT_PEAK = 1e-6

_CONSENT = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"

WINDOWS_SETTINGS_URL = "ms-settings:privacy-microphone"
MACOS_SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"


def _read_windows_value(root: str, path: str) -> str | None:
    import winreg

    hive = winreg.HKEY_LOCAL_MACHINE if root == "HKLM" else winreg.HKEY_CURRENT_USER
    try:
        with winreg.OpenKey(hive, path) as key:
            value, _ = winreg.QueryValueEx(key, "Value")
            return str(value)
    except OSError:
        return None


def windows_access_denied(read: Callable[[str, str], str | None] | None = None) -> bool:
    """Windows のマイクの権限がオフなら True。

    次のどれかが "Deny" ならオフ。
    - HKLM の microphone：PC 全体の「マイクへのアクセス」
    - HKCU の microphone：このユーザーの「マイクへのアクセス」
    - HKCU の microphone\\NonPackaged：「デスクトップ アプリがマイクにアクセスできるようにする」
    """
    if read is None:
        if not IS_WINDOWS:
            return False
        read = _read_windows_value
    for root, path in (("HKLM", _CONSENT), ("HKCU", _CONSENT), ("HKCU", _CONSENT + r"\NonPackaged")):
        try:
            if read(root, path) == "Deny":
                log.info("マイクの権限がオフです: %s\\%s", root, path)
                return True
        except Exception:
            log.debug("マイクの権限を読めませんでした: %s\\%s", root, path, exc_info=True)
    return False


def settings_url() -> str | None:
    """マイクの権限を変える OS の設定画面の URL。Linux にはないので None。"""
    if IS_WINDOWS:
        return WINDOWS_SETTINGS_URL
    if IS_MACOS:
        return MACOS_SETTINGS_URL
    return None


def help_text(confirmed_denied: bool) -> str:
    """利用者に見せる説明。confirmed_denied は、OS の設定でオフだと確かめられた場合に True。"""
    if IS_WINDOWS:
        steps = ("「設定 > プライバシーとセキュリティ > マイク」で、「マイクへのアクセス」と"
                 "「デスクトップ アプリがマイクにアクセスできるようにする」をオンにしてください。")
    elif IS_MACOS:
        steps = "「システム設定 > プライバシーとセキュリティ > マイク」で、PrivDicta をオンにしてください。"
    else:
        steps = "OS のサウンドの設定で、マイクがミュートになっていないかを確かめてください。"
    if confirmed_denied:
        return "マイクへのアクセスがオフになっているため、録音できません。\n\n" + steps
    return ("マイクから音が届いていません。マイクへのアクセスがオフになっているか、"
            "マイクがミュートになっている可能性があります。\n\n" + steps
            + "\n\nマイクが複数ある場合は、PrivDicta の設定画面で使うマイクを選び直してください。")


class SilenceDetector:
    """録音の最初の SILENT_CHECK_SEC 秒が完全な無音かを調べる。PortAudio のスレッドから呼ぶ。"""

    def __init__(self, seconds: float = SILENT_CHECK_SEC, peak: float = SILENT_PEAK):
        self._seconds = seconds
        self._peak_limit = peak
        self._samples = 0  # 小数の誤差を避けるため、経過時間はサンプル数で数える
        self._peak = 0.0
        self._done = False

    def feed(self, audio: np.ndarray, rate: int) -> bool:
        """完全な無音が続いたと分かった最初の1回だけ True を返す。音が来たら、以後は調べない。"""
        if self._done:
            return False
        if audio.size:
            self._peak = max(self._peak, float(np.max(np.abs(audio))))
        if self._peak >= self._peak_limit:
            self._done = True
            return False
        self._samples += audio.size
        if self._samples >= round(self._seconds * rate):
            self._done = True
            return True
        return False
