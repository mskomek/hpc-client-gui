"""Bisect early native GUI test history before the F-03 FTP/Qt segfault.

Each half is a complete fresh subprocess, executed before the exact FTP
concurrency module. This is diagnostic only: individual PASS does not prove
the combined production/native suite. The original full suite stays red.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from v2_native_suite_runner import ROOT, run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    args = parser.parse_args()
    if not 60 <= args.timeout_seconds <= 500:
        parser.error("timeout must be 60..500 seconds")
    test_root = ROOT / "tests"
    target = "test_ftp_widget_backend_concurrency.py"
    prior = sorted(p for p in test_root.glob("test_*.py") if p.name < target)
    if len(prior) < 10:
        parser.error("source prefix cannot be established")
    mid = len(prior) // 2
    groups = {
        "linux-first-prefix-half": prior[:mid],
        "linux-second-prefix-half": prior[mid:],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    groups_manifest = {
        "target": f"tests/{target}",
        "prefix_count": len(prior),
        "groups": {
            label: [p.relative_to(ROOT).as_posix() for p in files]
            for label, files in groups.items()
        },
        "note": "Split A/B may pass even if full prefix crashes; do not promote to acceptance.",
    }
    (args.output / "prefix-isolation-selections.json").write_text(
        json.dumps(groups_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    failures = 0
    for label, files in groups.items():
        selections = [
            *[p.relative_to(ROOT).as_posix() for p in files],
            f"tests/{target}",
            "--maxfail=0",
        ]
        if run(label, args.output, args.timeout_seconds, selections) != 0:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
