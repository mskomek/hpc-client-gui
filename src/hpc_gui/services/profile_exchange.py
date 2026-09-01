"""Versioned, credential-free profile export/import helpers."""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass
from typing import Any, Callable


FORMAT = "hpc-client-profile"
VERSION = 1
_SECRET = re.compile(r"password|passphrase|secret|credential|token|mfa|private.?key.?content|keychain", re.I)
_SHAREABLE = re.compile(r"username|account|project|private.?key|key.?path|password|secret|credential|token|mfa", re.I)


def _clean(value: Any, *, shareable: bool) -> Any:
    if isinstance(value, dict):
        return {
            key: _clean(item, shareable=shareable)
            for key, item in value.items()
            if not _SECRET.search(str(key)) and not (shareable and _SHAREABLE.search(str(key)))
        }
    if isinstance(value, list):
        return [_clean(item, shareable=shareable) for item in value]
    return value


def export_profile(profile: dict[str, Any], *, mode: str = "shareable") -> dict[str, Any]:
    if mode not in {"shareable", "personal"}:
        raise ValueError("mode must be shareable or personal")
    safe = _clean(copy.deepcopy(profile), shareable=mode == "shareable")
    safe.pop("id", None)
    return {"format": FORMAT, "version": VERSION, "mode": mode, "profile": safe}


@dataclass(frozen=True)
class ImportPreview:
    profile: dict[str, Any]
    removed_keys: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def preview_profile_import(payload: dict[str, Any]) -> ImportPreview:
    if not isinstance(payload, dict) or payload.get("format") != FORMAT or payload.get("version") != VERSION:
        raise ValueError("unsupported hpc-client-profile schema")
    profile = payload.get("profile")
    if not isinstance(profile, dict) or not str(profile.get("name", "")).strip():
        raise ValueError("imported profile must contain a name")
    clean = _clean(profile, shareable=False)
    removed = tuple(sorted(set(profile) - set(clean)))
    clean["id"] = str(uuid.uuid4())
    clean["name"] = str(clean["name"]).strip()
    return ImportPreview(clean, removed)


def import_profile(payload: dict[str, Any], save: Callable[[dict[str, Any]], Any]) -> ImportPreview:
    preview = preview_profile_import(payload)
    save(dict(preview.profile))
    return preview
