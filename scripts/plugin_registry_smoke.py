#!/usr/bin/env python3
"""Manual live smoke test for the official plugin registry.

Run explicitly (never part of the automated suite):

    python scripts/plugin_registry_smoke.py

Checks that the real GitHub raw registry is reachable, parses, and that
every declared file of every plugin entry downloads and verifies.
Release builds must not depend on this succeeding.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from hpc_gui.plugins.registry_client import (  # noqa: E402
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    default_fetcher,
    parse_registry,
)


def main() -> int:
    print(f"Fetching {OFFICIAL_REGISTRY_URL} ...")
    try:
        payload = default_fetcher(OFFICIAL_REGISTRY_URL, 1024 * 1024)
    except Exception as exc:
        print(f"FAIL: registry fetch failed: {exc}")
        return 1
    try:
        registry = parse_registry(payload)
    except Exception as exc:
        print(f"FAIL: registry invalid: {exc}")
        return 1

    failures = 0
    plugins = [p for p in registry.get("plugins", []) if p.get("official")]
    print(f"OK: registry valid with {len(plugins)} official plugin(s).")
    for entry in plugins:
        label = f"{entry['id']}@{entry['version']}"
        try:
            manifest_bytes = default_fetcher(
                OFFICIAL_RAW_BASE + entry["manifest_path"], 256 * 1024
            )
            actual = hashlib.sha256(manifest_bytes).hexdigest()
            if actual != entry["manifest_sha256"]:
                raise RuntimeError("manifest SHA-256 mismatch")
            manifest = json.loads(manifest_bytes)
            base = entry["manifest_path"].rsplit("/", 1)[0]
            for file_entry in manifest["files"]:
                rel = f"{base}/{file_entry['path']}"
                data = default_fetcher(OFFICIAL_RAW_BASE + rel, 5 * 1024 * 1024)
                if hashlib.sha256(data).hexdigest() != file_entry["sha256"]:
                    raise RuntimeError(f"payload SHA-256 mismatch for {rel}")
                if len(data) != file_entry["size"]:
                    raise RuntimeError(f"payload size mismatch for {rel}")
            print(f"PASS: {label}")
        except Exception as exc:
            failures += 1
            print(f"FAIL: {label}: {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
