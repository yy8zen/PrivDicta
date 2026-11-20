"""コマンドラインの入口。

    moonshine-dictate            常駐を開始する
    moonshine-dictate toggle     録音の開始・終了を切り替える（start / stop / reload / quit も使える）
"""

from __future__ import annotations

import argparse
import sys

from moonshine_dictate import __version__

CLIENT_COMMANDS = ("toggle", "start", "stop", "reload", "quit")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="moonshine-dictate",
                                     description="ローカルで動く日本語音声入力ツール")
    parser.add_argument("command", nargs="?", choices=CLIENT_COMMANDS,
                        help="常駐中のプロセスに送る指示。省略すると常駐を開始する")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.command:
        return _client(args.command)
    return _run()


def _client(command: str) -> int:
    from PySide6.QtCore import QCoreApplication

    from moonshine_dictate import ipc

    _app = QCoreApplication(sys.argv[:1])
    reply = ipc.send(command)
    if reply is None:
        print("moonshine-dictate は起動していません", file=sys.stderr)
        return 1
    print(reply)
    return 0 if reply.startswith("ok") else 1


def _run() -> int:
    from PySide6.QtWidgets import QApplication

    from moonshine_dictate.app import DictateApp, setup_logging

    setup_logging()
    qt_app = QApplication(sys.argv[:1])
    qt_app.setApplicationName("moonshine-dictate")
    qt_app.setQuitOnLastWindowClosed(False)  # 録音ウィンドウを閉じても終了しない
    app = DictateApp(qt_app)
    if not app.start():
        print("moonshine-dictate はすでに起動しています", file=sys.stderr)
        return 1
    return qt_app.exec()
