import pytest

from privdicta.text import apply_punctuation, normalize_spaces, postprocess

# 2026年11月、Windows 11 の実機で base モデルが出力した文の一部
REAL_OUTPUT = [
    ("そ の 中 で 結いい感じに", "その中で結いい感じに"),
    ("キ ッ ト ハ ブ今 開 発 し て も ら っ た一 般 に 公 開 し た い と必要なことを。",
     "キットハブ今開発してもらった一般に公開したいと必要なことを。"),
    ("今 エ グ ゼ を 立 ち 上こう。", "今エグゼを立ち上こう。"),
    ("あ っ た と こ ろ の 説 明ほう。", "あったところの説明ほう。"),
    ("ぶ っ ち ゃ け 使 わ な い な っ て いふうに思いました。", "ぶっちゃけ使わないなっていふうに思いました。"),
]


@pytest.mark.parametrize("raw, expected", REAL_OUTPUT)
def test_normalize_spaces_real_output(raw, expected):
    assert normalize_spaces(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("Visual Studio Code を開く", "Visual Studio Code を開く"),  # 英単語の間と、英語と日本語の間は残す
    ("全角　空白 も", "全角空白も"),
    ("  前後の空白  ", "前後の空白"),
    ("読点 、 の前後", "読点、の前後"),
])
def test_normalize_spaces_keeps_latin(raw, expected):
    assert normalize_spaces(raw) == expected


@pytest.mark.parametrize("mode, raw, expected", [
    ("keep", "今日は晴れ", "今日は晴れ"),
    ("add", "今日は晴れ", "今日は晴れ。"),
    ("add", "今日は晴れ。", "今日は晴れ。"),
    ("add", "本当？", "本当？"),
    ("add", "「はい」", "「はい」"),
    ("remove", "はい、今日は晴れです。本当？", "はい今日は晴れです本当"),
    ("remove", "version 0.2.0", "version 0.2.0"),  # 半角のピリオドは消さない
    ("add", "", ""),
])
def test_apply_punctuation(mode, raw, expected):
    assert apply_punctuation(raw, mode) == expected


def test_postprocess_order():
    # 空白の除去 → 句読点 → 置換表の順。置換表は空白を除いた後の文字列に当たる
    assert postprocess("き っ と は ぶ を 開く", "add", {"きっとはぶ": "GitHub"}) == "GitHubを開く。"
