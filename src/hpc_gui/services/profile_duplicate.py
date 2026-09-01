"""Safe local duplication of connection profiles."""

from __future__ import annotations

import copy
import re
import uuid
from collections.abc import Iterable
from typing import Any

from hpc_gui.services.profile_exchange import _clean

_KEY_PATH = re.compile(r"private.?key|key.?path", re.I)


def _without_key_paths(value):
    if isinstance(value, dict):
        return {key: _without_key_paths(item) for key, item in value.items() if not _KEY_PATH.search(str(key))}
    if isinstance(value, list):
        return [_without_key_paths(item) for item in value]
    return value


def duplicate_profile(
    profile: dict[str, Any],
    existing_names: Iterable[str] = (),
    *,
    copy_key_path: bool = False,
    copy_suffix: str = " (copy)",
) -> dict[str, Any]:
    """Return an unpersisted duplicate with fresh identity and no credentials."""
    if not isinstance(profile, dict) or not str(profile.get("name", "")).strip():
        raise ValueError("profile name is required")
    duplicate = _clean(copy.deepcopy(profile), shareable=False)
    if not copy_key_path:
        duplicate = _without_key_paths(duplicate)
    duplicate["id"] = str(uuid.uuid4())
    names = {str(name) for name in existing_names}
    base = str(profile["name"]).strip() + copy_suffix
    name = base
    counter = 2
    while name in names:
        name = f"{base} {counter}"
        counter += 1
    duplicate["name"] = name
    return duplicate
