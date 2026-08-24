"""Bounded smoke checks for a packaged macOS app bundle."""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path


class SmokeFailure(RuntimeError):
    pass


def validate_app(app: Path, version: str | None = None) -> None:
    if not app.is_dir() or app.suffix != ".app":
        raise SmokeFailure(f"app bundle missing: {app}")
    contents = app / "Contents"
    info_path = contents / "Info.plist"
    if not info_path.is_file():
        raise SmokeFailure("Info.plist missing")
    if not shutil.which("plutil"):
        raise SmokeFailure("plutil is required on macOS")
    if subprocess.run(
        ["plutil", "-lint", str(info_path)], capture_output=True, text=True, timeout=10
    ).returncode:
        raise SmokeFailure("plutil rejected Info.plist")
    info = plistlib.loads(info_path.read_bytes())
    if info.get("CFBundleIdentifier") != "io.github.mskomek.HpcClientGui":
        raise SmokeFailure("bundle identifier mismatch")
    if info.get("CFBundleDisplayName") != "HPC Client GUI":
        raise SmokeFailure("bundle display name mismatch")
    if version and str(info.get("CFBundleShortVersionString")) != version:
        raise SmokeFailure("bundle version mismatch")
    if not list(contents.rglob("libqcocoa*.dylib")):
        raise SmokeFailure("Qt Cocoa platform plugin missing")
    if not list(contents.rglob("QtWebEngineProcess")):
        raise SmokeFailure("QtWebEngineProcess missing")
    if not list(contents.rglob("xterm.js")):
        raise SmokeFailure("embedded xterm.js missing")
    for path in app.rglob("*"):
        if path.name.lower() in {"plink.exe", "vcxsrv.exe", "powershell.exe"} or path.suffix.lower() == ".exe":
            raise SmokeFailure(f"Windows payload found: {path.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="macos_release_smoke")
    parser.add_argument("--app", required=True)
    parser.add_argument("--version")
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args(argv)
    app = Path(args.app).resolve()
    binary = app / "Contents" / "MacOS" / "HPC Client GUI"
    if os.sys.platform != "darwin":
        print("macos smoke: requires Darwin")
        return 1
    try:
        validate_app(app, args.version)
        if not binary.is_file():
            raise SmokeFailure(f"executable missing: {binary}")
        result = subprocess.run([str(binary), "--help"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise SmokeFailure(result.stderr[-2000:])
        if args.gui:
            with tempfile.TemporaryDirectory(prefix="hpc-macos-smoke-") as root:
                env = dict(os.environ, HOME=root, QT_QPA_PLATFORM="offscreen")
                proc = subprocess.Popen([str(binary)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=5)
                else:
                    raise SmokeFailure("GUI exited before the bounded smoke window")
    except (OSError, plistlib.InvalidFileException, SmokeFailure, subprocess.SubprocessError) as exc:
        print(f"macos smoke: {exc}")
        return 1
    print("macos smoke: CLI help OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
