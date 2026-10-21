"""Environment helpers for test subprocesses that import the project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def project_python_environment(
    repository_root: str | os.PathLike[str],
    base_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Prepend project sources while retaining runtime paths such as wxPython."""
    environment = dict(os.environ if base_environment is None else base_environment)
    source_path = str((Path(repository_root) / "src").resolve())
    source_identity = os.path.normcase(os.path.abspath(source_path))
    existing_paths = [
        value for value in environment.get("PYTHONPATH", "").split(os.pathsep)
        if value and os.path.normcase(os.path.abspath(value)) != source_identity
    ]
    environment["PYTHONPATH"] = os.pathsep.join([source_path, *existing_paths])
    return environment
