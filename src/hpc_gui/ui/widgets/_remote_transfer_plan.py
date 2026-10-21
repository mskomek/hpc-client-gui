"""Remote transfer-planning leaf for the file-manager remote panel.

Owns ``RemoteTransferPlanMixin``: the ``_TransferPlanWorker`` / QThread
planning channel (worker ``run()`` executes the planner off the GUI thread;
conflict/rename bridges re-enter the GUI thread via ``BlockingQueuedConnection``
``invokeMethod``), planning-job lifecycle, the conflict/rename dialog bridge,
the plan-confirmation (upload preflight) gate, plan→item conversion, and the
transfer dedup key. Execution (runner, queue, shutdown) lives in
``_remote_transfer_exec``; directional flows live in the download/upload/
copy-move leaves; all are reached via ``self``. Class-level conflict state
(``_session_conflict_action``) is reached via ``type(self)``, which is exactly
``RemoteDirPanel`` for the single concrete panel class — no leaf→facade import.

Imports Qt and lower-level core/config/dialogs/services only — never the local
panel, FTP widget, controllers, or another branch's private implementation.
Shared plan vocabulary (``_PlannedOp``) is imported from the sibling
``_remote_mutations`` module: same remote-panel branch, one-directional edge
(the mutations leaf imports nothing from any transfer leaf), no cycle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional, Tuple

from shiboken6 import isValid

from PySide6.QtCore import (
    Q_ARG,
    QMetaObject,
    QObject,
    QThread,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QDialog, QInputDialog, QWidget

from hpc_gui.config.storage import (
    get_upload_preflight_confirmation_enabled,
    set_upload_preflight_confirmation_enabled,
)
from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.ui.dialogs.transfer_conflict_dialog import (
    TransferConflictDecision,
    TransferConflictDialog,
    TransferConflictInfo,
)
from hpc_gui.ui.dialogs.transfer_dialog import TransferItem, TransferPreflightDialog
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp
from hpc_gui.services.transfer_conflict_policy import (
    clear_session_conflict_action,
    get_session_conflict_action,
    resolve_conflict_action,
    set_session_conflict_action,
)


@dataclass
class _LocalUploadPlanJob:
    steps: Generator[None, None, Optional[List[_PlannedOp]]]
    dest_dir: str


class _TransferPlanWorker(QObject):
    finished = Signal(int, str, object)
    failed = Signal(int, str, object)

    def __init__(self, job_id: int, kind: str, planner, panel: QWidget) -> None:
        super().__init__()
        self.job_id = job_id
        self.kind = kind
        self._planner = planner
        self._panel = panel
        self.cancelled = False
        self._pending_source = None
        self._pending_target = None
        self._pending_partial = False
        self._pending_direction = "download"
        self._pending_decision = "cancel"
        self._pending_rename_dir = ""
        self._pending_rename_name = ""
        self._pending_rename_result = None

    @Slot()
    def run(self) -> None:
        try:
            result = self._planner(self)
        except Exception as exc:
            self.failed.emit(self.job_id, self.kind, exc)
            return
        self.finished.emit(self.job_id, self.kind, result)

    def request_conflict_decision(
        self, source, target, *, partial: bool = False, direction: str = "download"
    ) -> str:
        """Show the conflict dialog on the GUI thread and return the raw action.

        Called from the worker thread while planning. Blocks until the GUI
        thread has shown the decision dialog and normalized the result, so all
        remote stat probes stay off the GUI event loop.
        """
        self._pending_source = source
        self._pending_target = target
        self._pending_partial = bool(partial)
        self._pending_direction = direction
        self._pending_decision = "cancel"
        QMetaObject.invokeMethod(
            self._panel,
            "_resolve_conflict_from_worker",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG("int", self.job_id),
        )
        return self._pending_decision

    def request_rename(self, dst_dir: str, current_name: str) -> Optional[str]:
        """Prompt for a new target name on the GUI thread and return it."""
        self._pending_rename_dir = dst_dir
        self._pending_rename_name = current_name
        self._pending_rename_result = None
        QMetaObject.invokeMethod(
            self._panel,
            "_prompt_rename_from_worker",
            Qt.ConnectionType.BlockingQueuedConnection,
            Q_ARG("int", self.job_id),
        )
        return self._pending_rename_result


class RemoteTransferPlanMixin:
    """Transfer planning + conflict-bridge ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    _planning_jobs: Dict[int, Tuple[QThread, _TransferPlanWorker]]
    _next_planning_job_id: int

    def _resolve_conflict(
        self,
        dst: str,
        *,
        src: str = "",
        source_is_local: bool | None = None,
        target_is_local: bool | None = None,
    ):
        """Return one of: overwrite|resume|skip|rename|cancel (optionally applied to all)."""
        source = self._conflict_info(src or dst, is_local=source_is_local)
        target = self._conflict_info(dst, is_local=target_is_local)
        if source_is_local is True:
            direction = "upload"
        elif target_is_local is True:
            direction = "download"
        else:
            direction = "other"
        return self._conflict_decision(source, target, direction=direction)

    def reset_conflict_preference(self) -> None:
        """Forget the process-session always-use choice."""
        clear_session_conflict_action()

    def _conflict_decision(
        self,
        source: TransferConflictInfo,
        target: TransferConflictInfo,
        *,
        partial: bool = False,
        direction: str = "upload",
    ) -> str:
        """Turn already-known conflict info into a decision.

        Applies the process-wide "always use" action when one is set, otherwise
        shows the conflict dialog. Must run on the GUI thread because it shows a
        modal dialog. Returns the normalized action string, optionally suffixed
        with "_all".
        """
        session_action = get_session_conflict_action(direction)
        if session_action is not None:
            return self._normalize_conflict_decision(
                TransferConflictDecision(action=session_action), source, target
            )

        decision = TransferConflictDialog.get_decision(
            self,
            source=source,
            target=target,
            partial=partial,
        )
        action = self._normalize_conflict_decision(decision, source, target)
        if decision.always_use:
            # Keep the selected action (rather than its result) so conditional
            # actions are evaluated against each later conflicting file.
            set_session_conflict_action(
                decision.action,
                downloads_only=decision.apply_downloads_only,
            )
        apply_all = bool(
            (decision.always_use or decision.apply_current_queue_only)
            and (not decision.apply_downloads_only or direction == "download")
        )
        return action + "_all" if apply_all else action

    @Slot(int)
    def _resolve_conflict_from_worker(self, job_id: int) -> None:
        """GUI-thread half of the plan worker's conflict bridge.

        Runs inside a blocking call from the planning thread: shows the conflict
        dialog and leaves the normalized decision on the worker object so the
        planner can continue building the plan off the GUI thread.
        """
        current = self._planning_jobs.get(job_id)
        if current is None:
            return
        worker = current[1]
        try:
            worker._pending_decision = self._conflict_decision(
                worker._pending_source,
                worker._pending_target,
                partial=getattr(worker, "_pending_partial", False),
                direction=getattr(worker, "_pending_direction", "download"),
            )
        except Exception:
            worker._pending_decision = "cancel"

    @Slot(int)
    def _prompt_rename_from_worker(self, job_id: int) -> None:
        """GUI-thread half of the plan worker's rename bridge."""
        current = self._planning_jobs.get(job_id)
        if current is None:
            return
        worker = current[1]
        try:
            worker._pending_rename_result = self._prompt_rename(
                worker._pending_rename_dir,
                worker._pending_rename_name,
            )
        except Exception:
            worker._pending_rename_result = None

    def _conflict_info(
        self,
        path: str,
        *,
        is_local: bool | None = None,
    ) -> TransferConflictInfo:
        if is_local is True:
            try:
                st = os.stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(st.st_size),
                    mtime=int(st.st_mtime),
                )
            except Exception:
                return TransferConflictInfo(path=path)
        if is_local is False and self.session and self.session.get("files"):
            try:
                size, mtime = self.session["files"].stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(size),
                    mtime=int(mtime),
                )
            except Exception:
                return TransferConflictInfo(path=path)
        try:
            if os.path.exists(path):
                st = os.stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(st.st_size),
                    mtime=int(st.st_mtime),
                )
        except Exception:
            pass
        if self.session and self.session.get("files"):
            try:
                size, mtime = self.session["files"].stat(path)
                return TransferConflictInfo(
                    path=path,
                    size=int(size),
                    mtime=int(mtime),
                )
            except Exception:
                pass
        return TransferConflictInfo(path=path)

    @staticmethod
    def _normalize_conflict_decision(
        decision: TransferConflictDecision,
        source: TransferConflictInfo,
        target: TransferConflictInfo,
    ) -> str:
        return resolve_conflict_action(
            decision.action,
            source_size=source.size,
            target_size=target.size,
            source_mtime=source.mtime,
            target_mtime=target.mtime,
        )

    def _prompt_rename(self, dst_dir: str, current_name: str) -> str | None:
        new_name, ok = QInputDialog.getText(self, "Yeniden adlandır", "Yeni ad:", text=current_name)  # type: ignore[arg-type]
        if not ok:
            return None
        new_name = (new_name or "").strip()
        if not new_name:
            return None
        return dst_dir.rstrip("/") + "/" + new_name

    @staticmethod
    def _transfer_key(op: _PlannedOp) -> tuple[str, str, str] | None:
        if op.op not in {"upload", "download"}:
            return None
        return (op.op, op.src, op.dst)

    @staticmethod
    def _transfer_items_from_plan(plan: List[_PlannedOp]) -> List[TransferItem]:
        """Convert a plan into transfer items, keeping any already-known size."""
        return [
            TransferItem(
                op=p.op,
                src=p.src,
                dst=p.dst,
                recursive=p.recursive,
                cached_size=p.size,
            )
            for p in plan
        ]

    def _confirm_transfer_plan(
        self,
        transfer_items: List[TransferItem],
        title: str,
        parallel_limit: int,
    ) -> bool:
        if not get_upload_preflight_confirmation_enabled():
            return True
        dialog = TransferPreflightDialog(
            self,  # type: ignore[arg-type]
            title=title,
            items=transfer_items,
            parallel_limit=parallel_limit,
        )
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
            if accepted and dialog.cb_dont_ask_again.isChecked():
                set_upload_preflight_confirmation_enabled(False)
            return accepted
        finally:
            dialog.deleteLater()

    def _start_transfer_planning(self, kind: str, planner) -> bool:
        job_id = self._next_planning_job_id
        self._next_planning_job_id += 1
        thread = QThread()
        worker = _TransferPlanWorker(job_id, kind, planner, panel=self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_transfer_plan_finished)
        worker.failed.connect(self._on_transfer_plan_failed)
        worker.finished.connect(lambda *_args, current=thread: current.quit())
        worker.failed.connect(lambda *_args, current=thread: current.quit())
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(
            lambda current_job_id=job_id: self._planning_job_finished(
                current_job_id
            )
        )
        self._planning_jobs[job_id] = (thread, worker)
        thread.start()
        return True

    @Slot(int, str, object)
    def _on_transfer_plan_finished(
        self,
        job_id: int,
        kind: str,
        result,
    ) -> None:
        if not isValid(self):
            return
        if job_id not in self._planning_jobs or not result:
            return
        if result.get("conflict"):
            # Only upload planning defers conflict resolution to the bounded
            # GUI-thread planner. Remote download planning resolves conflicts
            # on the worker thread and therefore never returns this sentinel.
            self._apply_local_upload_incremental_gui(  # type: ignore[attr-defined]
                result["paths"],
                result["directory"],
            )
            return
        plan = result.get("plan") or []
        if not plan:
            return
        affected_dirs = list(result.get("affected_dirs") or [])
        self._run_plan_with_progress(  # type: ignore[attr-defined]
            plan,
            result["title"],
            after_finished=lambda dirs=affected_dirs: (
                self._finish_remote_directory_mutation(dirs)  # type: ignore[attr-defined]
            ),
            confirm_before_start=bool(result.get("confirm_before_start")),
        )

    @Slot(int, str, object)
    def _on_transfer_plan_failed(
        self,
        job_id: int,
        _kind: str,
        exc,
    ) -> None:
        if not isValid(self):
            return
        if job_id not in self._planning_jobs:
            return
        show_exception(
            self,  # type: ignore[arg-type]
            title=t("common.error"),
            user_message=str(exc),
            exc=exc,
            area="FILES",
        )

    def _planning_job_finished(self, job_id: int) -> None:
        if not isValid(self):
            # The panel's underlying C++ QWidget can already be gone by the
            # time a background planning QThread we deliberately kept alive
            # (see shutdown()) finally emits `finished` during app teardown.
            # Touching `self` past that point corrupts native heap state
            # instead of raising a clean Python error. There is nothing left
            # to clean up on a destroyed panel; let `thread`/`worker` be
            # garbage-collected once the signal-connection reference drops.
            return
        current = self._planning_jobs.pop(job_id, None)
        if current is not None:
            thread, _worker = current
            thread.deleteLater()


__all__ = [
    "RemoteTransferPlanMixin",
    "_LocalUploadPlanJob",
    "_TransferPlanWorker",
]
