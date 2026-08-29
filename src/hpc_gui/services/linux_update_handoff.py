"""Safe, unprivileged Linux update handoff helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FlatpakContext:
    app_id: str
    scope: str
    origin: str
    update_command: tuple[str, ...] | None
    reason: str


def appimage_path(environ: dict[str, str] | None = None) -> Path | None:
    value = (environ or os.environ).get("APPIMAGE", "")
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_file() or path.is_symlink():
        return None
    return path.resolve()


def stage_appimage(source: Path, destination: Path) -> Path:
    """Stage verified bytes beside destination, preserving executable mode."""
    source = Path(source).expanduser()
    if source.is_symlink():
        raise ValueError("source must be a regular AppImage")
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if not source.is_file():
        raise ValueError("source must be a regular AppImage")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".part", dir=destination.parent)
    staged = Path(raw)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(staged, source.stat().st_mode & 0o777)
        return staged
    except Exception:
        staged.unlink(missing_ok=True)
        raise


def replace_appimage(staged: Path, destination: Path) -> Path:
    """Keep the old image as a recoverable sibling and atomically replace it."""
    staged = staged.resolve(strict=True)
    destination = destination.resolve()
    if staged.suffix != ".part" or not staged.is_file() or staged.is_symlink():
        raise ValueError("staged AppImage is invalid")
    backup = destination.with_name(destination.name + ".previous")
    if destination.exists():
        destination.replace(backup)
    try:
        staged.replace(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    return backup


def detect_flatpak(app_id: str, runner=subprocess.run) -> FlatpakContext:
    try:
        result = runner(["flatpak", "info", "--show-ref", app_id], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return FlatpakContext(app_id, "unknown", "", None, "Flatpak is unavailable.")
    if result.returncode != 0:
        return FlatpakContext(app_id, "unknown", "", None, "Flatpak application is not installed.")
    ref = (result.stdout or "").strip()
    scope = "user" if "user" in ref else "system"
    try:
        origin_result = runner(["flatpak", "info", "--show-origin", app_id], capture_output=True, text=True, timeout=3, check=False)
        origin = (origin_result.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        origin = ""
    return FlatpakContext(app_id, scope, origin, ("flatpak", "update", "--app", app_id), "Flatpak update is delegated to the system manager.")
