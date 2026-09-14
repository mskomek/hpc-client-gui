from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.audit, pytest.mark.semantic]
ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_WORKFLOW = ROOT / "docs" / "ci-disabled" / "ci.yml"
ACTIVE_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_archived_macos_matrix_covers_both_native_architectures():
    assert not ACTIVE_WORKFLOW.exists(), "automatic CI is intentionally disabled"
    text = ARCHIVED_WORKFLOW.read_text(encoding="utf-8")
    assert "name: macOS (${{ matrix.arch }})" in text
    assert "os: macos-15" in text
    assert "os: macos-15-intel" in text
    assert "arch: arm64" in text
    assert "arch: x86_64" in text
    assert "fail-fast: false" in text
    assert "python scripts/ci.py macos" in text


def test_archived_macos_job_has_no_release_upload_or_signing_step():
    assert not ACTIVE_WORKFLOW.exists(), "automatic CI is intentionally disabled"
    text = ARCHIVED_WORKFLOW.read_text(encoding="utf-8")
    macos_block = text.split("  macos:\n", 1)[1].split("  windows:\n", 1)[0]
    assert "actions/upload-release-asset" not in macos_block
    assert "notarytool" not in macos_block
    assert "codesign" not in macos_block
