"""マイクを開けないときに、利用者を OS の設定画面へ案内する（要件 R2.8）。

OS のマイクの権限は、アプリからは変えない。利用者のプライバシーの選択を上書きすることになるうえ、
Windows では PC 全体の設定に管理者権限が要り、組織のポリシーで固定されていることもあるため。

案内するのは、マイクを開くときにエラーになった場合だけとする。Windows 11 Pro の実機で、
マイクの権限がオフのときはマイクを開く時点でエラーになることを確かめた（2026年11月）。
「完全な無音が続いたら案内する」方法は、雑音を自動で消すマイクなどで、正常なのに録音を
止めてしまうおそれがあるため採らない。
"""

from __future__ import annotations

from privdicta.platform_info import IS_MACOS, IS_WINDOWS

WINDOWS_SETTINGS_URL = "ms-settings:privacy-microphone"
MACOS_SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"


def settings_url() -> str | None:
    """マイクの権限を変える OS の設定画面の URL。Linux にはないので None。"""
    if IS_WINDOWS:
        return WINDOWS_SETTINGS_URL
    if IS_MACOS:
        return MACOS_SETTINGS_URL
    return None


def help_text(error: str) -> str:
    """利用者に見せる説明。error はマイクを開けなかったときのエラーの内容。"""
    if IS_WINDOWS:
        steps = ("「設定 > プライバシーとセキュリティ > マイク」で、「マイクへのアクセス」と"
                 "「デスクトップ アプリがマイクにアクセスできるようにする」がオンになっているかを確かめてください。")
    elif IS_MACOS:
        steps = "「システム設定 > プライバシーとセキュリティ > マイク」で、PrivDicta がオンになっているかを確かめてください。"
    else:
        steps = "OS のサウンドの設定で、マイクがつながっているかを確かめてください。"
    return (f"マイクを使えませんでした。\n（{error}）\n\n" + steps
            + "\n\nマイクが複数ある場合は、PrivDicta の設定画面で使うマイクを選び直してください。")
