"""Write the exact runtime versions used by a release build."""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import sys
from pathlib import Path

PACKAGES = (
    ("PySide6", "PySide6"),
    ("Shiboken6", "shiboken6"),
    ("PySide6-Essentials", "PySide6-Essentials"),
    ("PySide6-Addons", "PySide6-Addons"),
    ("PyInstaller", "PyInstaller"),
    ("Paramiko", "paramiko"),
    ("Cryptography", "cryptography"),
)


def package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError(f"Required release dependency is not installed: {distribution}") from exc


def collect(version: str) -> list[tuple[str, str]]:
    try:
        from PySide6.QtCore import qVersion
    except ImportError as exc:
        raise RuntimeError("PySide6/Qt runtime could not be imported") from exc
    qt_version = qVersion()
    if not qt_version:
        raise RuntimeError("PySide6/Qt runtime returned no version")
    values = [("HPC Client GUI", version), ("Python", sys.version.split()[0])]
    values.extend((name, package_version(distribution)) for name, distribution in PACKAGES)
    values.append(("Qt runtime", qt_version))
    return values


def write_manifest(output: Path, values: list[tuple[str, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text("".join(f"{name}: {value}\n" for name, value in values), encoding="utf-8")
    os.replace(temporary, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("THIRD_PARTY_VERSIONS.txt"))
    args = parser.parse_args()
    try:
        write_manifest(args.output, collect(args.version))
    except RuntimeError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
