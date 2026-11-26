import re
import tomllib
from pathlib import Path

import privdicta

ROOT = Path(__file__).resolve().parents[1]


def test_versions_match():
    # リリースのとき、タグとこの番号が一致することをビルドで確かめている（.github/workflows/build.yml）
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == privdicta.__version__


def test_release_notes_exist_for_current_version():
    assert (ROOT / "docs" / "release-notes" / f"v{privdicta.__version__}.md").is_file()


def test_spec_reads_version_from_package():
    spec = (ROOT / "packaging" / "privdicta.spec").read_text(encoding="utf-8")
    assert re.search(r'"CFBundleShortVersionString": VERSION', spec)
