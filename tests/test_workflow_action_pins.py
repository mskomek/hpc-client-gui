"""Every third-party GitHub Action in every workflow must be SHA-pinned.

The changelog historically claimed full-SHA pinning while the CI macOS
matrix still used floating version tags. This scanner fails for any
``uses: owner/repo@ref`` whose ref is not a full 40-character commit SHA,
across all workflow files, so the claim can never silently regress.
"""

from __future__ import annotations

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


def test_every_workflow_exists():
    files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert {path.name for path in files} >= {"ci.yml", "release.yml"}


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


def test_pins_keep_a_version_comment():
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for target, line in _action_refs(text):
            if "@" not in target:
                continue
            assert "# v" in line, f"{path.name}: pin lacks version comment: {line.strip()}"


def test_release_workflow_publish_step_is_pinned():
    text = (WORKFLOWS_DIR / "release.yml").read_text(encoding="utf-8")
    assert re.search(
        r"uses: softprops/action-gh-release@[0-9a-f]{40}", text
    ), "release publication step must stay SHA-pinned"
