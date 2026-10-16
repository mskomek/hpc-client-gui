"""Validation rules for Linux release definition files."""

from __future__ import annotations

import json
import re
from pathlib import Path


class PackagingError(RuntimeError):
    """An actionable Linux packaging failure."""


def validate_desktop_entry(path: Path) -> None:
    """Validate the static AppImage .desktop entry."""
    if not path.is_file():
        raise PackagingError(f"AppImage desktop entry missing: {path}")
    text = path.read_text(encoding="utf-8")
    if "[Desktop Entry]" not in text:
        raise PackagingError(f"AppImage desktop entry has no [Desktop Entry] section: {path}")
    if not re.search(r"(?m)^Exec=\S+$", text):
        raise PackagingError(f"AppImage desktop entry has no Exec= line: {path}")
    if not re.search(r"(?m)^Name=", text):
        raise PackagingError(f"AppImage desktop entry has no Name= line: {path}")


def validate_apprun(path: Path) -> None:
    """Validate the AppImage AppRun launcher and require a shebang."""
    if not path.is_file():
        raise PackagingError(f"AppImage AppRun launcher missing: {path}")
    if not path.read_text(encoding="utf-8").startswith("#!"):
        raise PackagingError(f"AppImage AppRun has no shebang: {path}")


def validate_deb_control(path: Path) -> None:
    """Validate .deb metadata against the current wxPython Linux package."""
    if not path.is_file():
        raise PackagingError(f".deb control file missing: {path}")
    text = path.read_text(encoding="utf-8")
    for required_field in ("Package:", "Version:", "Architecture:", "Description:"):
        if not re.search(rf"(?m)^{re.escape(required_field)}", text):
            raise PackagingError(f".deb control file has no {required_field} field: {path}")
    if "<VERSION>" not in text:
        raise PackagingError(f".deb control file has no <VERSION> placeholder: {path}")
    if "wxPython" not in text or "WebKitGTK" not in text or "PySide6" in text:
        raise PackagingError(f".deb control description does not match the Linux GUI runtime: {path}")


def validate_flatpak_manifest(path: Path) -> None:
    """Validate a Flatpak manifest's syntax and required keys."""
    if not path.is_file():
        raise PackagingError(f"Flatpak manifest missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackagingError(f"Flatpak manifest is not valid JSON: {exc}") from exc
    for key in ("app-id", "runtime", "sdk", "command", "modules"):
        if key not in data:
            raise PackagingError(f"Flatpak manifest has no {key} key: {path}")
    if not isinstance(data.get("modules"), list) or not data["modules"]:
        raise PackagingError(f"Flatpak manifest modules must be a non-empty list: {path}")


def validate_pip_metadata(pyproject: Path, entry: Path) -> None:
    """Verify the pip/source path is well-formed (entry point + dependencies)."""
    if not pyproject.is_file():
        raise PackagingError(f"pyproject.toml missing: {pyproject}")
    text = pyproject.read_text(encoding="utf-8")
    if "requires-python" not in text:
        raise PackagingError("pyproject.toml has no requires-python declaration.")
    for dep in ("PySide6", "paramiko", "cryptography"):
        if dep not in text:
            raise PackagingError(f"pyproject.toml missing dependency {dep}.")
    if not entry.is_file():
        raise PackagingError(f"pip entry point missing: {entry}")
