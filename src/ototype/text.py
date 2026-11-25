"""認識結果の後処理。"""

from __future__ import annotations

import re

# 日本語の文字（ひらがな、カタカナ、漢字、全角の記号と英数字、和文の句読点）
_JA = r"　-〿぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿＀-￯"
# 日本語の文字に挟まれた空白。base モデルは「そ の 中 で」のように文字の間に空白を入れることがある
_SPACE_IN_JA = re.compile(rf"(?<=[{_JA}])[ \t　]+(?=[{_JA}])")

PUNCTUATION_MODES = ("keep", "add", "remove")
_PUNCT = "、。，．！？"
_SENTENCE_END = "。！？!?…」』）)"


def normalize_spaces(text: str) -> str:
    """日本語の文字の間の空白を取り除く。英単語どうしの間の空白は残す。"""
    return _SPACE_IN_JA.sub("", text).strip()


def apply_punctuation(text: str, mode: str) -> str:
    """句読点の扱いを設定に合わせる。

    keep   : 認識結果のまま
    add    : 区切りの終わりに句点（。）がなければ足す
    remove : 和文の句読点（、。，．！？）を取り除く
    """
    if not text:
        return text
    if mode == "remove":
        return text.translate({ord(c): None for c in _PUNCT})
    if mode == "add" and text[-1] not in _SENTENCE_END:
        return text + "。"
    return text


def apply_replace(text: str, table: dict[str, str]) -> str:
    """置換表を適用する。長い語から先に置き換え、短い語が長い語の一部を壊さないようにする。"""
    for src in sorted(table, key=len, reverse=True):
        text = text.replace(src, table[src])
    return text


def postprocess(text: str, punctuation: str, table: dict[str, str]) -> str:
    """1つの区切りの認識結果を整える。置換表は利用者の指定なので最後に適用する。"""
    text = normalize_spaces(text)
    text = apply_punctuation(text, punctuation)
    return apply_replace(text, table)


def join_lines(lines: list[str]) -> str:
    """確定した区切りをつなぐ。日本語なので区切りの間に空白は入れない。"""
    return "".join(s.strip() for s in lines if s.strip())
