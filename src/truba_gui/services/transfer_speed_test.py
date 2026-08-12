from __future__ import annotations

import hashlib
import os
import posixpath
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


def run_transfer_speed_test(
    files: Any,
    *,
    remote_dir: str,
    size_mib: int = 8,
) -> dict[str, Any]:
    """Run a bounded upload/download round trip and remove its remote file."""
    size = max(1, min(int(size_mib), 256)) * 1024 * 1024
    remote_path = posixpath.join(
        remote_dir.rstrip("/") or "/",
        f".truba-speedtest-{uuid.uuid4().hex}.bin",
    )
    source: Path | None = None
    target: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="truba-speedtest-", suffix=".bin", delete=False) as handle:
            source = Path(handle.name)
            handle.write(os.urandom(size))
        target = source.with_name(source.stem + "-downloaded.bin")
        started = time.perf_counter()
        files.upload(str(source), remote_path)
        upload_seconds = max(time.perf_counter() - started, 1e-9)
        started = time.perf_counter()
        files.download(remote_path, str(target))
        download_seconds = max(time.perf_counter() - started, 1e-9)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise ValueError("speed-test download checksum mismatch")
        mib = size / (1024 * 1024)
        return {
            "size_mib": mib,
            "upload_seconds": upload_seconds,
            "download_seconds": download_seconds,
            "upload_mib_s": mib / upload_seconds,
            "download_mib_s": mib / download_seconds,
            "remote_path": remote_path,
        }
    finally:
        try:
            files.remove(remote_path)
        except Exception:
            pass
        for path in (source, target):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
