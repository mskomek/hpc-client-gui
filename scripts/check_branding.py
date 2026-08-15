"""Guard against the branding-rename string corruption fixed in Wave 42.

The 2d22678 branding rename mangled user-visible strings ("Create" -> "Lreate",
"config" -> "conoig", "JSON" -> "JSnN"). This check keeps those patterns from
silently returning.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


CORRUPT_PATTERNS = [
    re.compile(r"\bHPL\b"),
    re.compile(r"\bLlient\b"),
    re.compile(r"\bLLI\b"),
    re.compile(
        r"\bL(?:reate|onnect|opy|ancel|ancelled|onfirm|onfig|ommand|heck|urrent|lient|hange)\b"
    ),
    re.compile(r"\bL(?:OMMAND|ONFIRM|REATE|ANCEL|OPY|ONNECT|HECK)\b"),
    re.compile(r"conoig"),
    re.compile(r"JSnN"),
]
SCAN_SUFFIXES = {".py", ".md", ".json", ".ps1", ".yml", ".yaml", ".txt"}
SCAN_ROOTS = ("src", "docs", "scripts", "tests", "README.md", "SECURITY.md", "SUPPORT.md")
SKIP_PARTS = {"__pycache__", ".git", "node_modules"}


def _iter_files(base: Path):
    for entry in SCAN_ROOTS:
        target = base / entry
        if target.is_file():
            yield target
        elif target.is_dir():
            for path in sorted(target.rglob("*")):
                if path.is_file() and path.suffix in SCAN_SUFFIXES:
                    if not SKIP_PARTS.intersection(path.parts):
                        yield path


def find_corrupt_strings(base: Path) -> list[str]:
    findings: list[str] = []
    # The checkers spell the corrupt tokens out on purpose.
    checkers = {
        (Path(__file__).parent / name).resolve()
        for name in ("check_branding.py", "check_wiki.py")
    }
    for path in _iter_files(base):
        if path.resolve() in checkers:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in CORRUPT_PATTERNS:
                if pattern.search(line):
                    rel = path.relative_to(base)
                    findings.append(f"{rel}:{lineno}: {line.strip()}")
                    break
    return findings


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    base = Path(argv[0]) if argv else Path(__file__).resolve().parents[1]
    findings = find_corrupt_strings(base)
    if not findings:
        print("branding string check: OK")
        return 0
    print(f"branding string check: FAILED ({len(findings)})")
    for item in findings:
        print("  -", item)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
