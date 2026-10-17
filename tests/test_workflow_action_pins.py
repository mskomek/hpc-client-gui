"""Every third-party GitHub Action in every workflow must be SHA-pinned.

The changelog historically claimed full-SHA pinning while the CI macOS
matrix still used floating version tags. This scanner fails for any
``uses: owner/repo@ref`` whose ref is not a full 40-character commit SHA,
across all workflow files, so the claim can never silently regress.
"""

from __future__ import annotations

import pytest

import re
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
USES_RE = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)\s*(?:#.*)?$", re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _action_refs(text: str) -> list[tuple[str, str]]:
    refs = []
    for match in USES_RE.finditer(text):
        target = match.group(1).strip("'\"")
        if target.startswith("./") or target.startswith("docker://"):
            continue  # local composite actions / container images: no ref pinning
        refs.append((target, match.group(0)))
    return refs


@pytest.mark.audit
@pytest.mark.semantic
def test_source_and_diagnostic_workflows_exist_without_publishing():
    files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert {path.name for path in files} == {
        "ci.yml",
        "release.yml",
        "w19-ubuntu-webkit-diagnostic.yml",
        "w55-windows-packaged-evidence.yml",
    }
    root = WORKFLOWS_DIR.parents[1]
    assert (root / "docs" / "ci-disabled" / "ci.yml").is_file()
    for name in ("ci.yml", "w19-ubuntu-webkit-diagnostic.yml", "w55-windows-packaged-evidence.yml"):
        text = (WORKFLOWS_DIR / name).read_text(encoding="utf-8").lower()
        assert "softprops/action-gh-release" not in text
        assert "create-release" not in text

@pytest.mark.audit
@pytest.mark.semantic

def test_all_action_references_are_pinned_to_full_commit_shas():
    violations: list[str] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for target, line in _action_refs(text):
            if "@" not in target:
                violations.append(f"{path.name}: missing ref: {line.strip()}")
                continue
            ref = target.rsplit("@", 1)[1]
            if not FULL_SHA_RE.match(ref):
                violations.append(f"{path.name}: floating ref '{ref}': {line.strip()}")
    assert not violations, "unpinned action references:\n" + "\n".join(violations)

@pytest.mark.audit
@pytest.mark.semantic

def test_pins_keep_a_version_comment():
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for target, line in _action_refs(text):
            if "@" not in target:
                continue
            assert "# v" in line, f"{path.name}: pin lacks version comment: {line.strip()}"

@pytest.mark.audit
@pytest.mark.semantic

def test_release_workflow_publish_step_is_pinned():
    text = (WORKFLOWS_DIR / "release.yml").read_text(encoding="utf-8")
    assert re.search(
        r"uses: softprops/action-gh-release@[0-9a-f]{40}", text
    ), "release publication step must stay SHA-pinned"


@pytest.mark.audit
@pytest.mark.semantic
def test_windows_and_linux_release_tests_use_pinned_legacy_qt_lock():
    root = WORKFLOWS_DIR.parents[1]
    workflow = (WORKFLOWS_DIR / "release.yml").read_text(encoding="utf-8")
    qt_lock = (root / "requirements-legacy-qt-test.lock").read_text(encoding="utf-8")
    release_lock = (root / "requirements-release.lock").read_text(encoding="utf-8")

    assert workflow.count("pip install -r requirements-legacy-qt-test.lock") == 2
    assert workflow.count("pip uninstall --yes PySide6 PySide6_Addons PySide6_Essentials shiboken6") == 2
    assert "PySide6" not in release_lock
    assert set(qt_lock.splitlines()) == {
        "PySide6==6.11.2",
        "PySide6_Addons==6.11.2",
        "PySide6_Essentials==6.11.2",
        "shiboken6==6.11.2",
    }
