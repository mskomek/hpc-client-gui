"""Generate a deterministic CycloneDX inventory from a pinned pip lock."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Mapping

from packaging.markers import default_environment
from packaging.requirements import Requirement


def read_lock(path: Path, environment: Mapping[str, str] | None = None) -> list[tuple[str, str]]:
    marker_environment = default_environment()
    if environment is not None:
        marker_environment.update(environment)
    components = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except ValueError as exc:
            raise ValueError(f"Unsupported or unpinned lock entry: {line}") from exc
        if not requirement.specifier or len(requirement.specifier) != 1:
            raise ValueError(f"Unsupported or unpinned lock entry: {line}")
        specifier = next(iter(requirement.specifier))
        if specifier.operator != "==":
            raise ValueError(f"Unsupported or unpinned lock entry: {line}")
        if requirement.marker is not None and not requirement.marker.evaluate(marker_environment):
            continue
        components.append((requirement.name, specifier.version))
    return sorted(components, key=lambda item: item[0].lower())


def write_sbom(lock: Path, output: Path, application_version: str) -> None:
    components = [
        {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
        }
        for name, version in read_lock(lock)
    ]
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "HPC Client GUI",
                "version": application_version,
            }
        },
        "components": components,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("requirements-release.lock"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("SBOM.cdx.json"))
    args = parser.parse_args()
    try:
        write_sbom(args.lock, args.output, args.version)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
