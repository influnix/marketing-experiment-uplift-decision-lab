"""Execute the explicit Day 14 suite with Python path and socket auditing."""

import argparse
from collections import Counter
from importlib.metadata import version
from ipaddress import ip_address
import json
import os
from pathlib import Path
import platform
import sys

TEST_FILES = (
    "dashboard/tests/test_synthetic_contract.py",
    "dashboard/tests/test_synthetic_dashboard.py",
)
GROUPS = ("raw_splits", "development_snapshot", "holdout", "private_inputs", "network", "blocked_import")
PATH_EVENTS = {"open", "os.listdir", "os.scandir"}
NETWORK_EVENTS = {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.sendto", "socket.sendmsg"}


def access_hook(protected_root, test_root, attempts):
    def deny(group, event):
        attempts[group] += 1
        raise PermissionError(f"Day 14 boundary: {group} ({event})")

    def audit(event, args):
        if event in NETWORK_EVENTS:
            if event == "socket.connect" and isinstance(args[1], tuple):
                try:
                    local = ip_address(args[1][0]).is_loopback
                except ValueError:
                    local = False
                if local:
                    # asyncio's Windows self-pipe uses an internal loopback socket.
                    return
            deny("network", event)
        if event == "import" and args[0].split(".")[0] == "marketing_lab":
            deny("blocked_import", event)
        if event not in PATH_EVENTS or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.path.abspath(os.fsdecode(args[0])))
        if path.name.casefold() == "secrets.toml":
            deny("private_inputs", event)
        for root in {protected_root, test_root}:
            if not path.is_relative_to(root):
                continue
            parts = tuple(part.casefold() for part in path.relative_to(root).parts)
            if not parts:
                continue
            if "holdout" in "/".join(parts) and parts[0] in {"data", "artifacts", "holdout"}:
                deny("holdout", event)
            if parts[:2] == ("data", "development") or parts[0] == "snapshot":
                deny("development_snapshot", event)
            if parts[0] in {"data", "raw", "splits", "hillstrom.csv"}:
                deny("raw_splits", event)
            if parts[0] in {"src", "docs", "artifacts", "readme.md", ".env"}:
                if not path.is_relative_to(test_root) and not path.is_relative_to(Path(sys.prefix)):
                    deny("private_inputs", event)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protected-root", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    attempts = Counter(dict.fromkeys(GROUPS, 0))
    sys.addaudithook(access_hook(args.protected_root.resolve(), root, attempts))
    import pytest

    report = {}

    class Summary:
        def pytest_terminal_summary(self, terminalreporter):
            report["collected"] = terminalreporter._numcollected
            for status in ("passed", "failed", "skipped", "warnings", "error"):
                report[status] = len(terminalreporter.stats.get(status, []))

    pytest_args = ["-c", "dashboard/pytest.ini", "--rootdir=.", "-q",
                   "-p", "no:cacheprovider", "--noconftest", *TEST_FILES]
    code = pytest.main(pytest_args, plugins=[Summary()])
    unexpected = [name for name in sys.modules if name.split(".")[0] == "marketing_lab"]
    report.update(
        pytest_args=pytest_args, pytest_exit_code=int(code),
        access_attempts=dict(attempts), unexpected_imports=unexpected,
        access_scope="Python audit events in the AppTest process, not OS/browser telemetry",
        python=sys.version.split()[0], os=platform.system(),
        packages={name: version(name) for name in ("streamlit", "pandas", "pyarrow", "pytest")},
    )
    with (root / "dashboard_test_report.json").open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
    return int(code) or int(any(attempts.values()) or bool(unexpected))


if __name__ == "__main__":
    sys.exit(main())
