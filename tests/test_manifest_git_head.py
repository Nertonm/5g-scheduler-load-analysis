import importlib.util
import subprocess
from pathlib import Path


def test_manifest_records_current_git_head():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "write_manifest.py"
    spec = importlib.util.spec_from_file_location("write_manifest", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    expected = subprocess.check_output(
        ["git", "-c", f"safe.directory={root}", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    assert module.git_commit(str(root)) == expected
