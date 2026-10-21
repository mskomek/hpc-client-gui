"""Concurrency and phase result records for the FTP stress harness."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


@dataclass
class PhaseResult:
    name: str
    elapsed_seconds: float
    bytes_transferred: int
    throughput_mib_s: float
    completed_rows: int
    error_rows: list[str]
    pending_rows: list[str]
    max_observed_concurrency: int


class ConcurrencyTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = 0
        self.maximum = 0

    @contextmanager
    def transfer(self) -> Iterator[None]:
        with self._lock:
            self.active += 1
            self.maximum = max(self.maximum, self.active)
        try:
            yield
        finally:
            with self._lock:
                self.active -= 1

