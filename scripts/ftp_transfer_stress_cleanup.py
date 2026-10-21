"""Retry-safe cleanup for the disposable FTP stress fixture."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


def remove_temp_root(temp_root: Path) -> None:
    """Remove this run's known temp root, retrying transient Windows handles."""
    last_error: OSError | None = None
    for _attempt in range(20):
        try:
            shutil.rmtree(temp_root)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"temporary cleanup failed for {temp_root}: {last_error}")
