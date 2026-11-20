"""認識結果の後処理。"""

from __future__ import annotations


def apply_replace(text: str, table: dict[str, str]) -> str:
    """置換表を適用する。長い語から先に置き換え、短い語が長い語の一部を壊さないようにする。"""
    for src in sorted(table, key=len, reverse=True):
        text = text.replace(src, table[src])
    return text


def join_lines(lines: list[str]) -> str:
    """確定した区切りをつなぐ。日本語なので区切りの間に空白は入れない。"""
    return "".join(s.strip() for s in lines if s.strip())
