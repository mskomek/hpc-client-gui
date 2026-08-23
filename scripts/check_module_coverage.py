#!/usr/bin/env python3
"""Module-specific coverage floors (read from a coverage.py XML report).

Global coverage alone can hide regressions in small, security-relevant
modules. This script enforces per-module minimums for the areas that most
need protection; values start at measured current levels minus a small
tolerance and may only be lowered deliberately.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# module path prefix -> required line-coverage percentage
FLOORS = {
    "src/hpc_gui/plugins/installer.py": 80,
    "src/hpc_gui/plugins/registry_client.py": 90,
    "src/hpc_gui/plugins/downloader.py": 90,
    "src/hpc_gui/plugins/validator.py": 70,
    "src/hpc_gui/services/transfer_controller.py": 85,
    "src/hpc_gui/config/storage.py": 70,
}


def class_coverage(xml_path: Path) -> dict[str, int]:
    tree = ET.parse(xml_path)
    result: dict[str, int] = {}
    for klass in tree.iter("class"):
        filename = klass.get("filename")
        if filename in FLOORS:
            lines = klass.find("lines")
            total = len(lines)
            hit = sum(1 for line in lines if line.get("hits") != "0")
            result[filename] = round(hit * 100 / max(total, 1))
    return result


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    xml_path = Path(sys.argv[1] if len(sys.argv) > 1 else "coverage.xml")
    if not xml_path.is_file():
        print(f"FAIL: coverage XML not found: {xml_path}")
        return 2
    measured = class_coverage(xml_path)
    failures = []
    for module, floor in sorted(FLOORS.items()):
        actual = measured.get(module)
        if actual is None:
            failures.append(f"{module}: not present in coverage report")
        elif actual < floor:
            failures.append(f"{module}: {actual}% < required {floor}%")
        else:
            print(f"OK {module}: {actual}% >= {floor}%")
    if failures:
        print("FAIL: module coverage floors:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: all module coverage floors met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
