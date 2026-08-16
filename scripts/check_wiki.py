"""Quality gates for the wiki source tree in `docs/wiki/`.

Checks internal link resolution, EN/TR page parity, heading parity, sidebar
completeness, orphan pages, forbidden terms, and asset references.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


RESERVED = {"_Sidebar", "_Footer", "README", "PUBLISHING"}
# Maintainer docs that live here but are never mirrored to the wiki.
NOT_PUBLISHED = {"README", "PUBLISHING"}
WIKI_LINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")
MD_LINK = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
# GitHub serves wiki assets from this prefix; relative subdirectory paths do not
# resolve reliably in rendered wiki pages, so pages reference the raw URL and
# this checker maps it back to the file that must exist in `docs/wiki/`.
WIKI_RAW_PREFIX = "https://raw.githubusercontent.com/wiki/mskomek/hpc-client-gui/"
HEADING = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
FORBIDDEN = [
    (re.compile(r"(?i)\bdeepseek\b"), "internal orchestration tooling"),
    (re.compile(r"(?i)\bopencode\b"), "internal orchestration tooling"),
    (re.compile(r"\.agent-runs"), "internal orchestration tooling"),
    (re.compile(r"(?<![\w./-])waves/"), "internal orchestration tooling"),
    (
        re.compile(
            r"\bHPL\b|\bLLI\b|\bL(?:OMMAND|ONFIRM|REATE|ANCEL|OPY|ONNECT|HECK)\b"
            r"|\bL(?:reate|onnect|opy|ancel|ancelled|onfirm|onfig|ommand|heck|urrent|lient|hange)\b"
        ),
        "corrupted branding token",
    ),
    (re.compile(r"conoig|JSnN"), "corrupted branding token"),
    (re.compile(r"TrubaGUI|truba_gui"), "stale module or project path"),
]


def _pages(wiki_root: Path) -> dict[str, Path]:
    return {p.stem: p for p in sorted(wiki_root.glob("*.md"))}


def _link_targets(text: str) -> list[str]:
    return [(m.group(2) or m.group(1)).strip() for m in WIKI_LINK.finditer(text)]


def check_wiki(wiki_root: Path) -> list[str]:
    problems: list[str] = []
    pages = _pages(wiki_root)
    if not pages:
        return [f"{wiki_root}: no wiki pages found"]

    content = {name: path.read_text(encoding="utf-8") for name, path in pages.items()}
    articles = {n for n in pages if n not in RESERVED}
    english = {n for n in articles if not n.endswith("-TR")}
    turkish = {n[:-3] for n in articles if n.endswith("-TR")}

    for name in sorted(english - turkish):
        problems.append(f"{name}.md: missing Turkish counterpart {name}-TR.md")
    for name in sorted(turkish - english):
        problems.append(f"{name}-TR.md: missing English counterpart {name}.md")

    for name in sorted(english & turkish):
        en_headings = len(HEADING.findall(content[name]))
        tr_headings = len(HEADING.findall(content[f"{name}-TR"]))
        if en_headings != tr_headings:
            problems.append(
                f"{name}: heading count differs (EN {en_headings}, TR {tr_headings})"
            )

    for name in sorted(set(pages) - NOT_PUBLISHED):
        for target in _link_targets(content[name]):
            if target not in pages:
                problems.append(f"{name}.md: unresolved wiki link [[{target}]]")
        for ref in MD_LINK.findall(content[name]):
            if ref.startswith(WIKI_RAW_PREFIX):
                ref = ref[len(WIKI_RAW_PREFIX) :]
            elif ref.startswith(("http://", "https://", "data:")):
                continue
            if not (wiki_root / ref).exists():
                problems.append(f"{name}.md: unresolved asset reference {ref}")
        for pattern, reason in FORBIDDEN:
            match = pattern.search(content[name])
            if match:
                problems.append(f"{name}.md: forbidden term {match.group(0)!r} ({reason})")

    sidebar = content.get("_Sidebar")
    if sidebar is None:
        problems.append("_Sidebar.md: missing")
    else:
        linked = set(_link_targets(sidebar))
        for name in sorted(articles - linked):
            problems.append(f"{name}.md: not listed in _Sidebar.md")

    linked_anywhere = {
        target
        for name, text in content.items()
        if name != "_Sidebar"
        for target in _link_targets(text)
    }
    for name in sorted(articles - linked_anywhere - {"Home", "Home-TR"}):
        problems.append(f"{name}.md: orphan page, no other page links to it")

    return problems


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1] / "docs" / "wiki"
    problems = check_wiki(root)
    if not problems:
        print("wiki check: OK")
        return 0
    print(f"wiki check: FAILED ({len(problems)})")
    for item in problems:
        print("  -", item)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
