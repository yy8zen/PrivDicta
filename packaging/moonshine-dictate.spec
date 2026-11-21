# PyInstaller の設定。リポジトリのルートで次のように実行する。
#   python scripts/fetch_model.py
#   pyinstaller packaging/moonshine-dictate.spec
# -*- mode: python -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent
MODEL = ROOT / "models" / "small-streaming-ja"
if not MODEL.is_dir():
    raise SystemExit(f"{MODEL} がありません。先に python scripts/fetch_model.py を実行してください")

datas = [
    (str(MODEL), "models/small-streaming-ja"),
    (str(ROOT / "LICENSE"), "."),
]
# Moonshine の同梱ライセンス全文（要件 R7.2）。ファイルがあれば入れる
community_license = ROOT / "packaging" / "MOONSHINE-COMMUNITY-LICENSE.txt"
if community_license.exists():
    datas.append((str(community_license), "."))
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
)
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
            "CFBundleShortVersionString": "0.1.0",
        },
    )
