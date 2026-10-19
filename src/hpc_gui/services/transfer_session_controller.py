"""Framework-neutral transfer-session state around the transfer engine."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from threading import Lock
from typing import Iterable

from hpc_gui.services.transfer_controller import TransferCancelled, TransferController, TransferItem
from hpc_gui.services.transfer_conflict_policy import (
    get_session_conflict_action,
    set_session_conflict_action,
)


@dataclass(frozen=True)
class TransferStatus:
    queued: int
    failed: int
    completed: int


class TransferSessionController:
    """Framework-neutral transfer-session state around the transfer engine.

    ``verify`` is an optional post-transfer integrity hook
    (``HPC-W06-TODO-043``): ``verify(item)`` runs after the backend reports
    success and only when ``checksum_enabled`` is true.  It must raise on a
    digest mismatch (the engine then records ``FAILED`` instead of success)
    and return normally for ``VERIFIED``/``UNSUPPORTED`` outcomes.  The
    default ``None`` preserves the historical run-without-verify behavior.
    """

    def __init__(
        self,
        items: Iterable[TransferItem],
        run_item,
        *,
        conflict_check=None,
        conflict_resolver=None,
        conflict_evaluator=None,
        verify=None,
        **kwargs,
    ) -> None:
        self._run_item_backend = run_item
        self._conflict_check = conflict_check
        self._conflict_resolver = conflict_resolver
        self._conflict_evaluator = conflict_evaluator
        self._verify = verify
        parameters = inspect.signature(run_item).parameters
        self._run_item_accepts_decision = "conflict_decision" in parameters or any(
            parameter.kind is parameter.VAR_KEYWORD for parameter in parameters.values()
        )
        self.engine = TransferController(items, self._run_item, **kwargs)
        self.conflict_policy = "ask"
        self._queue_conflict_policy: tuple[str, bool] | None = None
        self._conflict_resolution_lock = Lock()
        self.checksum_enabled = False

    def _run_item(self, item: TransferItem, progress) -> None:
        decision = None
        if self._conflict_check:
            with self._conflict_resolution_lock:
                if self._conflict_check(item):
                    direction = item.op if item.op in {"upload", "download"} else "other"
                    decision = get_session_conflict_action(direction)
                    if decision is None:
                        if self._queue_conflict_policy is not None:
                            queue_action, downloads_only = self._queue_conflict_policy
                            if not downloads_only or direction == "download":
                                decision = queue_action
                        if decision is None:
                            decision = self.conflict_policy
                    if decision in {"ask", "rename"}:
                        if not self._conflict_resolver:
                            raise RuntimeError("transfer conflict requires a decision")
                        resolved = self._conflict_resolver(item)
                        apply_all = False
                        always_use = False
                        downloads_only = False
                        if isinstance(resolved, dict) and "value" in resolved:
                            apply_all = bool(resolved.get("apply_all"))
                            always_use = bool(resolved.get("always_use"))
                            downloads_only = bool(resolved.get("downloads_only"))
                            resolved = resolved["value"]
                        decision = resolved
                        action = (
                            decision[0]
                            if isinstance(decision, tuple) and decision
                            else decision
                        )
                        if action in {
                            "overwrite",
                            "overwrite_if_newer",
                            "overwrite_if_size_differs",
                            "overwrite_if_size_differs_or_newer",
                            "skip",
                            "rename",
                            "resume",
                        }:
                            if always_use:
                                set_session_conflict_action(
                                    action, downloads_only=downloads_only
                                )
                            if apply_all:
                                self._queue_conflict_policy = (action, downloads_only)
                    if decision in {
                        "overwrite_if_newer",
                        "overwrite_if_size_differs",
                        "overwrite_if_size_differs_or_newer",
                    }:
                        if self._conflict_evaluator is None:
                            decision = "skip"
                        else:
                            decision = self._conflict_evaluator(item, decision)
            if decision is not None:
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
        if self._run_item_accepts_decision:
            self._run_item_backend(item, progress, conflict_decision=decision)
        else:
            self._run_item_backend(item, progress)
        if self.checksum_enabled and self._verify is not None and item.op in {"upload", "download"}:
            self._verify(item)

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
