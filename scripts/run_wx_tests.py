"""Run the wx test suite in separate processes.

The wx suite exhausts a process-wide Windows resource ceiling when every module
shares one interpreter: once it is crossed, `wx.Dialog` creation starts failing
and whichever wx-heavy tests run late fail with
"Failed to create dialog. Incorrect DLGTEMPLATE?" or "invalid window".

Measured on this repository: with every module in one process the suite fails
14-25 tests, while the same code split into the groups below passes completely.
Adding a single extra `wx.StaticText` to the remote files panel was enough to
cross the ceiling, whether or not it was added to a sizer, so this is a limit of
the test process rather than a defect in the panels.

`test_wx_shell_p0_stress.py` builds hundreds of shells and is the main consumer,
so it gets a process of its own.

Usage:
    python scripts/run_wx_tests.py [extra pytest args...]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

STRESS = "test_wx_shell_p0_stress.py"


def _group(pattern: str, exclude: set[str] = frozenset()) -> list[str]:
    return sorted(
        f"tests/{path.name}"
        for path in TESTS.glob(pattern)
        if path.name not in exclude
    )


GROUPS: list[tuple[str, list[str]]] = [
    ("a-i", _group("test_wx_[a-i]*.py")),
    ("j-r", _group("test_wx_[j-r]*.py")),
    ("shell", _group("test_wx_s*.py", exclude={STRESS})),
    ("shell-stress", [f"tests/{STRESS}"]),
    ("t-z", _group("test_wx_[t-z]*.py")),
]


def main(argv: list[str]) -> int:
    failures: list[str] = []
    for name, files in GROUPS:
        if not files:
            continue
        print(f"\n=== wx group: {name} ({len(files)} files) ===", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *files, *argv],
            cwd=ROOT,
        )
        if result.returncode != 0:
            failures.append(f"{name} (exit {result.returncode})")

    print("\n=== summary ===")
    if failures:
        print("FAILED groups: " + ", ".join(failures))
        return 1
    print(f"all {len(GROUPS)} wx groups passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
