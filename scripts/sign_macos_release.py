"""Sign, notarize, staple, and verify one macOS release bundle.

This script is intentionally Darwin-only and reads credentials exclusively from
the protected CI environment. It never prints secret values.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import platform
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path


class SigningError(RuntimeError):
    pass


def _run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=capture, text=True, timeout=600)
    if result.returncode:
        raise SigningError(f"command failed: {command[0]}")
    return result


def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SigningError(f"missing protected secret: {name}")
    return value


def _write_b64(value: str, path: Path) -> None:
    try:
        path.write_bytes(base64.b64decode(value, validate=True))
    except (ValueError, OSError) as exc:
        raise SigningError("invalid base64 signing material") from exc
    path.chmod(0o600)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sign_app(app: Path, identity: str, entitlements: Path) -> None:
    candidates = sorted(
        (p for p in app.rglob("*") if p.is_file() and (p.suffix in {".dylib", ".so"} or os.access(p, os.X_OK))),
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for path in candidates:
        _run(["codesign", "--force", "--options", "runtime", "--timestamp", "--sign", identity, "--entitlements", str(entitlements), str(path)])
    _run(["codesign", "--force", "--options", "runtime", "--timestamp", "--sign", identity, "--entitlements", str(entitlements), str(app)])
    _run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    _run(["codesign", "-dv", "--verbose=4", str(app)])


def sign_and_notarize(app: Path, dmg: Path, entitlements: Path, arch: str) -> Path:
    if os.sys.platform != "darwin" or platform.machine().lower() not in {arch, "aarch64" if arch == "arm64" else "x86_64"}:
        raise SigningError("signing requires a native Darwin runner")
    if not app.is_dir() or not dmg.is_file():
        raise SigningError("app or DMG input is missing")
    certificate = _required("MACOS_CERTIFICATE_P12_BASE64")
    certificate_password = _required("MACOS_CERTIFICATE_PASSWORD")
    identity = os.environ.get("MACOS_SIGNING_IDENTITY", "")
    team_id = _required("APPLE_TEAM_ID")
    key_id = _required("APPLE_NOTARY_KEY_ID")
    issuer_id = _required("APPLE_NOTARY_ISSUER_ID")
    private_key = _required("APPLE_NOTARY_PRIVATE_KEY_BASE64")
    keychain_name = f"hpc-release-{secrets.token_hex(8)}.keychain-db"
    keychain = Path.home() / "Library" / "Keychains" / keychain_name
    keychain_password = secrets.token_urlsafe(32)
    try:
        with tempfile.TemporaryDirectory(prefix="hpc-macos-sign-") as temp:
            temp_dir = Path(temp)
            cert_path = temp_dir / "certificate.p12"
            notary_key = temp_dir / "notary-key.p8"
            _write_b64(certificate, cert_path)
            _write_b64(private_key, notary_key)
            _run(["security", "create-keychain", "-p", keychain_password, str(keychain)])
            _run(["security", "set-keychain-settings", "-lut", "900", str(keychain)])
            _run(["security", "unlock-keychain", "-p", keychain_password, str(keychain)])
            _run(["security", "import", str(cert_path), "-k", str(keychain), "-P", certificate_password, "-T", "/usr/bin/codesign"])
            _run(["security", "set-key-partition-list", "-S", "apple-tool:,apple:", "-s", "-k", keychain_password, str(keychain)])
            if not identity:
                identities = _run(["security", "find-identity", "-v", "-p", "codesigning", str(keychain)]).stdout.splitlines()
                identity = next((line.split('"')[1] for line in identities if '"Developer ID Application:' in line), "")
            if not identity:
                raise SigningError("Developer ID Application identity not found")
            _sign_app(app, identity, entitlements)
            dmg.unlink(missing_ok=True)
            stage = dmg.parent / f"macos_{arch}" / "dmg-root"
            if stage.exists():
                shutil.rmtree(stage)
            stage.mkdir(parents=True)
            # Keep framework symlinks intact when rebuilding the signed DMG.
            shutil.copytree(app, stage / app.name, symlinks=True)
            (stage / "Applications").symlink_to("/Applications")
            _run(["hdiutil", "create", "-format", "UDZO", "-srcfolder", str(stage), str(dmg)])
            _run(["xcrun", "notarytool", "submit", str(dmg), "--key", str(notary_key), "--key-id", key_id, "--issuer", issuer_id, "--team-id", team_id, "--wait"])
            _run(["xcrun", "stapler", "staple", str(dmg)])
            _run(["xcrun", "stapler", "validate", str(dmg)])
            if shutil.which("spctl"):
                _run(["spctl", "-a", "-vv", str(app)])
            checksum = dmg.with_name(dmg.name + ".sha256")
            checksum.write_text(f"{_sha256(dmg)}  {dmg.name}\n", encoding="ascii")
            return checksum
    finally:
        subprocess.run(["security", "delete-keychain", str(keychain)], capture_output=True, text=True, timeout=30)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sign_macos_release")
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--dmg", required=True, type=Path)
    parser.add_argument("--entitlements", required=True, type=Path)
    parser.add_argument("--arch", choices=("arm64", "x86_64"), required=True)
    args = parser.parse_args(argv)
    try:
        sign_and_notarize(args.app.resolve(), args.dmg.resolve(), args.entitlements.resolve(), args.arch)
        print("macOS signing and notarization completed")
        return 0
    except SigningError as exc:
        print(f"sign_macos_release: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
