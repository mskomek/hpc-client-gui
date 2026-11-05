"""Local path-component checks for untrusted OpenFOAM case inputs."""

from __future__ import annotations

import os
from pathlib import Path


def require_local_path_without_links(path: str | Path) -> Path:
    """Return an absolute path after rejecting symlink/junction components."""
    target = Path(os.path.abspath(Path(path).expanduser()))
    cursor = target
    while cursor.parent != cursor:
        try:
            is_junction = getattr(cursor, "is_junction", None)
            if cursor.is_symlink() or (callable(is_junction) and is_junction()):
                raise ValueError(f"path traverses a symbolic link or junction: {cursor}")
        except OSError as exc:
            raise ValueError(f"path component could not be inspected: {cursor}") from exc
        cursor = cursor.parent
    return target
