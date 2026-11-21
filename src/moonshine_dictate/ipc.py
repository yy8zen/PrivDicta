"""常駐プロセスへの指示（要件 R3.4）と、二重起動の防止。

Qt の QLocalServer を使う。Windows では名前付きパイプ、macOS と Linux では UNIX ドメインソケットになる。
"""

from __future__ import annotations

import getpass
import logging
import re
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)

COMMANDS = ("toggle", "start", "stop", "reload", "quit", "ping")
TIMEOUT_MS = 2000


def server_name() -> str:
    user = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser() or "user")
    return f"moonshine-dictate-{user}"


def send(command: str) -> str | None:
    """常駐プロセスに指示を送り、返事を返す。常駐プロセスがなければ None。"""
    sock = QLocalSocket()
    sock.connectToServer(server_name())
    if not sock.waitForConnected(TIMEOUT_MS):
        return None
    sock.write((command + "\n").encode("utf-8"))
    sock.flush()
    sock.waitForBytesWritten(TIMEOUT_MS)
    reply = b""
    while sock.waitForReadyRead(TIMEOUT_MS):
        reply += bytes(sock.readAll())
        if reply.endswith(b"\n"):
            break
    sock.disconnectFromServer()
    return reply.decode("utf-8", errors="replace").strip()


class CommandServer(QObject):
    def __init__(self, handler: Callable[[str], str]):
        super().__init__()
        self._handler = handler
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.UserAccessOption)
        self._server.newConnection.connect(self._on_connection)

    def listen(self) -> bool:
        """指示の受付を始める。ほかに常駐中のプロセスがあれば False を返す。"""
        name = server_name()
        # UserAccessOption を付けた listen() は、既存のソケットを黙って上書きする（Unix の Qt の動作）。
        # 先に応答を確かめないと、常駐中のプロセスから受付を奪ってしまう
        if send("ping") is not None:
            return False
        if self._server.listen(name):
            return True
        # 前回の異常終了でソケットファイルが残っている場合は、消してからやり直す
        QLocalServer.removeServer(name)
        return self._server.listen(name)

    def close(self) -> None:
        self._server.close()

    def _on_connection(self) -> None:
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._on_ready(s))
            # 接続と同時に届いた指示は readyRead が出ないことがあるので、先に一度読む
            self._on_ready(sock)

    def _on_ready(self, sock: QLocalSocket) -> None:
        if not sock.canReadLine():
            return
        command = bytes(sock.readLine()).decode("utf-8", errors="replace").strip()
        if command in COMMANDS:
            reply = self._handler(command)
        else:
            reply = f"error: unknown command {command!r}"
        sock.write((reply + "\n").encode("utf-8"))
        sock.flush()
        sock.disconnectFromServer()
