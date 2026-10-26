from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Dict, Iterator

from hpc_gui.core.paths import app_data_dir


_COMPAT_PATH_PROVIDER: ContextVar[Callable[[], Path] | None] = ContextVar(
    "hpc_gui_config_path_provider", default=None
)
_COMPAT_SAVE_WRITER: ContextVar[Callable[[Dict[str, Any]], None] | None] = ContextVar(
    "hpc_gui_config_save_writer", default=None
)


@contextmanager
def _compat_config_io(
    path_provider: Callable[[], Path],
    save_writer: Callable[[Dict[str, Any]], None],
) -> Iterator[None]:
    """Bind facade hooks for one synchronous configuration operation.

    The public ``storage`` module historically exposed monkeypatchable path
    and writer seams. Keep those seams working after the implementation was
    split into leaf modules without changing process-global state.
    """
    path_token = _COMPAT_PATH_PROVIDER.set(path_provider)
    save_token = _COMPAT_SAVE_WRITER.set(save_writer)
    try:
        yield
    finally:
        _COMPAT_SAVE_WRITER.reset(save_token)
        _COMPAT_PATH_PROVIDER.reset(path_token)


def _default_config_path() -> Path:
    return app_data_dir() / "config.json"


def _config_dir() -> Path:
    return app_data_dir()


def _config_path() -> Path:
    provider = _COMPAT_PATH_PROVIDER.get()
    return Path(provider()) if provider is not None else _default_config_path()


def _next_config_backup(path: Path) -> Path:
    backup = path.with_name(path.name + ".bak")
    index = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak.{index}")
        index += 1
    return backup


def _backup_corrupt_config(path: Path) -> None:
    path.replace(_next_config_backup(path))


def _backup_before_migration(path: Path) -> None:
    """Keep a rollback copy before a migration replaces valid user data."""
    if path.exists():
        shutil.copy2(path, _next_config_backup(path))


def load_config() -> Dict[str, Any]:
    p = _config_path()
    if not p.exists():
        return {"profiles": [], "settings": {}}
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("config root must be a JSON object")
        if not isinstance(loaded.get("profiles", []), list):
            raise ValueError("config profiles must be a JSON array")
        if not isinstance(loaded.get("settings", {}), dict):
            raise ValueError("config settings must be a JSON object")
        return loaded
    except Exception:
        # corrupted config; keep a backup and start fresh
        try:
            _backup_corrupt_config(p)
        except Exception:
            pass
        return {"profiles": [], "settings": {}}


def load_settings() -> Dict[str, Any]:
    """Load application-wide settings stored in config.json.

    Settings are kept separate from profiles.
    """
    cfg = load_config()
    st = cfg.get("settings", {})
    return st if isinstance(st, dict) else {}


def update_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Merge patch into settings and persist."""
    cfg = load_config()
    st = cfg.get("settings")
    if not isinstance(st, dict):
        st = {}
    for k, v in (patch or {}).items():
        st[k] = v
    cfg["settings"] = st
    save_config(cfg)
    return st


def _save_config_payload(cfg: Dict[str, Any], path: Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        p.parent.chmod(0o700)
    fd, tmp_name = tempfile.mkstemp(
        prefix=p.name + ".", suffix=".tmp", dir=p.parent
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(cfg, ensure_ascii=False, indent=2))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
        if os.name == "posix":
            p.chmod(0o600)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def save_config(cfg: Dict[str, Any]) -> None:
    writer = _COMPAT_SAVE_WRITER.get()
    if writer is not None:
        writer(cfg)
        return
    _save_config_payload(cfg, _config_path())
