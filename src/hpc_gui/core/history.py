import json
import os
import tempfile
from threading import Lock
from pathlib import Path
from datetime import datetime

from hpc_gui.services.command_history_store import is_sensitive_command
from hpc_gui.core.paths import app_data_dir


_HISTORY_LOCK = Lock()


def _redact_cmd(cmd: str) -> str:
    """Redact secrets inside a command string.

    We avoid persisting secrets entirely in command history. For event logs,
    we store a redacted placeholder when the command looks sensitive.
    """
    if is_sensitive_command(cmd):
        return "<redacted>"
    return cmd


def _sanitize_event(event: dict) -> dict:
    e = dict(event or {})
    # Never persist plaintext password-like keys if they appear.
    for k in list(e.keys()):
        if str(k).lower() in {"password", "pass", "passphrase", "parola", "sifre", "secret", "token", "api_key", "apikey"}:
            e[k] = "<redacted>"
    if "cmd" in e and isinstance(e["cmd"], str):
        e["cmd"] = _redact_cmd(e["cmd"])
    return e

def _history_path() -> Path:
    return app_data_dir() / "history.json"


def _backup_corrupt_history(path: Path) -> None:
    backup = path.with_name(path.name + ".bak")
    index = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak.{index}")
        index += 1
    path.replace(backup)


def _write_history(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            path.chmod(0o600)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def append_event(event: dict) -> None:
    p = _history_path()
    with _HISTORY_LOCK:
        data: list[dict] = []
        if p.exists():
            try:
                loaded = json.loads(p.read_text(encoding="utf-8"))
                if not isinstance(loaded, list) or not all(isinstance(item, dict) for item in loaded):
                    raise ValueError("history must be a JSON array of objects")
                data = loaded
            except Exception:
                _backup_corrupt_history(p)
        event = _sanitize_event(event)
        event["ts"] = datetime.now().isoformat(timespec="seconds")
        data.append(event)
        _write_history(p, data)
