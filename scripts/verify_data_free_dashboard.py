"""Stage the allowlisted Day 14 files and run the same suite locally and in CI."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

FILES = (
    ".streamlit/config.toml",
    "requirements-dashboard.txt",
    "dashboard/README.md",
    "dashboard/app.py",
    "dashboard/synthetic_contract.py",
    "dashboard/synthetic_data.py",
    "dashboard/synthetic_fixture.json",
    "dashboard/pytest.ini",
    "dashboard/tests/test_synthetic_contract.py",
    "dashboard/tests/test_synthetic_dashboard.py",
    "scripts/verify_synthetic_dashboard.py",
)
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    tree = output / "isolated"
    hashes = {}
    for name in FILES:
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    actual = {path.relative_to(tree).as_posix() for path in tree.rglob("*") if path.is_file()}
    if actual != set(FILES):
        raise ValueError("Unexpected data-free inputs")
    command = [sys.executable, "-I", "-B", "scripts/verify_synthetic_dashboard.py", "--protected-root", str(ROOT)]
    with (output / "suite_console.txt").open("xb") as log:
        child = subprocess.run(command, cwd=tree, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    print((output / "suite_console.txt").read_text(encoding="utf-8", errors="replace"))
    report = {
        "status": "DATA_FREE_TESTED" if child.returncode == 0 else "FAIL",
        "copied_files_sha256": hashes, "child_command": command, "child_exit_code": child.returncode,
        "working_tree_scope": "allowlisted files only before execution",
        "dependencies_reinstalled_in_tree": False,
    }
    (output / "data_free_reproduction.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return child.returncode


if __name__ == "__main__":
    sys.exit(main())
