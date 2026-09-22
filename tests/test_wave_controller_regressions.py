from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
import sys
sys.path.insert(0, str(ROOT / ".opencode" / "scripts"))


def load_script(name: str, filename: str):
    path = ROOT / ".opencode" / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


controller = load_script("wave_program_controller", "run-wave-program.py")
router = load_script("wave_findings_router", "route-wave-findings.py")


def test_latest_lifecycle_marker_wins(tmp_path: Path):
    report = tmp_path / "audit.md"
    report.write_text(
        "WAVE_PHASE_STATUS: READY_FOR_AUDIT\n"
        "old prose\n"
        "WAVE_REPAIR_STATUS: BLOCKED\n",
        encoding="utf-8",
    )
    assert controller.effective_audit_status(report) == "BLOCKED"

    report.write_text(
        "WAVE_REPAIR_STATUS: BLOCKED\n"
        "WAVE_REPAIR_STATUS: READY_FOR_AUDIT\n",
        encoding="utf-8",
    )
    assert controller.effective_audit_status(report) == "READY_FOR_AUDIT"

    report.write_text(
        "WAVE_PHASE_STATUS: READY_FOR_AUDIT\n"
        "WAVE_PHASE_STATUS: REOPEN\n",
        encoding="utf-8",
    )
    assert controller.effective_audit_status(report) == "REOPEN"


def test_done_owner_beats_stale_pending_duplicate(tmp_path: Path):
    for state in ("done", "pending", "blocked", "postponed"):
        (tmp_path / "waves" / state).mkdir(parents=True)
    body = """---
wave_id: W17
---
# W17

Canonical requirement IDs owned: HPC-W05-PROF-001
"""
    (tmp_path / "waves" / "done" / "W17.md").write_text(body, encoding="utf-8")
    (tmp_path / "waves" / "pending" / "W17.md").write_text(body, encoding="utf-8")
    assert router.build_owner_index(tmp_path)["HPC-W05-PROF-001"] == ("W17", "done")


def test_generic_lab_capability_findings_are_not_human_only():
    generic = [
        "password authentication capability missing from repository lab",
        "credential field missing from manifest",
    ]
    authority = "interactive authorization required: provider returned 401 unauthorized"
    assert not any(router.HUMAN_RE.search(text) for text in generic)
    assert router.HUMAN_RE.search(authority)
