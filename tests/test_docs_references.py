"""Documentation integrity: referenced local files must exist.

Docs are only trustworthy when every local file they reference is actually
present in the repository. This test scans tracked Markdown files for
relative links and verifies each target exists.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [ROOT / line.strip() for line in out.splitlines() if line.strip()]


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def test_referenced_local_files_exist() -> None:
    errors: list[str] = []
    for path in _tracked_files():
        if path.suffix.lower() != ".md":
            continue
        if not path.is_file():
            continue  # Deleted tracked files are outside this link check.
        text = _strip_code_blocks(path.read_text(encoding="utf-8", errors="replace"))
        for match in LINK_RE.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:", "data:")):
                continue
            clean = target.split("#", 1)[0].strip()
            if not clean or "<" in clean:
                continue  # anchors only or templated placeholder
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not errors, "Referenced local files missing:\n" + "\n".join(errors)


def test_agent_guidance_points_at_single_authority() -> None:
    # AGENTS.md is intentionally local-only (gitignored); the public
    # contribution workflow lives in CONTRIBUTING.md.
    agents = ROOT / "AGENTS.md"
    if agents.exists():
        text = agents.read_text(encoding="utf-8")
        assert "rules.md" in text
        assert "pull request" in text.lower()
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "pull request" in contributing.lower()
