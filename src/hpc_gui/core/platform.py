from __future__ import annotations

import platform as _platform
import sys


def current_os(platform_name: str | None = None) -> str:
    """Return the application's stable operating-system key."""
    value = (platform_name if platform_name is not None else sys.platform).lower()
    if value.startswith("win"):
        return "windows"
    if value.startswith("linux"):
        return "linux"
    if value == "darwin":
        return "macos"
    return "unsupported"


def current_architecture(machine: str | None = None) -> str:
    """Return the stable release architecture key, or ``unsupported``."""
    value = (machine if machine is not None else _platform.machine()).lower()
    if value in {"arm64", "aarch64"}:
        return "arm64"
    if value in {"x86_64", "amd64"}:
        return "x86_64"
    return "unsupported"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def release_platform_key(platform_name: str | None = None, machine: str | None = None) -> str:
    os_key = current_os(platform_name)
    architecture = current_architecture(machine)
    if os_key == "unsupported" or architecture == "unsupported":
        raise RuntimeError(f"Unsupported release platform: {os_key}/{architecture}")
    return f"{os_key}_{architecture}"
