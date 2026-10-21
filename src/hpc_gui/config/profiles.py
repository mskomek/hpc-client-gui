"""Stable public profile operations for application services."""

from __future__ import annotations

from typing import Any

from hpc_gui.config._storage_profiles import get_profile_id as _get_profile_id
from hpc_gui.config._storage_profiles import load_profiles as _load_profiles


def get_profile_id(name: str) -> str | None:
    """Return the stable ID for a saved profile name."""
    return _get_profile_id(name)


def load_profiles() -> list[dict[str, Any]]:
    """Load saved profiles using the config storage migration rules."""
    return _load_profiles()
