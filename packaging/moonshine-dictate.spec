# PyInstaller の設定。リポジトリのルートで次のように実行する。
#   python scripts/fetch_model.py base
#   pyinstaller packaging/moonshine-dictate.spec
# -*- mode: python -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent
# 同梱するモデル。small-streaming は精度が低く使われなかったため、base だけを入れる（要件 R2.5）
MODELS = ["base-ja"]

# ライセンス全文、帰属表示、使い方（要件 R7.2）。Moonshine AI Community License の配布条件を満たすために必須
datas = [
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "packaging" / "MOONSHINE-LICENSE.txt"), "."),
    (str(ROOT / "packaging" / "NOTICE.txt"), "."),
    (str(ROOT / "docs" / "user-guide.md"), "."),
]
for name in MODELS:
    model = ROOT / "models" / name
    if not model.is_dir():
        raise SystemExit(f"{model} がありません。先に python scripts/fetch_model.py を実行してください")
    datas.append((str(model), f"models/{name}"))
datas += collect_data_files("moonshine_voice", excludes=["**/*.wav", "assets/tiny-en/**"])

a = Analysis(
    [str(ROOT / "src" / "moonshine_dictate" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=collect_dynamic_libs("moonshine_voice"),
    datas=datas,
    hiddenimports=["pynput.keyboard._win32", "pynput.keyboard._darwin", "pynput.keyboard._xorg",
                   "pynput.mouse._win32", "pynput.mouse._darwin", "pynput.mouse._xorg"],
    # moonshine_voice のうち、音声入力に使わない機能（TTS、LoRA 学習など）の依存は入れない
    excludes=["torch", "transformers", "tkinter", "matplotlib"],
    # LGPL の Python パッケージは、利用者が差し替えられるように .py のまま同梱する（要件 R7.4）
    module_collection_mode={"pynput": "py", "Xlib": "py", "PySide6": "py", "shiboken6": "py"},
)

if sys.platform.startswith("linux"):
    # Qt の GTK テーマの部品（libqgtk3）と、それだけが使うライブラリを外す。
    # 使っていない部品のために、GTK 一式とそのライセンスを配布物に抱えないため（要件 R7.4）
    GTK_ONLY = ("libqgtk3", "libgtk-3", "libgdk-3", "libgdk_pixbuf", "libatk-1.0", "libatk-bridge",
                "libatspi", "libcairo", "libpango", "libepoxy", "libfribidi", "libthai", "libdatrie",
                "libpixman", "libharfbuzz", "libgraphite2", "libjpeg")
    a.binaries = [b for b in a.binaries
                  if not Path(b[0]).name.startswith(GTK_ONLY)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="moonshine-dictate",
    console=False,
    # macOS の署名は行わない（要件 R1.3）。BUNDLE の後にアドホック署名する
)
coll = COLLECT(exe, a.binaries, a.datas, name="moonshine-dictate")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="moonshine-dictate.app",
        bundle_identifier="io.github.moonshine-dictate",
        info_plist={
            "LSUIElement": True,  # Dock に出さず、メニューバーだけに常駐する
            "NSMicrophoneUsageDescription": "音声入力のためにマイクを使います。音声は外部に送信しません。",
            "CFBundleShortVersionString": "0.2.0",
        },
    )
