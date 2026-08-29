"""Unit tests for the release-gate policy and RELEASE_SECURITY metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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
