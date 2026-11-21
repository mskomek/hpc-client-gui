"""Minimal MIT-MAGIC-COOKIE-1 support for Xauthority files.

This keeps X11 cookies out of command lines and logs, and lets the Windows
VcXsrv path use the same authenticated authority file as the SSH relay.
"""

from __future__ import annotations

import os
import shutil
import secrets
import subprocess
import struct
import sys
import tempfile
from pathlib import Path

_FAMILY_WILD = 0xFFFF
_MIT_COOKIE = b"MIT-MAGIC-COOKIE-1"


def find_xauth_executable() -> str | None:
    """Return the installed xauth executable, including the VcXsrv copy."""
    candidates = [shutil.which("xauth")]
    if sys.platform == "darwin":
        candidates.append("/opt/X11/bin/xauth")
    if os.name == "nt":
        for env_name in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            root = os.environ.get(env_name)
            if root:
                candidates.append(str(Path(root) / "Programs" / "VcXsrv" / "xauth.exe"))
                candidates.append(str(Path(root) / "VcXsrv" / "xauth.exe"))
    return next((item for item in candidates if item and Path(item).is_file()), None)


def _cookies_from_xauth_output(text: str) -> list[bytes]:
    """Select only valid MIT cookies; exclude other Xauthority protocols."""
    cookies = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] != _MIT_COOKIE.decode("ascii"):
            continue
        try:
            value = bytes.fromhex(parts[2])
        except ValueError:
            continue
        if len(value) == 16:
            cookies.append(value)
    return cookies


def create_untrusted_cookie(
    authority_path: str | Path,
    display_name: str,
    *,
    timeout_seconds: int = 3600,
    runner=subprocess.run,
) -> tuple[Path, bytes]:
    """Generate an X SECURITY untrusted cookie in a private authority copy.

    The X server must support the SECURITY extension. No trusted-cookie
    fallback is attempted; callers must make that choice explicitly.
    """
    executable = find_xauth_executable()
    source = Path(authority_path)
    if not executable or not source.is_file():
        raise RuntimeError("xauth or the local Xauthority file is unavailable")
    fd, temp_name = tempfile.mkstemp(prefix="hpc-x11-", suffix=".xauth", dir=source.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(source.read_bytes())
        if os.name == "posix":
            temp_path.chmod(0o600)
        env = os.environ.copy()
        env["XAUTHORITY"] = str(temp_path)
        list_command = [executable, "-f", str(temp_path), "list", display_name]
        original = runner(
            list_command, capture_output=True, text=True, timeout=5, env=env,
        )
        if original.returncode != 0:
            raise RuntimeError("cannot inspect existing trusted X11 credentials")
        trusted_cookies = set(_cookies_from_xauth_output(original.stdout or ""))
        command = [executable, "-f", str(temp_path), "generate", display_name,
                   ".", "untrusted", "timeout", str(max(1, int(timeout_seconds)))]
        generated = runner(command, capture_output=True, text=True, timeout=10, env=env)
        if generated.returncode != 0:
            raise RuntimeError("local X server does not support untrusted X11 cookies")
        listed = runner(
            list_command, capture_output=True, text=True, timeout=5, env=env,
        )
        new_cookies = [
            cookie for cookie in _cookies_from_xauth_output(listed.stdout or "")
            if cookie not in trusted_cookies
        ]
        if listed.returncode != 0 or len(set(new_cookies)) != 1:
            raise RuntimeError("xauth did not return a distinct untrusted X11 cookie")
        return temp_path, new_cookies[0]
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _field(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated Xauthority field")
    size = struct.unpack_from(">H", data, offset)[0]
    offset += 2
    end = offset + size
    if end > len(data):
        raise ValueError("truncated Xauthority value")
    return data[offset:end], end


def read_mit_cookie(path: str | Path, display: int) -> bytes | None:
    """Read a MIT cookie for one display, returning None on absent/malformed data."""
    try:
        records = Path(path).read_bytes()
    except OSError:
        return None
    display_number = str(int(display)).encode("ascii")
    offset = 0
    while offset < len(records):
        try:
            if offset + 2 > len(records):
                return None
            family = struct.unpack_from(">H", records, offset)[0]
            offset += 2
            _address, offset = _field(records, offset)
            number, offset = _field(records, offset)
            name, offset = _field(records, offset)
            data, offset = _field(records, offset)
        except (ValueError, struct.error):
            return None
        if (
            family == _FAMILY_WILD
            and number == display_number
            and name == _MIT_COOKIE
            and len(data) == 16
        ):
            return data
    return None


def create_mit_cookie_file(path: str | Path, display: int) -> bytes:
    """Create a single-entry FamilyWild Xauthority file with owner-only mode."""
    target = Path(path)
    cookie = secrets.token_bytes(16)
    fields = (b"", str(int(display)).encode("ascii"), _MIT_COOKIE, cookie)
    record = struct.pack(">H", _FAMILY_WILD) + b"".join(
        struct.pack(">H", len(value)) + value for value in fields
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(record)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if os.name == "posix":
        target.chmod(0o600)
    return cookie
