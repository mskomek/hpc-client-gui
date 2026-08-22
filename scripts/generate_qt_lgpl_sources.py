"""Generate verified corresponding-source records for the Qt runtime."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

COMPONENTS = ("PySide6", "Shiboken6", "PySide6-Essentials", "PySide6-Addons")


def read_versions(path: Path) -> dict[str, str]:
    versions = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, version = line.partition(": ")
        if separator:
            versions[name] = version
    missing = [name for name in COMPONENTS if name not in versions]
    if missing:
        raise ValueError(f"Version manifest is missing: {', '.join(missing)}")
    if len({versions[name] for name in COMPONENTS}) != 1:
        raise ValueError("PySide6 component versions do not match")
    return versions


def verify_url(url: str) -> None:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            response.read(1)
    except OSError as exc:
        raise RuntimeError(f"Unable to verify source URL: {url}") from exc


def write_sources(versions_path: Path, output: Path) -> None:
    versions = read_versions(versions_path)
    version = versions[COMPONENTS[0]]
    pyside_url = f"https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v{version}"
    qt_url = f"https://code.qt.io/cgit/qt/qt5.git/tag/?h=v{version}"
    verify_url(pyside_url)
    verify_url(qt_url)
    records = [
        {
            "component": name,
            "version": versions[name],
            "license": "LGPL-3.0-only",
            "source_project_url": "https://code.qt.io/cgit/pyside/pyside-setup.git/",
            "source_tag_url": pyside_url,
        }
        for name in COMPONENTS
    ]
    records.append(
        {
            "component": "Qt libraries",
            "version": version,
            "license": "LGPL-3.0-only",
            "source_project_url": "https://code.qt.io/cgit/qt/qt5.git/",
            "source_tag_url": qt_url,
        }
    )
    document = {"format": "qt-lgpl-corresponding-source", "version": 1, "records": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versions", type=Path, default=Path("THIRD_PARTY_VERSIONS.txt"))
    parser.add_argument("--output", type=Path, default=Path("QT_LGPL_SOURCES.json"))
    args = parser.parse_args()
    try:
        write_sources(args.versions, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
