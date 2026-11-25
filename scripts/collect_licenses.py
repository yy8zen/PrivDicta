"""配布物に入るサードパーティのソフトウェアのライセンスを集める（要件 R7.4）。

    python scripts/collect_licenses.py <PyInstaller の _internal> <出力先> [同梱した最上位の名前の一覧]

3つ目の引数は、privdicta.spec が書き出す build/bundled-top-level.txt。省略すると、依存関係の
宣言だけからパッケージを決める。

PyInstaller で固めた後に実行する。出力先には次のものを作る。
- THIRD-PARTY-NOTICES.md : 同梱しているソフトウェアとライセンス、ソースの入手先の一覧
- python/                : Python パッケージごとのライセンスのファイル
- other/                 : packaging/licenses/ のライセンス本文（LGPL、GPL、ONNX Runtime など）
- linux/                 : Linux 版で同梱した OS のライブラリの Debian 著作権ファイル

ライセンスのファイルが見つからないパッケージがあれば、一覧に「要確認」と書き、終了コード 1 を返す。
ビルドを止めて、人が確かめるためである。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import sysconfig
from datetime import date
from importlib import metadata
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "privdicta"
LICENSE_FILE = re.compile(r"(LICEN[CS]E|COPYING|NOTICE|AUTHORS|COPYRIGHT)", re.I)
# LGPL のパッケージ。利用者が差し替えられるよう、.py のまま同梱している（privdicta.spec）
LGPL = {"pyside6-essentials", "shiboken6", "pynput", "python-xlib"}


def runtime_distributions(bundled_tops: list[str] | None = None) -> list[metadata.Distribution]:
    """privdicta の実行時の依存パッケージ（推移的に全部）と、実際に同梱した最上位の名前を持つパッケージ。"""
    env = default_environment()
    seen: dict[str, metadata.Distribution] = {}
    stack = [PROJECT]
    if bundled_tops:
        owners = metadata.packages_distributions()
        for top in bundled_tops:
            stack.extend(owners.get(top, []))
    while stack:
        name = stack.pop()
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        seen[key] = dist
        for spec in dist.requires or []:
            req = Requirement(spec)
            if req.marker is None or req.marker.evaluate({**env, "extra": ""}):
                stack.append(req.name)
    seen.pop(PROJECT, None)
    return sorted(seen.values(), key=lambda d: d.metadata["Name"].lower())


def license_of(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    expr = meta.get("License-Expression")
    if expr:
        return expr
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or []
                   if c.startswith("License ::")]
    if classifiers:
        return " / ".join(classifiers)
    text = (meta.get("License") or "").strip()
    return text.splitlines()[0][:80] if text else "不明"


def copy_python_licenses(out: Path, bundled_tops: list[str] | None = None) -> tuple[list[dict], list[str]]:
    rows, missing = [], []
    for dist in runtime_distributions(bundled_tops):
        name, version = dist.metadata["Name"], dist.version
        dest = out / "python" / f"{name}-{version}"
        copied = []
        for f in dist.files or []:
            if LICENSE_FILE.search(f.name) and not f.name.endswith((".py", ".pyc")):
                src = Path(dist.locate_file(f))
                if src.is_file():
                    dest.mkdir(parents=True, exist_ok=True)
                    target = dest / f.name
                    if target.exists():  # 同じ名前のファイルが複数ある（numpy など）
                        target = dest / f"{f.parent.name}-{f.name}"
                    shutil.copyfile(src, target)
                    copied.append(target.name)
        if not copied and name.lower().replace("_", "-") in LGPL:
            # PySide6 と shiboken6 のパッケージにはライセンスのファイルが入っていない。
            # 本文は packaging/licenses/ の LGPL-3.0 と GPL-3.0 を同梱している
            copied = ["other/LGPL-3.0.txt", "other/GPL-3.0.txt"]
        if not copied and name.lower().startswith("pyobjc"):
            # pyobjc の一部のパッケージ（pyobjc-core など）にはライセンスのファイルが入っていない。
            # 本文（MIT）は開発元のリポジトリの pyobjc-core/License.txt を packaging/licenses/ に置いている
            copied = ["other/pyobjc-LICENSE.txt"]
        if not copied:
            missing.append(name)
        rows.append({"name": name, "version": version, "license": license_of(dist),
                     "files": copied, "lgpl": name.lower().replace("_", "-") in LGPL})
    return rows, missing


def copy_python_runtime_license(out: Path) -> str | None:
    candidates = [Path(sys.base_prefix) / "LICENSE.txt",
                  Path(sysconfig.get_paths()["stdlib"]) / "LICENSE.txt"]
    for src in candidates:
        if src.is_file():
            dest = out / "python" / f"Python-{sys.version.split()[0]}"
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest / "LICENSE.txt")
            return sys.version.split()[0]
    return None


def copy_static_licenses(out: Path) -> list[str]:
    dest = out / "other"
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for src in sorted((ROOT / "packaging" / "licenses").glob("*.txt")):
        shutil.copyfile(src, dest / src.name)
        names.append(src.name)
    return names


def linux_system_packages(bundle: Path, out: Path) -> tuple[list[tuple[str, str, str]], list[str]]:
    """PyInstaller が OS から持ってきた共有ライブラリの Debian パッケージと著作権ファイルを集める。"""
    if not sys.platform.startswith("linux") or not shutil.which("dpkg"):
        return [], []
    names = sorted(p.name for p in bundle.iterdir()
                   if ".so" in p.name and p.is_file() and not p.is_symlink())
    packages: dict[str, tuple[str, str]] = {}
    unknown = []
    for name in names:
        result = subprocess.run(["dpkg", "-S", name], capture_output=True, text=True)
        owners = {line.split(":")[0] for line in result.stdout.splitlines()
                  if line.rstrip().endswith("/" + name)}
        if not owners:
            unknown.append(name)  # Python パッケージに入っていた共有ライブラリ。python/ 側で扱う
            continue
        for pkg in owners:
            if pkg in packages:
                continue
            q = subprocess.run(["dpkg-query", "-W", "-f=${source:Package}\t${Version}", pkg],
                               capture_output=True, text=True)
            source, version = (q.stdout.split("\t") + ["", ""])[:2]
            packages[pkg] = (source or pkg, version)
    dest = out / "linux"
    rows = []
    for pkg, (source, version) in sorted(packages.items()):
        copyright_file = Path("/usr/share/doc") / pkg.split(":")[0] / "copyright"
        if copyright_file.is_file():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(copyright_file, dest / f"{pkg.split(':')[0]}.copyright")
        rows.append((pkg, version, source))
    return rows, unknown


def qt_version() -> str:
    try:
        from PySide6 import QtCore

        return QtCore.qVersion()
    except Exception:
        return "不明"


def write_notices(out: Path, py_rows, missing, python_version, static_files, linux_rows) -> None:
    qt = qt_version()
    qt_minor = ".".join(qt.split(".")[:2])
    lines = [
        "# サードパーティのソフトウェアとライセンス",
        "",
        f"この一覧は PrivDicta の配布物に同梱しているソフトウェアのものです（{date.today():%Y-%m-%d} にビルド時に自動生成）。",
        "各ライセンスの本文は、このファイルと同じフォルダの `python/`、`other/`、`linux/` にあります。",
        "",
        "## 音声認識モデル",
        "",
        "- 日本語の音声認識モデル base-ja：Moonshine AI Community License（`MOONSHINE-LICENSE.txt` の SECTION 2、帰属表示は `NOTICE.txt`）",
        "  - This Moonshine AI Model is licensed under the Moonshine AI Community License, Copyright © Moonshine AI Ltd. All Rights Reserved",
        "  - Powered by Moonshine AI",
        "",
        "## LGPL のライブラリについて",
        "",
        "次のライブラリは GNU Lesser General Public License（LGPL）のもとで同梱しています。どれも変更していません。"
        "共有ライブラリと Python のソースファイルのまま同梱しているので、利用者が自分で変更したものに差し替えられます。"
        "PySide6 と shiboken6 は、LGPL-3.0 と GPL から選べるライセンスのうち LGPL-3.0 を選んで使っています。"
        "ライセンス本文は `other/LGPL-3.0.txt`、`other/GPL-3.0.txt`、`other/LGPL-2.1.txt` にあります。",
        "",
        f"- Qt {qt}（PySide6 に含まれる）：LGPL-3.0。ソース：https://download.qt.io/archive/qt/{qt_minor}/{qt}/single/ 。"
        "Qt が含むサードパーティのライセンス：https://doc.qt.io/qt-6/licenses-used-in-qt.html",
    ]
    for r in py_rows:
        if r["lgpl"]:
            lines.append(f"- {r['name']} {r['version']}：{r['license']}。"
                         f"ソース：https://pypi.org/project/{r['name']}/{r['version']}/#files")
    lines += [
        "",
        "## Python パッケージ",
        "",
        "| パッケージ | バージョン | ライセンス | ソース |",
        "| --- | --- | --- | --- |",
    ]
    for r in py_rows:
        lic = r["license"].replace("|", "/")
        lines.append(f"| {r['name']} | {r['version']} | {lic} | https://pypi.org/project/{r['name']}/{r['version']}/ |")
    if python_version:
        lines.append(f"| Python（実行環境） | {python_version} | PSF-2.0 | https://www.python.org/downloads/source/ |")
    lines += [
        "",
        "## Python パッケージに含まれるネイティブのライブラリ",
        "",
        "- ONNX Runtime 1.23.2（moonshine-voice に含まれる）：MIT。`other/onnxruntime-LICENSE.txt`、"
        "ONNX Runtime が含むサードパーティのライセンスは `other/onnxruntime-ThirdPartyNotices.txt`",
        "- PortAudio（sounddevice が使う。Linux 版は OS のパッケージから同梱）：MIT 系。`other/PortAudio-LICENSE.txt`",
        "- OpenBLAS ほか（numpy に含まれる）：numpy のライセンスのファイル（`python/numpy-*/`）に記載",
    ]
    if linux_rows:
        lines += [
            "- AppImage の実行部分（type2-runtime）：MIT。`other/AppImage-type2-runtime-LICENSE.txt`",
            "",
            "## Linux 版で同梱している OS のライブラリ",
            "",
            "ビルドに使った Ubuntu のパッケージから同梱しています。著作権とライセンスは `linux/<パッケージ名>.copyright` にあります。"
            "ソースは https://launchpad.net/ubuntu/+source/<ソースパッケージ名> から入手できます。",
            "",
            "| パッケージ | バージョン | ソースパッケージ |",
            "| --- | --- | --- |",
        ]
        lines += [f"| {pkg} | {ver} | {src} |" for pkg, ver, src in linux_rows]
    if missing:
        lines += ["", "## 要確認", "",
                  "次のパッケージはライセンスのファイルが見つかりませんでした: " + ", ".join(missing)]
    lines += ["", f"同梱しているライセンス本文：{', '.join(static_files)}", ""]
    (out / "THIRD-PARTY-NOTICES.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(errors="replace")
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    bundle, out = Path(argv[0]), Path(argv[1])
    bundled_tops = None
    if len(argv) == 3:
        bundled_tops = [t for t in Path(argv[2]).read_text(encoding="utf-8").split() if t]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    py_rows, missing = copy_python_licenses(out, bundled_tops)
    python_version = copy_python_runtime_license(out)
    static_files = copy_static_licenses(out)
    linux_rows, _ = linux_system_packages(bundle, out) if bundle.is_dir() else ([], [])
    write_notices(out, py_rows, missing, python_version, static_files, linux_rows)
    print(f"{len(py_rows)} 個の Python パッケージ、{len(linux_rows)} 個の OS のパッケージのライセンスを {out} に集めました")
    if missing:
        print("ライセンスのファイルが見つからないパッケージ:", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
