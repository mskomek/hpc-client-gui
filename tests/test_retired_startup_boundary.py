"""Prevent reintroducing references to retired Qt startup modules."""
from pathlib import Path
import re
import subprocess

import pytest


@pytest.mark.audit
def test_retired_startup_has_no_tracked_executable_references():
    root = Path(__file__).resolve().parents[1]
    retired = re.compile(
        r"\blegacy_app\b|\bwelcome_dialog\b|\bWelcomeDialog\b|hpc_gui\.ui\.debug_telemetry"
    )
    candidates = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "src", "tests", "scripts", "devtools", "build", ".github"],
        cwd=root,
    ).decode("utf-8").split("\0")
    hits = []
    for name in candidates:
        path = root / name
        if not name or path.resolve() == Path(__file__).resolve():
            continue
        if path.suffix not in {".py", ".spec", ".ps1", ".sh", ".yml", ".yaml", ".toml", ".bat", ".cmd"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            if retired.search(line) or (
                re.search(r"\bStartupSplash\b", line)
                and name not in {"scripts/create_demo_gif.py", "src/hpc_gui/ui/splash_screen.py"}
            ):
                hits.append(f"{name}:{number}: {line.strip()}")
    assert not hits, "\n".join(hits)
