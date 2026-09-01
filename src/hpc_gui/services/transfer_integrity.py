"""Streaming SHA-256 verification primitives for file transfers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable


class VerificationState(str, Enum):
    OFF = "off"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class VerificationResult:
    state: VerificationState
    local_digest: str = ""
    remote_digest: str = ""
    message: str = ""


class VerificationCancelled(Exception):
    pass


def sha256_file(path: str | Path, *, cancel: Callable[[], bool] | None = None, progress: Callable[[int, int], None] | None = None) -> str:
    source = Path(path)
    total = source.stat().st_size
    done = 0
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if cancel is not None and cancel():
                raise VerificationCancelled()
            digest.update(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
    return digest.hexdigest()


def verify_transfer(local_path: str | Path, remote_digest: str | None, *, cancel=None, progress=None) -> VerificationResult:
    if not remote_digest:
        return VerificationResult(VerificationState.UNSUPPORTED, message="remote SHA-256 is unavailable")
    local_digest = sha256_file(local_path, cancel=cancel, progress=progress)
    remote_digest = str(remote_digest).strip().lower()
    if local_digest != remote_digest:
        return VerificationResult(VerificationState.FAILED, local_digest, remote_digest, "SHA-256 mismatch")
    return VerificationResult(VerificationState.VERIFIED, local_digest, remote_digest, "SHA-256 verified")
