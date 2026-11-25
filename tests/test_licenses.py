import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_collect_licenses_writes_notices(tmp_path):
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "collect_licenses.py"),
                             str(tmp_path / "no-bundle"), str(out)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    notices = (out / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
    assert "Powered by Moonshine AI" in notices
    assert "pynput" in notices and "LGPL" in notices
    assert (out / "other" / "LGPL-3.0.txt").is_file()
    assert (out / "other" / "onnxruntime-ThirdPartyNotices.txt").is_file()
