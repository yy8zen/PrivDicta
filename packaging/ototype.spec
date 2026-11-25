# PyInstaller の設定。リポジトリのルートで次のように実行する。
#   python scripts/fetch_model.py base
#   pyinstaller packaging/ototype.spec
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
    [str(ROOT / "src" / "ototype" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=collect_dynamic_libs("moonshine_voice"),
    datas=datas,
    hiddenimports=["pynput.keyboard._win32", "pynput.keyboard._darwin", "pynput.keyboard._xorg",
                   "pynput.mouse._win32", "pynput.mouse._darwin", "pynput.mouse._xorg"],
    # moonshine_voice のうち、音声入力に使わない機能（TTS、LoRA 学習など）の依存は入れない
    # setuptools などは実行時に使わない（2026年11月に確認）。使わないものとそのライセンスを抱えない
    excludes=["torch", "transformers", "tkinter", "matplotlib",
              "setuptools", "pkg_resources", "distutils", "_distutils_hack"],
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

# sounddevice は、全 OS 向けの PortAudio を同梱している。使うのは、その OS の64bit版の1つだけ。
# ASIO 版は Steinberg の ASIO SDK を使って作られており、PortAudio 本体（MIT）とは再配布の条件が違うため入れない
def _keep_portaudio(dest: str) -> bool:
    if "portaudio-binaries" not in dest.replace("\\", "/"):
        return True
    name = Path(dest).name
    if name.endswith(".md"):
        return True
    if "asio" in name:
        return False
    if sys.platform == "win32":
        return name == "libportaudio64bit.dll"
    if sys.platform == "darwin":
        return name.endswith(".dylib")
    return False


a.binaries = [b for b in a.binaries if _keep_portaudio(b[0])]
a.datas = [d for d in a.datas if _keep_portaudio(d[0])]

# 同梱したモジュールとファイルの最上位の名前を書き出す。scripts/collect_licenses.py が、
# 依存関係の宣言に出てこないパッケージのライセンスも取りこぼさないように使う
_tops = {entry[0].split(".")[0] for entry in a.pure}
_tops |= {Path(entry[0]).parts[0] for entry in a.datas + a.binaries}
(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "build" / "bundled-top-level.txt").write_text("\n".join(sorted(_tops)), encoding="utf-8")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OtoType",
    console=False,
    # macOS の署名は行わない（要件 R1.3）。BUNDLE の後にアドホック署名する
)
coll = COLLECT(exe, a.binaries, a.datas, name="OtoType")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="OtoType.app",
        bundle_identifier="io.github.ototype",
        info_plist={
            "LSUIElement": True,  # Dock に出さず、メニューバーだけに常駐する
            "NSMicrophoneUsageDescription": "音声入力のためにマイクを使います。音声は外部に送信しません。",
            "CFBundleShortVersionString": "0.2.0",
        },
    )
