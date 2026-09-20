from __future__ import annotations

import os
import shutil
from pathlib import Path

from hpc_gui.core.platform import current_os


_LEGACY_DIRNAME = ".truba_slurm_gui"
_MAC_APP_NAME = "HPC Client GUI"

#: Environment variable naming an isolated per-run config root. When set to a
#: non-blank directory, all per-user state (config, logs, history, third-party
#: downloads) lives under it instead of the real home directory, so fresh-user
#: packaged acceptance never touches a developer profile (PKG-GJ-01).
ISOLATED_CONFIG_ROOT_ENV = "HPC_GUI_CONFIG_ROOT"
_MIGRATABLE_NAMES = {
    "config.json",
    "language.json",
    "history.json",
    "history.jsonl",
    "last_batch.json",
    "processes.json",
    "transfer_journal.jsonl",
    "known_hosts",
    "plugins",
    "private",
    "third_party",
    "updates",
    "templates",
}


def legacy_app_data_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / _LEGACY_DIRNAME


def _mac_support_dir(home: Path) -> Path:
    return home / "Library" / "Application Support" / _MAC_APP_NAME


def _mac_log_dir(home: Path) -> Path:
    return home / "Library" / "Logs" / _MAC_APP_NAME


def isolated_config_root() -> Path | None:
    """Return the isolated per-run config root, or ``None`` for default.

    A non-blank ``HPC_GUI_CONFIG_ROOT`` redirects every per-user location so
    a packaged first-run can be proven without hand-editing hidden config or
    contaminating the developer profile. The directory is created on demand;
    a path that cannot be created raises instead of silently falling back.
    """
    raw = os.environ.get(ISOLATED_CONFIG_ROOT_ENV, "")
    if not raw.strip():
        return None
    root = Path(raw.strip()).expanduser()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"Cannot create isolated config root: {exc}") from exc
    if os.name == "posix":
        try:
            root.chmod(0o700)
        except OSError:
            pass
    return root


def app_log_dir(home: Path | None = None) -> Path:
    override = isolated_config_root()
    if override is not None:
        path = override / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    root = home or Path.home()
    path = _mac_log_dir(root) if current_os() == "macos" else legacy_app_data_dir(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _copy_legacy_entry(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise RuntimeError(f"Refusing to migrate symlinked application data: {source.name}")
    if source.is_dir() and any(path.is_symlink() for path in source.rglob("*")):
        raise RuntimeError(f"Refusing to migrate symlinked application data: {source.name}")
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def migrate_legacy_app_data(*, home: Path | None = None) -> bool:
    """Copy known legacy data to macOS Application Support once, never delete it."""
    if current_os() != "macos":
        return False
    root = home or Path.home()
    legacy = legacy_app_data_dir(root)
    target = _mac_support_dir(root)
    if target.exists() or not legacy.is_dir() or legacy.is_symlink():
        return False
    target.mkdir(parents=True)
    try:
        for source in legacy.iterdir():
            if source.name in _MIGRATABLE_NAMES:
                _copy_legacy_entry(source, target / source.name)
        legacy_log = legacy / "app.log"
        if legacy_log.is_file() and not legacy_log.is_symlink():
            log_target = _mac_log_dir(root)
            log_target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_log, log_target / legacy_log.name)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return True


def app_data_dir() -> Path:
    """Per-user app data directory used for logs/config/3rd-party downloads."""
    override = isolated_config_root()
    if override is not None:
        return override
    home = Path.home()
    if current_os() == "macos":
        migrate_legacy_app_data(home=home)
        base = _mac_support_dir(home)
    else:
        base = legacy_app_data_dir(home)
    base.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        base.chmod(0o700)
    return base


def third_party_dir() -> Path:
    d = app_data_dir() / "third_party"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_frozen_exe() -> bool:
    return bool(getattr(os, "frozen", False) or getattr(__import__("sys"), "frozen", False))
