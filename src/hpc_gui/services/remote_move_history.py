"""Small, thread-safe history for remote move undo."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RemoteMoveRecord:
    moves: tuple[tuple[str, str], ...]


class RemoteMoveHistory:
    def __init__(self) -> None:
        self._records: list[RemoteMoveRecord] = []
        self._lock = Lock()

    def record(self, moves: tuple[tuple[str, str], ...]) -> None:
        if moves:
            with self._lock:
                self._records.append(RemoteMoveRecord(tuple(moves)))

    def pop_last(self) -> RemoteMoveRecord | None:
        with self._lock:
            return self._records.pop() if self._records else None

    def push(self, record: RemoteMoveRecord) -> None:
        with self._lock:
            self._records.append(record)


__all__ = ["RemoteMoveHistory", "RemoteMoveRecord"]
