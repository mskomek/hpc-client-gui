"""Process-session conflict choices shared by the Qt and wx file surfaces."""

from __future__ import annotations

from threading import RLock

_LOCK = RLock()
_SESSION_ACTION: tuple[str, bool] | None = None


def resolve_conflict_action(
    action: str,
    *,
    source_size: int | None = None,
    target_size: int | None = None,
    source_mtime: int | None = None,
    target_mtime: int | None = None,
) -> str:
    """Resolve conditional overwrite choices using only known metadata."""
    try:
        size_differs = (
            source_size is not None
            and target_size is not None
            and int(source_size) != int(target_size)
        )
    except (TypeError, ValueError):
        size_differs = False
    try:
        source_time = int(source_mtime) if source_mtime is not None else 0
        target_time = int(target_mtime) if target_mtime is not None else 0
        source_newer = source_time > 0 and target_time > 0 and source_time > target_time
    except (TypeError, ValueError):
        source_newer = False

    if action == "overwrite_if_newer":
        return "overwrite" if source_newer else "skip"
    if action == "overwrite_if_size_differs":
        return "overwrite" if size_differs else "skip"
    if action == "overwrite_if_size_differs_or_newer":
        return "overwrite" if size_differs or source_newer else "skip"
    if action in {"overwrite", "resume", "skip", "rename", "cancel"}:
        return action
    return "cancel"


def set_session_conflict_action(action: str, *, downloads_only: bool = False) -> None:
    """Use ``action`` for later conflicts until the application exits."""
    global _SESSION_ACTION
    with _LOCK:
        _SESSION_ACTION = (str(action), bool(downloads_only))


def get_session_conflict_action(direction: str) -> str | None:
    """Return the session choice when it applies to this transfer direction."""
    with _LOCK:
        preference = _SESSION_ACTION
    if preference is None:
        return None
    action, downloads_only = preference
    if downloads_only and direction != "download":
        return None
    return action


def clear_session_conflict_action() -> None:
    """Forget the current application's conflict choice."""
    global _SESSION_ACTION
    with _LOCK:
        _SESSION_ACTION = None


__all__ = [
    "clear_session_conflict_action",
    "get_session_conflict_action",
    "resolve_conflict_action",
    "set_session_conflict_action",
]
