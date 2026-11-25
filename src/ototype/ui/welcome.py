"""初回起動時に出す使い方の画面。トレイのメニューの「使い方」からも開ける。

起動してもタスクトレイに入るだけで画面が出ないため、何が起きたか分からない利用者がいた。
"""

from __future__ import annotations

import re
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ototype import __version__
from ototype.platform_info import IS_MACOS, IS_WINDOWS, config_dir

POWERED_BY = "Powered by Moonshine AI"


def _hotkey_label(hotkey: str) -> str:
    names = {"ctrl": "Ctrl", "alt": "Alt", "option": "Option", "shift": "Shift", "cmd": "Command",
             "win": "Win", "space": "Space", "enter": "Enter", "tab": "Tab"}
    return " + ".join(names.get(p, p.upper() if len(p) == 1 else p.capitalize())
                      for p in hotkey.split("+"))


def platform_texts() -> dict[str, str]:
    """OS ごとに異なる説明。"""
    folder = escape(str(config_dir()))
    if IS_WINDOWS:
        return {
            "where": "画面右下のタスクトレイ（表示されていなければ「^」の中）",
            "launch": "スタートメニューの「OtoType」から起動します。",
            "uninstall": ("「設定 &gt; アプリ &gt; インストールされているアプリ」で OtoType の"
                          "「…」から「アンインストール」を選びます。"
                          f"設定とログを消すには、<code>{folder}</code> フォルダも削除してください。"),
        }
    if IS_MACOS:
        return {
            "where": "画面右上のメニューバー",
            "launch": "「アプリケーション」フォルダの OtoType を開きます。",
            "uninstall": ("メニューバーのアイコンから「終了」を選び、「アプリケーション」フォルダの"
                          "OtoType をゴミ箱に入れます。"
                          f"設定とログを消すには、<code>{folder}</code> フォルダも削除してください。"
                          "「システム設定 &gt; プライバシーとセキュリティ &gt; アクセシビリティ」の一覧からも"
                          "削除しておくと確実です。"),
        }
    return {
        "where": "パネル（タスクバー）の通知領域",
        "launch": "ダウンロードした AppImage のファイルを実行します。",
        "uninstall": ("トレイのメニューから「終了」を選び、AppImage のファイルを削除します。"
                      f"設定とログを消すには、<code>{folder}</code> フォルダも削除してください。"),
    }


def build_html(hotkey: str) -> str:
    t = platform_texts()
    key = escape(_hotkey_label(hotkey))
    html = f"""
<h2>OtoType へようこそ</h2>
<p>話した日本語を、カーソルのある場所に入力するアプリです。音声の認識はすべてこの PC の中で行い、
インターネットには接続しません。</p>
<p>アプリは{t["where"]}にマイクのアイコンとして常駐しています。
アイコンが黄色の間はモデルを読み込んでいます。灰色になったら使えます。</p>

<h3>使い方</h3>
<ol>
<li>文字を入れたい場所（メモ帳やブラウザの入力欄など）をクリックします。</li>
<li><b>{key}</b> を押します。画面の下に録音ウィンドウが出て、マイクのボタンが赤くなります。</li>
<li>話します。</li>
<li>もう一度 <b>{key}</b> を押すか、録音ウィンドウのマイクのボタンを押すと、録音が終わって文字が入ります。
60秒間何も話さなかった場合も終わります。</li>
</ol>

<h3>設定を変える</h3>
<p>アイコンを右クリックして「設定…」を選びます。ホットキー、マイク、句読点の入れ方、
置換表（例：「でぃすこーど」を「Discord」にする）などを変えられます。</p>

<h3>次に起動するとき</h3>
<p>{t["launch"]}下の「ログインしたときに自動で起動する」にチェックを入れておくと、毎回起動する必要はありません。</p>

<h3>アンインストール</h3>
<p>{t["uninstall"]}</p>

<p style="color: gray;">この画面は、アイコンのメニューの「使い方」からいつでも開けます。<br>
バージョン {escape(__version__)} ・ {POWERED_BY}<br>
日本語の音声認識モデルは Moonshine AI Community License のもとで配布しています。</p>
"""
    # 文の途中の改行は、Qt の表示で余分な空白になる。タグとタグの間以外の改行を取り除く
    return re.sub(r"(?<=[^>])\n(?=[^<])", "", html)


class WelcomeDialog(QDialog):
    settings_requested = Signal()

    def __init__(self, hotkey: str, autostart: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("OtoType の使い方")
        self.resize(560, 640)

        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(build_html(hotkey))

        self.autostart = QCheckBox("ログインしたときに自動で起動する")
        self.autostart.setChecked(autostart)

        powered = QLabel(POWERED_BY)
        powered.setStyleSheet("color: gray;")
        settings = QPushButton("設定を開く")
        settings.clicked.connect(self._open_settings)
        close = QPushButton("閉じる")
        close.setDefault(True)
        close.clicked.connect(self.accept)

        bottom = QHBoxLayout()
        bottom.addWidget(powered)
        bottom.addStretch()
        bottom.addWidget(settings)
        bottom.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(body, 1)
        layout.addWidget(self.autostart, 0, Qt.AlignLeft)
        layout.addLayout(bottom)

    def _open_settings(self) -> None:
        self.settings_requested.emit()
        self.accept()
