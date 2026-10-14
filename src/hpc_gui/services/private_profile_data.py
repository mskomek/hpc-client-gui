"""Encrypted, namespaced private data stored per connection profile."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

from ..core import secret_store
from hpc_gui.core.paths import app_data_dir

_MAGIC = b"HPCPRV1\n"
_LEGACY_MAGICS = (b"HPCNAV1\n",)
_KEYRING_SERVICE = "hpc-client-gui"
_KEYRING_USERNAME = "remote-navigation"
_PROFILE_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_NAMESPACE = re.compile(r"^[a-z][a-z0-9_-]{0,40}$")
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _path(profile_id: str, namespace: str) -> Path:
    profile_id = str(profile_id or "").strip()
    namespace = str(namespace or "").strip()
    if not _PROFILE_ID.fullmatch(profile_id) or not _NAMESPACE.fullmatch(namespace):
        raise ValueError("invalid private profile data identity")
    directory = app_data_dir() / "private"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{profile_id}.bin" if namespace == "navigation" else f"{profile_id}.{namespace}.bin"
    return directory / filename


def _lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


def _fernet():
    try:
        import keyring
        from cryptography.fernet import Fernet
    except Exception:
        return None
    try:
        key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if not key:
            key = Fernet.generate_key().decode("ascii")
            keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key)
        return Fernet(key.encode("ascii"))
    except Exception:
        return None


def is_private_profile_data_available() -> bool:
    """Whether an OS-protected encryption key is available on this machine."""
    return secret_store.is_available() or _fernet() is not None


def _encrypt(payload: dict[str, Any]) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False)
    if secret_store.is_available():
        return _MAGIC + secret_store.protect_secret(raw).encode("ascii")
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError("no OS-held secret available for private profile data")
    return _MAGIC + fernet.encrypt(raw.encode("utf-8"))


def _decrypt(blob: bytes) -> dict[str, Any]:
    magic = next((item for item in (_MAGIC, *_LEGACY_MAGICS) if blob.startswith(item)), None)
    if magic is None:
        raise ValueError("unrecognised private profile data")
    body = blob[len(magic) :]
    if secret_store.is_available():
        raw = secret_store.unprotect_secret(body.decode("ascii"))
    else:
        fernet = _fernet()
        if fernet is None:
            raise RuntimeError("no OS-held secret available for private profile data")
        raw = fernet.decrypt(body).decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("unrecognised private profile data")
    return data


def load_private_profile_data(
    profile_id: str, namespace: str, default: dict[str, Any]
) -> dict[str, Any]:
    path = _path(profile_id, namespace)
    with _lock_for(path):
        try:
            return _decrypt(path.read_bytes())
        except FileNotFoundError:
            return dict(default)
        except Exception:
            return dict(default)


def save_private_profile_data(
    profile_id: str, namespace: str, payload: dict[str, Any]
) -> None:
    path = _path(profile_id, namespace)
    with _lock_for(path):
        blob = _encrypt(payload)
        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name + ".", suffix=".tmp", dir=path.parent
        )
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(blob)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise


def delete_private_profile_data(profile_id: str, namespace: str) -> None:
    path = _path(profile_id, namespace)
    with _lock_for(path):
        path.unlink(missing_ok=True)
