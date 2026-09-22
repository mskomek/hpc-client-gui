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


def test_no_progress_key_spans_repair_audit_cycle():
    first = controller.no_progress_key("W18", "repair", "same finding", "same tree")
    second = controller.no_progress_key("W18", "audit", "same finding", "same tree")
    assert first == second
    assert first != controller.no_progress_key("W18", "audit", "same finding", "changed tree")


def test_result_fingerprint_ignores_report_prose_for_stable_finding_ids():
    first = controller.result_fingerprint(
        "W18", "audit", {"status": "REOPEN", "findings": ["W18-001: old report text at 63b696b3b8c64296d9d17f94c8d0d903f9bab7eb"]}
    )
    second = controller.result_fingerprint(
        "W18", "audit", {"status": "REOPEN", "findings": ["W18-001: appended report text at e51572de3e6018bef4f4f97cc25531c19fb2c4ac"]}
    )
    assert first == second
