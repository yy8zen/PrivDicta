"""設定ファイル（TOML）の読み込みと検証（要件 R6）。

誤った項目は標準値に戻して動かし、誤りの内容を `Config.errors` に入れて返す（要件 R6.4）。
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from privdicta.platform_info import IS_MACOS

INSERT_METHODS = ("clipboard", "live")
LOG_LEVELS = ("error", "info", "debug")
MODEL_ARCHS = ("base", "small-streaming", "tiny-streaming")
PUNCTUATION_MODES = ("keep", "add", "remove")
DEFAULT_MODEL_ARCH = "base"


def default_hotkey() -> str:
    return "ctrl+option+space" if IS_MACOS else "ctrl+alt+space"


@dataclass
class Config:
    hotkey: str = field(default_factory=default_hotkey)
    silence_timeout_sec: int = 60
    insert_method: str = "clipboard"
    restore_clipboard: bool = True
    input_device: str = ""
    sound: bool = True
    autostart: bool = False
    log_level: str = "info"
    model_dir: str = ""
    model_arch: str = DEFAULT_MODEL_ARCH
    punctuation: str = "keep"
    save_recordings: bool = False
    replace: dict[str, str] = field(default_factory=dict)
    # 読み込み時に見つかった誤り。設定項目ではない
    errors: list[str] = field(default_factory=list, compare=False)


TEMPLATE = """\
# PrivDicta の設定ファイル
# トレイのメニューの「設定…」から画面で変更できます。
# このファイルを直接編集した場合は、メニューの「設定の再読み込み」で反映されます。
# 項目を消すと標準値で動きます。

# 録音の開始・終了に使うキー。修飾キーは ctrl / alt（option）/ shift / cmd（win）
# 例: "ctrl+alt+space"、"ctrl+shift+d"、"f9"
hotkey = {hotkey}

# 無音がこの秒数続いたら録音を終了します
silence_timeout_sec = {silence_timeout_sec}

# テキストの入れ方
#   "clipboard" : 録音の終了時に、全文をまとめて貼り付けます
#   "live"      : 話の区切りが確定するたびに入れます
insert_method = {insert_method}

# 句読点の扱い
#   "keep"   : 認識結果のまま
#   "add"    : 区切りの終わりに「。」がなければ足す
#   "remove" : 句読点（、。！？）を取り除く
punctuation = {punctuation}

# 貼り付けた後に元のクリップボードの内容に戻すか
restore_clipboard = {restore_clipboard}

# マイクのデバイス名（一部だけでも可）。空なら OS の既定のマイクを使います
input_device = {input_device}

# 録音の開始・終了時に効果音を鳴らすか
sound = {sound}

# OS にログインしたときに自動で起動するか
autostart = {autostart}

# ログの出力量: "error" / "info" / "debug"
log_level = {log_level}

# 認識の精度を調べるために、録音と認識結果を PC の中に保存するか。保存したものはどこにも送りません
# 保存先は、この設定ファイルと同じ場所の recordings フォルダです
save_recordings = {save_recordings}

# 使うモデルの種類
#   "base"            : 標準。区切りが確定してから文字が出ます
#   "small-streaming" : 話している途中から文字が出るが、精度は低い（配布物には入っていません）
#   "tiny-streaming"  : 小さく速いが精度はさらに低い（配布物には入っていません）
model_arch = {model_arch}
# モデルの置き場所。空なら同梱のモデル置き場を使います
model_dir = {model_dir}

# 認識結果の置換表。左の文字列を右の文字列に置き換えます
# 例: "でぃすこーど" = "Discord"
[replace]
{replace}"""


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    # JSON の文字列のエスケープ（\" や \n、\uXXXX など）は、TOML の基本文字列でもそのまま使える
    return json.dumps(str(value), ensure_ascii=False)


def render(cfg: Config) -> str:
    """設定を、説明のコメント付きの TOML にする。設定画面からの保存に使う。"""
    values = {name: _toml_value(getattr(cfg, name))
              for name in Config.__dataclass_fields__ if name not in ("errors", "replace")}
    values["replace"] = "".join(f"{_toml_value(src)} = {_toml_value(dst)}\n"
                                for src, dst in cfg.replace.items())
    return TEMPLATE.format(**values)


def save(path: Path, cfg: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".toml.tmp")
    tmp.write_text(render(cfg), encoding="utf-8")
    tmp.replace(path)  # 書きかけのファイルが残らないよう、置き換えで保存する


def write_default(path: Path) -> None:
    save(path, Config())


def load(path: Path) -> Config:
    """設定ファイルを読む。ファイルがなければ標準値のファイルを作る（要件 R6.2）。"""
    if not path.exists():
        write_default(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        cfg = Config()
        cfg.errors.append(f"設定ファイルの書式に誤りがあるため、すべて標準値で動きます: {e}")
        return cfg
    except OSError as e:
        cfg = Config()
        cfg.errors.append(f"設定ファイルを読めないため、すべて標準値で動きます: {e}")
        return cfg
    return parse(raw)


def parse(raw: dict) -> Config:
    cfg = Config()
    errors = cfg.errors

    def take(key: str, expected: type, choices: tuple | None = None, check=None):
        if key not in raw:
            return
        value = raw[key]
        default = getattr(cfg, key)
        # bool は int のサブクラスなので、int の項目に true を書いた誤りを先に弾く
        ok = isinstance(value, expected) and not (expected is int and isinstance(value, bool))
        if ok and choices is not None:
            ok = value in choices
        if ok and check is not None:
            ok = check(value)
        if ok:
            setattr(cfg, key, value)
        else:
            hint = f"（使える値: {', '.join(choices)}）" if choices else ""
            errors.append(f"{key} = {value!r} は使えないため、標準値 {default!r} で動きます{hint}")

    take("hotkey", str, check=_valid_hotkey)
    take("silence_timeout_sec", int, check=lambda v: 1 <= v <= 3600)
    take("insert_method", str, INSERT_METHODS)
    take("restore_clipboard", bool)
    take("input_device", str)
    take("sound", bool)
    take("autostart", bool)
    take("log_level", str, LOG_LEVELS)
    take("model_dir", str)
    take("model_arch", str, MODEL_ARCHS)
    take("punctuation", str, PUNCTUATION_MODES)
    take("save_recordings", bool)

    if "replace" in raw:
        table = raw["replace"]
        if isinstance(table, dict):
            for src, dst in table.items():
                if isinstance(dst, str) and src:
                    cfg.replace[src] = dst
                else:
                    errors.append(f"replace の {src!r} = {dst!r} は文字列ではないため、無視します")
        else:
            errors.append("replace は表（[replace]）で書いてください。置換は行いません")

    known = set(Config.__dataclass_fields__) - {"errors"}
    for key in raw:
        if key not in known:
            errors.append(f"{key} という設定項目はないため、無視します")
    return cfg


def _valid_hotkey(value: str) -> bool:
    from privdicta.hotkey import parse_hotkey

    try:
        parse_hotkey(value)
    except ValueError:
        return False
    return True
