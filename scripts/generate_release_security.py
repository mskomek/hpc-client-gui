"""Generate machine-readable release security metadata (RELEASE_SECURITY.json).

The file records what actually happened to the macOS artifacts so users and
automated verifiers never have to guess whether a DMG was Developer ID
signed, notarized, stapled, and Gatekeeper-assessed. The workflow generates
it from the selected ``macos_mode`` after the corresponding verification job
succeeded; an unsigned release can therefore never claim signing.

Usage:
    python scripts/generate_release_security.py \
        --release-dir dist/releases/v1.5.1 --version v1.5.1 \
        --commit <sha> --mode signed-notarized \
        --arch arm64 --arch x86_64
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SECURITY_NAME = "RELEASE_SECURITY.json"
MACOS_MODES = ("signed-notarized", "unsigned")


def build_security_metadata(
    version: str,
    commit: str,
    mode: str,
    architectures: list[str],
) -> dict[str, object]:
    signed = mode == "signed-notarized"
    return {
        "schema": 1,
        "release": version,
        "source_commit": commit,
        "macos_mode": mode,
        "developer_id_verification_passed": signed,
        "notarization_passed": signed,
        "stapling_passed": signed,
        "gatekeeper_assessment_passed": signed,
        "artifact_architectures": sorted(set(architectures)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--mode",
        choices=MACOS_MODES,
        required=True,
        help="signed-notarized or unsigned",
    )
    parser.add_argument(
        "--arch",
        action="append",
        choices=("arm64", "x86_64"),
        required=True,
        dest="architectures",
    )
    args = parser.parse_args(argv)

    release_dir = args.release_dir.resolve()
    if not release_dir.is_dir():
        print(f"release directory does not exist: {release_dir}", file=sys.stderr)
        return 2

    metadata = build_security_metadata(
        version=args.version,
        commit=args.commit,
        mode=args.mode,
        architectures=list(args.architectures),
    )
    target = release_dir / SECURITY_NAME
    target.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"RELEASE_SECURITY: {target} (macos_mode={args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
