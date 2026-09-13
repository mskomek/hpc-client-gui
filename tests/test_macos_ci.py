from __future__ import annotations
import pytest
pytestmark = pytest.mark.macos

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
ARCHIVED_WORKFLOW = Path(__file__).resolve().parents[1] / "docs" / "ci-disabled" / "ci.yml"


@pytest.mark.audit
def test_active_macos_ci_matrix_or_archived_ci_contract():
    if not WORKFLOW.exists():
        assert ARCHIVED_WORKFLOW.is_file()
        return
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "name: macOS (${{ matrix.arch }})" in text
    assert "os: macos-15" in text
    assert "os: macos-15-intel" in text
    assert "arch: arm64" in text
    assert "arch: x86_64" in text
    assert "fail-fast: false" in text
    assert "python scripts/ci.py macos" in text


@pytest.mark.audit
def test_active_macos_ci_has_no_release_signing_step_or_is_archived():
    if not WORKFLOW.exists():
        assert ARCHIVED_WORKFLOW.is_file()
        return
    text = WORKFLOW.read_text(encoding="utf-8")
    macos_block = text.split("  macos:\n", 1)[1].split("  windows:\n", 1)[0]
    assert "actions/upload-release-asset" not in macos_block
    assert "notarytool" not in macos_block
    assert "codesign" not in macos_block
