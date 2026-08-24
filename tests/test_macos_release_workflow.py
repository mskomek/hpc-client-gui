from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"


def test_release_workflow_has_two_mac_artifact_jobs_and_publish_dependencies():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "publish:" in text
    assert "default: false" in text
    assert "build-macos-arm64:" in text
    assert "runs-on: macos-15" in text
    assert "build-macos-x86_64:" in text
    assert "runs-on: macos-15-intel" in text
    assert "needs: [build-linux, build-windows, build-macos-arm64, build-macos-x86_64, sign-macos-arm64, sign-macos-x86_64, verify-macos-signed-candidate]" in text
    assert "environment: macos-release" in text
    assert "hpc-client-gui_macos_arm64.dmg" in text
    assert "hpc-client-gui_macos_x86_64.dmg" in text
    assert "*.dmg" in text


def test_publish_is_opt_in_and_actions_are_sha_pinned():
    text = WORKFLOW.read_text(encoding="utf-8")
    publish_block = text.split("  publish-release:\n", 1)[1]
    assert "if: ${{ inputs.publish == true }}" in text
    assert "Refuse an existing release" in publish_block
    for line in text.splitlines():
        if "uses: actions/" in line:
            assert "@" in line and len(line.split("@", 1)[1].split()[0]) >= 40


def test_unsigned_dry_run_verifies_all_platforms_without_publishing():
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("  verify-macos-dry-run:\n", 1)[1].split("\n  sign-macos-arm64:", 1)[0]
    assert "if: ${{ inputs.publish != true && inputs.sign != true }}" in block
    assert "hpc-client-gui-macos-arm64-unsigned-${{ github.event.inputs.version }}" in block
    assert "hpc-client-gui-macos-x86_64-unsigned-${{ github.event.inputs.version }}" in block
    assert "hpc-client-gui-linux-${{ github.event.inputs.version }}" in block
    assert "hpc-client-gui-${{ github.event.inputs.version }}" in block
    assert "generate_release_manifest.py" in block
    assert '"linux", "windows", "macos"' in block
    assert "softprops/action-gh-release" not in block


def test_sign_only_candidate_is_separate_from_publication():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'description: "Sign and notarize macOS candidates without publishing"' in text
    assert "if: ${{ inputs.sign == true || inputs.publish == true }}" in text
    assert "if: ${{ inputs.publish == true }}" in text
    assert "inputs.publish || inputs.sign" in text
    dry_run = text.split("  verify-macos-dry-run:\n", 1)[1].split("\n  sign-macos-arm64:", 1)[0]
    assert "inputs.publish != true && inputs.sign != true" in dry_run


def test_signed_candidates_are_verified_before_publish():
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("  verify-macos-signed-candidate:\n", 1)[1].split("\n  publish-release:", 1)[0]
    assert "needs: [sign-macos-arm64, sign-macos-x86_64]" in block
    assert "shasum -a 256 -c" in block
    assert "codesign --verify --deep --strict" in block
    assert "spctl --assess --type execute" in block
    publish = text.split("  publish-release:\n", 1)[1]
    assert "verify-macos-signed-candidate" in publish.split("\n    runs-on:", 1)[0]
    assert "Validate final release inventory" in publish
    assert 'assert not any("unsigned" in name.lower() for name in names)' in publish


def test_signing_secret_mapping_is_complete_and_publish_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in (
        "MACOS_CERTIFICATE_P12_BASE64",
        "MACOS_CERTIFICATE_PASSWORD",
        "APPLE_TEAM_ID",
        "APPLE_NOTARY_KEY_ID",
        "APPLE_NOTARY_ISSUER_ID",
        "APPLE_NOTARY_PRIVATE_KEY_BASE64",
    ):
        assert name in text
    assert "sign-macos-arm64:" in text and "sign-macos-x86_64:" in text
