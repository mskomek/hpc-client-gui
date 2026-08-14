from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Callable


def download_atomic(
    url: str,
    destination: Path,
    *,
    timeout: float = 60,
    cancelled: Callable[[], bool] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> bool:
    """Download to a sibling .part file and publish only after EOF."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "HPC-Client-GUI/1.0"}, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response, partial.open("wb") as output:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                if cancelled and cancelled():
                    return False
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
            output.flush()
        partial.replace(destination)
        return True
    finally:
        partial.unlink(missing_ok=True)
