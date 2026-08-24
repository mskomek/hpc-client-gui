from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def test_macos_ci_matrix_covers_both_native_architectures():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "name: macOS (${{ matrix.arch }})" in text
    assert "os: macos-15" in text
    assert "os: macos-15-intel" in text
    assert "arch: arm64" in text
    assert "arch: x86_64" in text
    assert "fail-fast: false" in text
    assert "hashFiles('requirements-release.lock')" in text


def test_macos_ci_has_no_release_upload_or_signing_step():
    text = WORKFLOW.read_text(encoding="utf-8")
    macos_block = text.split("  macos:\n", 1)[1].split("  windows:\n", 1)[0]
    assert "actions/upload-release-asset" not in macos_block
    assert "notarytool" not in macos_block
    assert "codesign" not in macos_block
