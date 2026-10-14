"""Unit tests for the release-gate policy and RELEASE_SECURITY metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.release, pytest.mark.semantic]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_release_security as sec  # noqa: E402
import release_gate as gate  # noqa: E402

ALL_OK_SIGNED = {
    "build-linux": "success",
    "build-windows": "success",
    "build-macos-arm64": "success",
    "build-macos-x86_64": "success",
    "sign-macos-arm64": "success",
    "sign-macos-x86_64": "success",
    "verify-macos-signed-candidate": "success",
    "verify-unsigned-release": "skipped",
}
ALL_OK_UNSIGNED = dict(ALL_OK_SIGNED, **{
    job: "skipped" for job in (
        "sign-macos-arm64", "sign-macos-x86_64", "verify-macos-signed-candidate",
    )
}, **{"verify-unsigned-release": "success"})


def test_signed_gate_passes_when_everything_succeeded():
    assert gate.evaluate_gate("signed", ALL_OK_SIGNED) == []


def test_unsigned_gate_passes_with_skipped_signing_jobs():
    assert gate.evaluate_gate("unsigned", ALL_OK_UNSIGNED) == []


def test_gate_rejects_signed_mode_without_verification():
    results = dict(ALL_OK_SIGNED, **{"verify-macos-signed-candidate": "failure"})
    violations = gate.evaluate_gate("signed", results)
    assert any("verify-macos-signed-candidate" in v for v in violations)


def test_gate_rejects_missing_results():
    violations = gate.evaluate_gate("signed", {})
    for job in gate.BUILD_JOBS + gate.SIGNED_ONLY_JOBS + (gate.UNSIGNED_VERIFY_JOB,):
        assert any(job in v and "missing result" in v for v in violations)


def test_gate_rejects_cancelled_build_and_unexpected_sign_skip():
    cancelled = {
        job: ("cancelled" if job == "build-windows" else result)
        for job, result in ALL_OK_SIGNED.items()
    }
    assert any("build-windows" in v for v in gate.evaluate_gate("signed", cancelled))
    forced_signed_skip = dict(ALL_OK_SIGNED, **{"sign-macos-x86_64": "skipped"})
    violations = gate.evaluate_gate("signed", forced_signed_skip)
    assert any("must be success" in v for v in violations)


def test_gate_requires_unsigned_inventory_job_even_in_signed_mode():
    results = dict(ALL_OK_SIGNED, **{"verify-unsigned-release": "success"})
    violations = gate.evaluate_gate("signed", results)
    assert any("verify-unsigned-release" in v and "must be skipped" in v for v in violations)


def test_unknown_mode_is_rejected():
    assert gate.evaluate_gate("", {}) == ["unsupported macos_mode: ''"]
    assert len(gate.evaluate_gate("adhoc", {})) == 1


def test_collect_results_preserves_x86_64_job_ids(monkeypatch):
    monkeypatch.setenv("GATE_RESULT_BUILD_MACOS_X86_64", "success")
    monkeypatch.setenv("GATE_RESULT_SIGN_MACOS_X86_64", "skipped")
    results = gate._collect_results()
    assert results["build-macos-x86_64"] == "success"
    assert results["sign-macos-x86_64"] == "skipped"


def test_security_metadata_never_claims_signing_for_unsigned():
    meta = sec.build_security_metadata("v1.5.1", "abc123", "unsigned", ["arm64"])
    assert meta["macos_mode"] == "unsigned"
    assert not meta["developer_id_verification_passed"]
    assert not meta["notarization_passed"]
    assert not meta["stapling_passed"]
    assert not meta["gatekeeper_assessment_passed"]


def test_security_metadata_records_all_outcomes_when_signed():
    meta = sec.build_security_metadata(
        "v1.5.1", "abc123", "signed-notarized", ["x86_64", "arm64"]
    )
    assert all(meta[key] for key in (
        "developer_id_verification_passed",
        "notarization_passed",
        "stapling_passed",
        "gatekeeper_assessment_passed",
    ))
    assert meta["artifact_architectures"] == ["arm64", "x86_64"]


def test_cli_writes_metadata_file(tmp_path: Path):
    status = sec.main([
        "--release-dir", str(tmp_path), "--version", "v9.9.9",
        "--commit", "deadbeef", "--mode", "unsigned",
        "--arch", "arm64", "--arch", "x86_64",
    ])
    assert status == 0
    payload = json.loads((tmp_path / "RELEASE_SECURITY.json").read_text(encoding="utf-8"))
    assert payload["release"] == "v9.9.9"
    assert payload["macos_mode"] == "unsigned"


@pytest.mark.parametrize("mode", ("signed-notarized", "unsigned"))
def test_manifest_includes_security_json(tmp_path: Path, mode):
    sys.path.insert(0, str(ROOT / "scripts"))
    import generate_release_manifest as gen

    (tmp_path / "hpc-client-gui_macos_arm64.dmg").write_bytes(b"dmg")
    sec.main([
        "--release-dir", str(tmp_path), "--version", f"v1.0.0-{mode}",
        "--commit", "cafe", "--mode", mode, "--arch", "arm64",
    ])
    manifest = gen.build_manifest(tmp_path, "v1.0.0")
    names = {entry["file"] for entry in manifest["artifacts"]}
    assert "RELEASE_SECURITY.json" in names


# --- W60.2 U01: publication gate fail-closed verification (001..005) ---

FROZEN_SHA = "B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD"
FROZEN_PLUGIN_IDENTITY = "in-tree at 0eb4f0d5026f87ba1aaad0dc1ba301590d82ca7d"


def _passing_acceptance(**overrides):
    payload = {
        "verdict": "PASS",
        "mandatory_fail": 0,
        "mandatory_blocked": 0,
        "mandatory_not_evidenced": 0,
        "feature_inventory_pct": 100,
        "settings_inventory_pct": 100,
        "secret_scan": "PASS",
        "open_p0": 0,
        "open_p1": 0,
        "rollback_ready": True,
        "tested_sha256": FROZEN_SHA,
        "publishing_sha256": FROZEN_SHA,
        "plugin_registry_freeze": FROZEN_PLUGIN_IDENTITY,
        "plugin_registry_commit": FROZEN_PLUGIN_IDENTITY,
        "evidence": {
            "ssh": "PASS",
            "sftp": "PASS",
            "pty": "PASS",
            "slurm": "PASS",
            "gui": "PASS",
            "updater": "PASS",
            "migration": "PASS",
            "settings": "PASS",
            "diagnostics": "PASS",
        },
    }
    payload.update(overrides)
    return payload


def test_publication_gate_passes_with_frozen_identity():
    acceptance = _passing_acceptance()
    assert gate.evaluate_acceptance_result(acceptance) == []
    assert gate.evaluate_publication_gate("signed", ALL_OK_SIGNED, acceptance) == []


def test_publication_gate_requires_acceptance_result():
    violations = gate.evaluate_publication_gate("signed", ALL_OK_SIGNED, None)
    assert any("acceptance result" in v for v in violations)
    # Build success alone never publishes without the acceptance layer.
    assert gate.evaluate_gate("signed", ALL_OK_SIGNED) == []


def test_publication_gate_rejects_fail_blocked_not_evidenced():
    assert any("FAIL" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(mandatory_fail=1)))
    assert any("BLOCKED" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(mandatory_blocked=2)))
    assert any("NOT_EVIDENCED" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(mandatory_not_evidenced=1)))


def test_publication_gate_rejects_non_pass_verdict_and_inventory_gaps():
    assert any("verdict" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(verdict="FAIL")))
    assert any("verdict" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(verdict="BLOCKED")))
    assert any("feature inventory" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(feature_inventory_pct=99)))
    assert any("settings inventory" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(settings_inventory_pct=50)))
    assert any("secret scan" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(secret_scan="FAIL")))


def test_publication_gate_rejects_hash_drift_and_bad_digests():
    drifted = _passing_acceptance(publishing_sha256="0" * 64)
    assert any("hash drift" in v for v in gate.evaluate_acceptance_result(drifted))
    malformed = _passing_acceptance(tested_sha256="not-a-digest")
    assert any("tested SHA-256" in v for v in gate.evaluate_acceptance_result(malformed))
    missing = _passing_acceptance()
    del missing["tested_sha256"]
    assert any("SHA-256" in v for v in gate.evaluate_acceptance_result(missing))


def test_publication_gate_rejects_plugin_identity_mismatch():
    mismatched = _passing_acceptance(plugin_registry_commit="in-tree at deadbeef")
    assert any("plugin-registry" in v for v in gate.evaluate_acceptance_result(mismatched))
    missing = _passing_acceptance()
    del missing["plugin_registry_freeze"]
    assert any("plugin-registry" in v for v in gate.evaluate_acceptance_result(missing))


def test_publication_gate_requires_all_evidence_domains():
    for domain in gate.REQUIRED_EVIDENCE_DOMAINS:
        payload = _passing_acceptance()
        del payload["evidence"][domain]
        violations = gate.evaluate_acceptance_result(payload)
        assert any(domain in v for v in violations), domain
    blocked_domain = _passing_acceptance()
    blocked_domain["evidence"]["slurm"] = "BLOCKED"
    assert any("slurm" in v for v in gate.evaluate_acceptance_result(blocked_domain))
    assert len(gate.REQUIRED_EVIDENCE_DOMAINS) == 9


def test_publication_gate_rejects_open_p0_p1_and_unsafe_rollback():
    assert any("P0" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(open_p0=1)))
    assert any("P1" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(open_p1=1)))
    assert any("rollback" in v for v in gate.evaluate_acceptance_result(
        _passing_acceptance(rollback_ready=False)))


def test_publication_gate_rejects_missing_result_and_bad_json(tmp_path: Path):
    data, errors = gate.load_acceptance_result(tmp_path / "does-not-exist.json")
    assert data is None and any("not found" in e for e in errors)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    data, errors = gate.load_acceptance_result(bad)
    assert data is None and any("valid JSON" in e for e in errors)
    assert gate.evaluate_acceptance_result("not-a-dict") != []


def test_publication_gate_rejects_env_override_drift():
    acceptance = _passing_acceptance()
    violations = gate.evaluate_publication_gate(
        "signed", ALL_OK_SIGNED, acceptance,
        tested_sha_override=FROZEN_SHA, publishing_sha_override="0" * 64,
    )
    assert any("drifts" in v for v in violations)
    violations = gate.evaluate_publication_gate(
        "signed", ALL_OK_SIGNED, acceptance,
        plugin_freeze_override="in-tree at deadbeef",
    )
    assert any("drift" in v for v in violations)


def test_publication_gate_combines_job_and_acceptance_layers():
    broken_jobs = dict(ALL_OK_SIGNED, **{"build-linux": "failure"})
    violations = gate.evaluate_publication_gate("signed", broken_jobs, _passing_acceptance())
    assert any("build-linux" in v for v in violations)
    violations = gate.evaluate_publication_gate(
        "signed", ALL_OK_SIGNED, _passing_acceptance(verdict="FAIL"))
    assert any("verdict" in v for v in violations)
