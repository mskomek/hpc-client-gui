"""Bounded smoke checks for a packaged macOS app bundle."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="macos_release_smoke")
    parser.add_argument("--app", required=True)
    args = parser.parse_args(argv)
    app = Path(args.app).resolve()
    binary = app / "Contents" / "MacOS" / "HPC Client GUI"
    if os.sys.platform != "darwin":
        print("macos smoke: requires Darwin")
        return 1
    if not binary.is_file():
        print(f"macos smoke: executable missing: {binary}")
        return 1
    result = subprocess.run([str(binary), "--help"], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(result.stderr[-2000:])
        return 1
    print("macos smoke: CLI help OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
