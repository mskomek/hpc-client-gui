"""Prevent reintroducing references to retired Qt startup and tour modules."""
from pathlib import Path
import re
import subprocess

import pytest


@pytest.mark.audit
def test_retired_startup_has_no_tracked_executable_references():
    root = Path(__file__).resolve().parents[1]
    retired = re.compile(
        r"\blegacy_app\b|\bwelcome_dialog\b|\bWelcomeDialog\b|hpc_gui\.ui\.debug_telemetry|\bStartupSplash\b"
        r"|\bQuickTourOverlay\b|hpc_gui\.ui\.dialogs\.quick_tour|\bstart_quick_tour\b|\b_act_quick_tour\b"
        r"|\bAboutDialog\b|hpc_gui\.ui\.dialogs\.about_dialog|\b_open_about\b|\b_act_about\b"
        r"|\bUpdateSplash\b|\b_main_window_updates\b|\b_MainWindowUpdatesMixin\b|hpc_gui\.ui\.splash_screen"
        r"|\bHelpDialog\b|\bSendLogsDialog\b|hpc_gui\.ui\.dialogs\.(?:help_dialog|send_logs_dialog)"
        r"|\bClusterSelfTestDialog\b|hpc_gui\.ui\.dialogs\.cluster_self_test_dialog"
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
            if retired.search(line):
                hits.append(f"{name}:{number}: {line.strip()}")
    assert not hits, "\n".join(hits)
