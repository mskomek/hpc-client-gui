"""Release workflow policy tests.

These tests assert the *behavior* of the release pipeline (explicit macOS
modes, an unskippable final gate, opt-in publication, security metadata,
and complete artifact-size reporting) instead of matching brittle full-line
YAML strings. The workflow must stay honest: unsigned releases can never be
represented as signed, and publication can never race ahead of verification.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")


def _job_block(job: str, text: str = TEXT) -> str:
    """Extract the body of a top-level workflow job."""
    pattern = rf"(?ms)^  {re.escape(job)}:\n(.*?)(?=^  \w[\w-]*:\n|^permissions:|^concurrency:|\Z)"
    match = re.search(pattern, text)
    assert match, f"job not found in workflow: {job}"
    return match.group(1)


def _needs(block: str) -> list[str]:
    """Collect ``needs`` entries from inline lists or multi-line item lists."""
    collected: list[str] = []
    lines = block.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("needs:"):
            continue
        rest = stripped[len("needs:"):].strip()
        if rest:
            collected.extend(re.findall(r"[A-Za-z][\w-]*", rest))
            continue
        for follow in lines[index + 1:]:
            item = follow.strip()
            if re.match(r"^-\s+[A-Za-z][\w-]*$", item):
                collected.append(item[1:].strip())
            elif item:
                break
    return collected


def test_inputs_define_explicit_signed_default_and_opt_in_publication():
    inputs_block = TEXT.split("    inputs:", 1)[1].split("\npermissions:", 1)[0]
    publish_block = inputs_block.split("      publish:", 1)[1].split("      macos_mode:", 1)[0]
    assert "type: boolean" in publish_block
    assert "default: false" in publish_block
    mode_block = inputs_block.split("      macos_mode:", 1)[1]
    assert "type: choice" in mode_block
    assert re.search(r"^\s+- signed$", mode_block, re.MULTILINE)
    assert re.search(r"^\s+- unsigned$", mode_block, re.MULTILINE)
    assert re.search(r"default: signed", mode_block)


def test_dry_run_can_never_publish():
    publish = _job_block("publish-release")
    assert re.search(r"^    if: \$\{\{ inputs\.publish == true \}\}", publish, re.MULTILINE)
    # Publication is gated behind the final gate job only.
    gate_needs = _needs(_job_block("release-gate"))
    for required in (
        "build-linux",
        "build-windows",
        "build-macos-arm64",
        "build-macos-x86_64",
        "sign-macos-arm64",
        "sign-macos-x86_64",
        "verify-macos-signed-candidate",
        "verify-unsigned-release",
    ):
        assert required in gate_needs
    assert "release-gate" in _needs(publish)
    assert "softprops/action-gh-release" in publish


def test_signing_jobs_run_only_in_signed_mode_and_upload_separate_artifacts():
    for arch in ("arm64", "x86_64"):
        sign = _job_block(f"sign-macos-{arch}")
        assert "inputs.macos_mode == 'signed'" in sign
        assert f"hpc-client-gui-macos-{arch}-signed-" in sign


def test_build_jobs_always_produce_unsigned_candidates():
    for arch in ("arm64", "x86_64"):
        build = _job_block(f"build-macos-{arch}")
        assert f"hpc-client-gui-macos-{arch}-candidate-" in build
        assert "-unsigned-" not in build


def test_signed_publication_is_verified_before_it_can_publish():
    verify = _job_block("verify-macos-signed-candidate")
    assert "inputs.macos_mode == 'signed'" in verify
    needs = _needs(verify)
    assert "sign-macos-arm64" in needs and "sign-macos-x86_64" in needs
    assert "codesign --verify --deep --strict" in verify
    assert "spctl --assess --type execute" in verify
    assert "hdiutil attach" in verify


def test_unsigned_mode_cannot_be_represented_as_signed():
    unsigned_verify = _job_block("verify-unsigned-release")
    assert "inputs.macos_mode == 'unsigned'" in unsigned_verify
    assert "--mode unsigned" in unsigned_verify
    warning = unsigned_verify
    assert "NOT Apple Developer ID signed" in warning
    assert "Gatekeeper may block the first launch" in warning
    assert "substitutes for Apple code signing" in warning
    # No signing/notarization commands may appear in the unsigned path.
    for forbidden in ("codesign ", "notarytool", "spctl --assess", "sign_macos_release"):
        assert forbidden not in unsigned_verify
    publish = _job_block("publish-release")
    assert "must never claim signing" in publish


def test_final_gate_rejects_missing_skipped_or_failed_required_jobs():
    gate_script = (ROOT / "scripts" / "release_gate.py").read_text(encoding="utf-8")
    assert '"success" if macos_mode == "signed" else "skipped"' in gate_script
    assert "missing result for required job" in gate_script
    assert "did not succeed" in gate_script
    gate_job = _job_block("release-gate")
    assert "always()" in gate_job
    for result_env in (
        "GATE_RESULT_BUILD_LINUX",
        "GATE_RESULT_BUILD_WINDOWS",
        "GATE_RESULT_BUILD_MACOS_ARM64",
        "GATE_RESULT_BUILD_MACOS_X86_64",
        "GATE_RESULT_SIGN_MACOS_ARM64",
        "GATE_RESULT_SIGN_MACOS_X86_64",
        "GATE_RESULT_VERIFY_MACOS_SIGNED_CANDIDATE",
        "GATE_RESULT_VERIFY_UNSIGNED_RELEASE",
    ):
        assert result_env in gate_job


def test_both_mac_architectures_are_required_for_publication():
    publish = _job_block("publish-release")
    for arch in ("arm64", "x86_64"):
        assert f"hpc-client-gui-macos-{arch}-" in publish
    inventory = publish + _job_block("verify-unsigned-release") + _job_block("verify-macos-signed-candidate")
    assert "hpc-client-gui_macos_arm64.dmg" in inventory
    assert "hpc-client-gui_macos_x86_64.dmg" in inventory


def test_final_inventory_contains_windows_linux_and_both_macs():
    publish = _job_block("publish-release")
    assert 'linux", "windows", "macos"' in publish or ('"linux"' in publish and '"macos"' in publish)
    assert "MANIFEST.json" in publish
    assert "RELEASE_SECURITY.json" in publish


def test_security_metadata_matches_selected_mode_at_publication():
    publish = _job_block("publish-release")
    assert "expected_mode" in publish
    assert "signed-notarized" in publish
    assert "requires verified signing claims" in publish


def test_artifact_size_report_runs_after_every_platform_download():
    for job in ("verify-unsigned-release", "verify-macos-signed-candidate", "publish-release"):
        block = _job_block(job)
        report_pos = block.find("Report artifact sizes")
        assert report_pos > -1, f"{job} lacks the size report"
        if job != "publish-release":
            # Verifiers download all platform artifacts before reporting.
            last_download = block.rfind("download-artifact", 0, report_pos)
            assert last_download > -1, f"{job} reports sizes before downloads"
        else:
            metadata_pos = block.find("Download release metadata")
            assert -1 < metadata_pos < report_pos
            last_mac = block.find("Download Mac x86_64 artifacts")
            assert -1 < last_mac < report_pos


def test_release_preflight_shares_the_ci_test_suite():
    shared = (ROOT / "scripts" / "release_test_suite.py").read_text(encoding="utf-8")
    assert '"not packaging"' in shared
    assert "check_i18n.py" in shared
    assert "smoke_test.py" in shared
    # Wire-heavy suites must stay isolated in their own processes while
    # remaining part of the same gates (nothing skipped).
    assert "ISOLATED_WIRE_FILES" in shared
    assert "tests/test_ftp_widget.py" in shared
    assert "tests/test_download_cancel_wire.py" in shared
    assert "--cov-append" in shared
    linux = _job_block("build-linux")
    windows = _job_block("build-windows")
    for block in (linux, windows):
        assert "release_test_suite.py" in block
        assert "unittest discover" not in block
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "release_test_suite.py --coverage" in ci


def test_release_notes_are_generated_from_the_changelog():
    for job in ("verify-unsigned-release", "verify-macos-signed-candidate"):
        block = _job_block(job)
        assert "RELEASE_NOTES.md" in block
        assert "src/hpc_gui/docs/CHANGELOG.md" in block
