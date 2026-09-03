"""Framework-neutral transfer-session state around the transfer engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hpc_gui.services.transfer_controller import TransferCancelled, TransferController, TransferItem


@dataclass(frozen=True)
class TransferStatus:
    queued: int
    failed: int
    completed: int


class TransferSessionController:
    def __init__(self, items: Iterable[TransferItem], run_item, *, conflict_check=None, conflict_resolver=None, **kwargs) -> None:
        self._run_item_backend = run_item
        self._conflict_check = conflict_check
        self._conflict_resolver = conflict_resolver
        self.engine = TransferController(items, self._run_item, **kwargs)
        self.conflict_policy = "ask"
        self.checksum_enabled = False

    def _run_item(self, item: TransferItem, progress) -> None:
        if self._conflict_check and self._conflict_check(item.dst):
            decision = self.conflict_policy
            if decision in {"ask", "rename"}:
                if not self._conflict_resolver:
                    raise RuntimeError("transfer conflict requires a decision")
                decision = self._conflict_resolver(item)
            if isinstance(decision, tuple) and decision and decision[0] == "rename":
                item.dst = str(decision[1])
                decision = "overwrite"
            if decision == "skip":
                progress(1, 1)
                return
            if decision == "cancel":
                raise TransferCancelled()
            if decision not in {"overwrite", "resume"}:
                raise ValueError(f"unsupported conflict decision: {decision}")
        self._run_item_backend(item, progress)

    def status(self) -> TransferStatus:
        return TransferStatus(len(self.engine.pending), len(self.engine.failed), len(self.engine.completed))

    def set_conflict_policy(self, policy: str) -> None:
        if policy not in {"ask", "overwrite", "skip", "rename", "resume"}:
            raise ValueError(f"unsupported conflict policy: {policy}")
        self.conflict_policy = policy

    def set_checksum_enabled(self, enabled: bool) -> None:
        self.checksum_enabled = bool(enabled)

    def start(self) -> None:
        self.engine.start()

    def cancel(self) -> None:
        self.engine.cancel_all()


__all__ = ["TransferSessionController", "TransferStatus"]
