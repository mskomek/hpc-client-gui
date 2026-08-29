#!/usr/bin/env python3
"""Synchronize generated/runtime version declarations from one version input."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def sync_version(root: Path, version: str) -> None:
    if not SEMVER.fullmatch(version):
        raise ValueError("version must be semantic X.Y.Z")
    files = {
        "pyproject.toml": [(r'(?m)^version = "[^"]+"$', f'version = "{version}"')],
        "src/hpc_gui/__init__.py": [(r"__version__ = '[^']+'", f"__version__ = '{version}'")],
        "src/hpc_gui/cli/main.py": [(r'CLI_VERSION = "[^"]+"', f'CLI_VERSION = "{version}"')],
        "build/windows/version_info.txt": [
            (r"filevers=\(\d+, \d+, \d+, \d+\)", f"filevers=({', '.join(version.split('.'))}, 0)"),
            (r"prodvers=\(\d+, \d+, \d+, \d+\)", f"prodvers=({', '.join(version.split('.'))}, 0)"),
            (r"(FileVersion|ProductVersion)', '\d+\.\d+\.\d+'", lambda m: f"{m.group(1)}', '{version}'"),
        ],
        "build/macos/hpc-client-gui.spec": [
            (r'(APP_VERSION", ")[^"]+(")', rf'\g<1>{version}\g<2>'),
        ],
        "docs/wiki/Release-History.md": [(r"current version is \*\*[^*]+\*\*", f"current version is **{version}**")],
        "docs/wiki/Release-History-TR.md": [(r"Geçerli sürüm \*\*[^*]+\*\*", f"Geçerli sürüm **{version}**")],
    }
    for relative, replacements in files.items():
        path = root / relative
        text = path.read_text(encoding="utf-8")
        for pattern, replacement in replacements:
            text, count = re.subn(pattern, replacement, text)
            if not count:
                raise ValueError(f"version declaration not found: {relative}")
        path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    sync_version(args.root.resolve(), args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
