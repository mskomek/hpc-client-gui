"""Framework-neutral transfer-session state around the transfer engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hpc_gui.services.transfer_controller import TransferController, TransferItem


@dataclass(frozen=True)
class TransferStatus:
    queued: int
    failed: int
    completed: int


class TransferSessionController:
    def __init__(self, items: Iterable[TransferItem], run_item, **kwargs) -> None:
        self.engine = TransferController(items, run_item, **kwargs)
        self.conflict_policy = "ask"
        self.checksum_enabled = False

    def status(self) -> TransferStatus:
        return TransferStatus(len(self.engine.pending), len(self.engine.failed), len(self.engine.completed))

    def set_conflict_policy(self, policy: str) -> None:
        if policy not in {"ask", "overwrite", "skip", "rename"}:
            raise ValueError(f"unsupported conflict policy: {policy}")
        self.conflict_policy = policy

    def set_checksum_enabled(self, enabled: bool) -> None:
        self.checksum_enabled = bool(enabled)

    def start(self) -> None:
        self.engine.start()

    def cancel(self) -> None:
        self.engine.cancel_all()


__all__ = ["TransferSessionController", "TransferStatus"]
