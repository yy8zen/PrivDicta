"""マイクを使えないときに、利用者を OS の設定画面へ案内する（要件 R2.8）。

OS のマイクの権限は、アプリからは変えない。利用者のプライバシーの選択を上書きすることになるうえ、
Windows では PC 全体の設定に管理者権限が要り、組織のポリシーで固定されていることもあるため。

次の2つの場合に、マイクを使えないと判断する。
- マイクを開くときにエラーになった
- 録音を始めてから一定時間、マイクから完全な無音（0）しか届かない。権限がオフのとき、OS は
  エラーを返さずにアプリに無音を渡すことが多い。静かな部屋でも、実際のマイクには小さな雑音が入る
"""

from __future__ import annotations

import logging
import numpy as np

from privdicta.platform_info import IS_MACOS, IS_WINDOWS

log = logging.getLogger(__name__)

# 録音を始めてから、この秒数だけ完全な無音が続いたら、権限がオフかミュートと判断する
SILENT_CHECK_SEC = 1.5
# これより小さい振幅しかなければ「完全な無音」とみなす（16bit の1段階は約 3e-5）
SILENT_PEAK = 1e-6

WINDOWS_SETTINGS_URL = "ms-settings:privacy-microphone"
MACOS_SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"


def settings_url() -> str | None:
    """マイクの権限を変える OS の設定画面の URL。Linux にはないので None。"""
    if IS_WINDOWS:
        return WINDOWS_SETTINGS_URL
    if IS_MACOS:
        return MACOS_SETTINGS_URL
    return None


def help_text(error: str | None = None) -> str:
    """利用者に見せる説明。error はマイクを開けなかったときのエラーの内容。None なら無音だった場合。"""
    if IS_WINDOWS:
        steps = ("「設定 > プライバシーとセキュリティ > マイク」で、「マイクへのアクセス」と"
                 "「デスクトップ アプリがマイクにアクセスできるようにする」がオンになっているかを確かめてください。")
    elif IS_MACOS:
        steps = "「システム設定 > プライバシーとセキュリティ > マイク」で、PrivDicta がオンになっているかを確かめてください。"
    else:
        steps = "OS のサウンドの設定で、マイクがつながっていて、ミュートになっていないかを確かめてください。"
    if error is None:
        head = ("マイクから音が届いていません。マイクへのアクセスがオフになっているか、"
                "マイクがミュートになっている可能性があります。")
    else:
        head = f"マイクを使えませんでした。\n（{error}）"
    return (head + "\n\n" + steps
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
