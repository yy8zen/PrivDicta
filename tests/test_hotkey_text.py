import pytest

from ototype.hotkey import parse_hotkey
from ototype.text import apply_replace, join_lines


@pytest.mark.parametrize("text, expected", [
    ("ctrl+alt+space", "<ctrl>+<alt>+<space>"),
    ("Ctrl + Option + Space", "<ctrl>+<alt>+<space>"),
    ("ctrl+shift+d", "<ctrl>+<shift>+d"),
    ("win+h", "<cmd>+h"),
    ("f9", "<f9>"),
])
def test_parse_hotkey(text, expected):
    assert parse_hotkey(text) == expected


@pytest.mark.parametrize("text", ["", "a", "space", "ctrl+hyper+a", "ctrl+nosuchkey"])
def test_parse_hotkey_rejects(text):
    with pytest.raises(ValueError):
        parse_hotkey(text)


def test_pynput_accepts_parsed_hotkey():
    keyboard = pytest.importorskip("pynput.keyboard", exc_type=ImportError)
    for text in ["ctrl+alt+space", "ctrl+shift+d", "f9", "cmd+pageup"]:
        keyboard.HotKey.parse(parse_hotkey(text))


def test_apply_replace_prefers_longer():
    table = {"ディスコ": "disco", "ディスコード": "Discord"}
    assert apply_replace("ディスコードを開く", table) == "Discordを開く"


def test_join_lines():
    assert join_lines([" 今日は ", "", "晴れです。"]) == "今日は晴れです。"
