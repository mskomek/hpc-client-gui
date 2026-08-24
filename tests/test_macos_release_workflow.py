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
    assert "needs: [build-linux, build-windows, build-macos-arm64, build-macos-x86_64, sign-macos-arm64, sign-macos-x86_64]" in text
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
