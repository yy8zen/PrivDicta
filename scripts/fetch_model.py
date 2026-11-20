"""同梱する日本語モデルを models/ にダウンロードする（ビルド前に1回実行する）。

    python scripts/fetch_model.py                # small-streaming-ja（同梱する標準のモデル）
    python scripts/fetch_model.py tiny-streaming # tiny-streaming-ja

アプリ本体はネットワーク通信をしない（要件 R2.3）。ダウンロードはこのスクリプトだけが行う。
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from moonshine_dictate.engine import MODEL_DIRS  # noqa: E402


def main(argv: list[str]) -> int:
    from moonshine_voice import ModelArch
    from moonshine_voice.download import get_model_for_language

    arch_key = argv[0] if argv else "small-streaming"
    dirname, arch_name = MODEL_DIRS[arch_key]
    dest = ROOT / "models" / dirname
    with tempfile.TemporaryDirectory() as tmp:
        path, _ = get_model_for_language("ja", ModelArch[arch_name], cache_root=Path(tmp))
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(path, dest)
    total = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"{dest} に保存しました（{total / 1e6:.1f}MB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
