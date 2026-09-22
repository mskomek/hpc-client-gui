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


def _audit_receipt(tmp_path: Path, *, status="PASS", identity="content-1", wave="W18"):
    result = tmp_path / ".tmp" / "audit-normalized.json"
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps({"status": status}), encoding="utf-8")
    return {
        "audit_status": status,
        "tested_wave": wave,
        "tested_content_identity": identity,
        "audit_result_path": str(result.relative_to(tmp_path)),
        "audit_candidate_sha": "head-1",
    }


def test_audit_close_receipt_overrides_historical_ready(tmp_path: Path, monkeypatch):
    receipt = _audit_receipt(tmp_path)
    monkeypatch.setattr(controller, "git", lambda *_args: (0, "head-1"))
    assert controller.audit_receipt_valid(tmp_path, {}, "W18", receipt, "content-1")
    prompt = controller.build_phase_prompt(
        tmp_path, "HPC", "W18", tmp_path / "W18.md", "close", "W18", None, False, receipt
    )
    assert "controller audit gate" in prompt.lower()
    assert "Historical READY_FOR_AUDIT" in prompt


def test_audit_close_receipt_survives_restart_when_identity_unchanged(tmp_path: Path, monkeypatch):
    receipt = _audit_receipt(tmp_path)
    monkeypatch.setattr(controller, "git", lambda *_args: (0, "head-1"))
    saved_state = json.loads(json.dumps(receipt))
    assert controller.audit_receipt_valid(tmp_path, {}, "W18", saved_state, "content-1")


def test_audit_close_receipt_invalidates_on_content_change(tmp_path: Path, monkeypatch):
    receipt = _audit_receipt(tmp_path)
    monkeypatch.setattr(controller, "git", lambda *_args: (0, "head-1"))
    assert not controller.audit_receipt_valid(tmp_path, {}, "W18", receipt, "content-2")


def test_audit_close_receipt_fails_closed_for_missing_or_nonpass_result(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(controller, "git", lambda *_args: (0, "head-1"))
    missing = {"audit_status": "PASS", "tested_wave": "W18", "tested_content_identity": "content-1",
               "audit_result_path": ".tmp/missing.json", "audit_candidate_sha": "head-1"}
    assert not controller.audit_receipt_valid(tmp_path, {}, "W18", missing, "content-1")
    failed = _audit_receipt(tmp_path, status="REOPEN")
    assert not controller.audit_receipt_valid(tmp_path, {}, "W18", failed, "content-1")


def test_status_order_without_receipt_remains_repair_then_audit(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("WAVE_PHASE_STATUS: READY_FOR_AUDIT\nWAVE_REPAIR_STATUS: BLOCKED\n", encoding="utf-8")
    assert controller.effective_audit_status(report) == "BLOCKED"
    report.write_text("WAVE_REPAIR_STATUS: BLOCKED\nWAVE_REPAIR_STATUS: READY_FOR_AUDIT\n", encoding="utf-8")
    assert controller.effective_audit_status(report) == "READY_FOR_AUDIT"
