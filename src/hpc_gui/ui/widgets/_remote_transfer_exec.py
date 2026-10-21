"""Remote transfer-execution leaf for the file-manager remote panel.

Owns ``RemoteTransferExecMixin``: the ``_FileOpWorker`` single-batch worker,
the plan runner (``_run_plan_with_progress`` with ``TransferDialog`` wiring,
transfer-key dedup, and transfer-activity callbacks), item execution with
integrity verification, and the lifecycle-critical ``shutdown()``. Planning
(workers, conflict bridge, confirmation gate) lives in ``_remote_transfer_plan``;
directional plan builders live in the download/upload/copy-move leaves; progress
UI, audit journal, and diagnostic persistence live in
``_remote_transfer_progress``; all are reached via ``self``.

Lifecycle ordering preserved verbatim: cancel active worker → quit/wait(1500)
active thread → mark planning jobs cancelled → rescue-close a blocking SFTP
channel → quit/wait(1500) planning threads (keeping still-running QThreads
referenced so PySide6 never destroys a running thread) → persist the remaining
plan as a diagnostic artifact → unregister the weakref instance and clear
local state.

Imports Qt and lower-level core/config/dialogs/services only — never the local
panel, FTP widget, controllers, or another branch's private implementation.
Shared plan vocabulary (``_PlannedOp``) is imported from the sibling
``_remote_mutations`` module: same remote-panel branch, one-directional edge,
no cycle.
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Tuple

from PySide6.QtCore import QObject, QThread, Signal, Slot

from hpc_gui.config.storage import (
    coerce_profile_transfer_parallelism,
    get_transfer_checksum_verification_enabled,
)
from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_integrity import VerificationState, verify_transfer
from hpc_gui.services.transfer_mode import download_with_mode, upload_with_mode
from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog, TransferItem
from hpc_gui.ui.widgets._remote_mutations import _PlannedOp
from hpc_gui.ui.widgets._remote_transfer_plan import _TransferPlanWorker


class _FileOpWorker(QObject):
    progress = Signal(int, str)  # step, label
    finished = Signal(bool, str)  # cancelled, message

    def __init__(self, files_backend, plan: List[_PlannedOp]):
        super().__init__()
        self._files = files_backend
        self._plan = plan
        self._cancel = False

    @Slot()
    def cancel(self) -> None:
        self._cancel = True

    @Slot()
    def run(self) -> None:
        total = len(self._plan)
        for i, op in enumerate(self._plan, start=1):
            if self._cancel:
                self.finished.emit(True, t("dirs.cancelled"))
                return
            label = f"{i}/{total}: {os.path.basename((op.dst or op.src).rstrip('/'))}"
            self.progress.emit(i, label)
            try:
                if op.op == "delete":
                    # delete remote path (dst)
                    self._files.remove(op.dst, recursive=op.recursive)
                elif op.op == "copy":
                    self._files.copy(op.src, op.dst, recursive=op.recursive)
                elif op.op == "move":
                    self._files.move(op.src, op.dst)
                elif op.op == "upload":
                    # upload local (src) -> remote (dst)
                    self._files.upload(op.src, op.dst)
                elif op.op == "download":
                    # download remote (src) -> local (dst)
                    self._files.download_toggle(op.src, op.dst) if hasattr(self._files, 'download_toggle') else self._files.download(op.src, op.dst)
                elif op.op == "mkdir_remote":
                    self._files.mkdir(op.dst)
                elif op.op == "mkdir_local":
                    os.makedirs(op.dst, exist_ok=True)
                elif op.op == "delete_local":
                    # delete local path (dst)
                    if os.path.isdir(op.dst):
                        shutil.rmtree(op.dst, ignore_errors=True)
                    else:
                        try:
                            os.remove(op.dst)
                        except FileNotFoundError:
                            pass
                else:
                    raise RuntimeError(f"Unknown op: {op.op}")
            except Exception as e:
                self.finished.emit(False, f"{label}\n{e}")
                return
        self.finished.emit(False, "")


class RemoteTransferExecMixin:
    """Transfer execution + shutdown ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    _transfer_dialogs: list
    _active_transfer_keys: set
    _active_thread: object
    _active_worker: object
    _active_plan: List[_PlannedOp]
    _active_step: int
    _active_title: str
    _show_transfer_dialog: bool
    _transfer_activity_callback: object
    _local_upload_plan_jobs: dict
    _planning_jobs: Dict[int, Tuple[QThread, object]]
    _local_target_refresh_callback: object

    def _run_plan_with_progress(
        self,
        plan: List[_PlannedOp],
        title: str,
        after_finished=None,
        *,
        confirm_before_start: bool = False,
    ) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        if not plan:
            return True
        active_keys: set[tuple[str, str, str]] = set()
        filtered_plan: List[_PlannedOp] = []
        for op in plan:
            key = self._transfer_key(op)  # type: ignore[attr-defined]
            if key is not None:
                if key in self._active_transfer_keys or key in active_keys:
                    continue
                active_keys.add(key)
            filtered_plan.append(op)
        if not filtered_plan:
            return True
        plan = filtered_plan
        transfer_items = self._transfer_items_from_plan(plan)  # type: ignore[attr-defined]
        files = self.session["files"]
        # The per-profile value is the single authority. A legacy profile
        # without the field safely defaults to 1; the stored *global*
        # "transfer_parallelism" settings key is never used here.
        configured_parallel_limit = coerce_profile_transfer_parallelism(
            getattr(self.session.get("cfg"), "transfer_parallelism", None),
            1,
        )
        backend_parallel_limit = (
            configured_parallel_limit
            if bool(getattr(files, "supports_parallel_transfers", False))
            else 1
        )
        effective_parallel_limit = min(
            configured_parallel_limit,
            backend_parallel_limit,
        )
        if confirm_before_start and not self._confirm_transfer_plan(  # type: ignore[attr-defined]
            transfer_items,
            title,
            effective_parallel_limit,
        ):
            return False

        for dlg in list(self._transfer_dialogs):
            if not dlg.is_active():
                continue
            if dlg.enqueue(transfer_items):
                dlg._truba_active_keys.update(active_keys)
                dlg._truba_plans.append(plan)
                dlg._truba_after_finished.append(after_finished)
                self._active_transfer_keys.update(active_keys)
                if self._transfer_activity_callback is not None:
                    self._transfer_activity_callback("queued", transfer_items, title)  # type: ignore[operator]
                return True

        self._active_transfer_keys.update(active_keys)
        if self._transfer_activity_callback is not None:
            self._transfer_activity_callback("queued", transfer_items, title)  # type: ignore[operator]
        dlg = TransferDialog(
            self,  # type: ignore[arg-type]
            title=title,
            items=transfer_items,
            run_item=self._execute_transfer_item,
            parallel_limit=effective_parallel_limit,
            max_parallel_limit=backend_parallel_limit,
            configured_limit=configured_parallel_limit,
            backend_context_factory=self._transfer_backend_context,
        )
        if self._transfer_activity_callback is not None:
            self._transfer_activity_callback("controller", [dlg], title)  # type: ignore[operator]
        self._active_plan = list(plan)
        self._active_step = 0
        self._active_title = title
        dlg._truba_active_keys = active_keys
        dlg._truba_plans = [plan]
        dlg._truba_after_finished = [after_finished]
        def handle_finished(_result: int) -> None:
            try:
                if self._transfer_activity_callback is not None:
                    event = "completed" if dlg.finished_cleanly() else "failed"
                    event_items = (
                        list(dlg._completed)
                        if event == "completed"
                        else [item for item, _error in dlg._errors]
                    )
                    self._transfer_activity_callback(event, event_items, title)  # type: ignore[operator]
                if dlg.finished_cleanly():
                    for callback in dlg._truba_after_finished:
                        if callback is not None:
                            callback()
                    for queued_plan in dlg._truba_plans:
                        self._refresh_local_transfer_targets(queued_plan)
            finally:
                self._active_transfer_keys.difference_update(dlg._truba_active_keys)
                try:
                    self._transfer_dialogs.remove(dlg)
                except ValueError:
                    pass
                dlg.deleteLater()

        def release_reserved_keys() -> None:
            # The queue is done; stop treating these transfers as in flight.
            # Waiting for `finished` used to hold them forever after a cancel,
            # because a cancelled dialog stays open and never emits it - so
            # re-downloading the same files planned them and then filtered
            # every one of them out again as a duplicate.
            self._active_transfer_keys.difference_update(dlg._truba_active_keys)

        dlg.queueFinished.connect(release_reserved_keys)
        dlg.finished.connect(handle_finished)
        self._transfer_dialogs.append(dlg)
        dlg.start()
        if self._show_transfer_dialog:
            dlg.show()
        self._active_plan = []
        self._active_step = 0
        self._active_title = ""
        return True

    def _refresh_local_transfer_targets(self, plan: List[_PlannedOp]) -> None:
        """Refresh local folders affected by a completed transfer plan."""
        callback = self._local_target_refresh_callback
        if callback is None:
            return
        target_dirs = {
            os.path.dirname(os.path.abspath(op.dst))
            for op in plan
            if op.op in {"download", "mkdir_local", "delete_local"} and op.dst
        }
        for target_dir in sorted(target_dirs):
            try:
                callback(target_dir)  # type: ignore[operator]
            except Exception:
                # Refreshing a view must never turn a successful transfer into
                # a failed one.
                pass

    def _transfer_backend_context(self):
        """Return an isolated files backend for one parallel transfer worker.

        Only backends that declare ``supports_parallel_transfers`` and expose
        ``open_transfer_backend`` qualify; the transfer queue closes whatever
        this returns after each item (success, failure, or cancellation).
        """
        files = self.session.get("files") if self.session else None
        if files is None or not bool(getattr(files, "supports_parallel_transfers", False)):
            return None
        opener = getattr(files, "open_transfer_backend", None)
        return opener() if callable(opener) else None

    def _execute_transfer_item(self, item: TransferItem, progress_cb=None, *, files=None) -> None:
        if not self.session or not self.session.get("files"):
            raise RuntimeError(t("common.no_connection"))
        files = files or self.session["files"]
        op = item.op
        if op == "delete":
            recursive = item.recursive
            if recursive is None:
                try:
                    recursive = bool(files.is_dir(item.dst))
                except Exception:
                    try:
                        files.listdir(item.dst)
                        recursive = True
                    except Exception:
                        recursive = False
            files.remove(item.dst, recursive=bool(recursive))
        elif op == "copy":
            files.copy(item.src, item.dst, recursive=item.recursive)
        elif op == "move":
            files.move(item.src, item.dst)
        elif op == "upload":
            upload_with_mode(
                files,
                item.src,
                item.dst,
                self._requested_transfer_mode(item.src),  # type: ignore[attr-defined]
                progress_cb=progress_cb,
            )
            self._verify_transfer_item(item, files=files)
        elif op == "download":
            download_with_mode(
                files,
                item.src,
                item.dst,
                self._requested_transfer_mode(item.src),  # type: ignore[attr-defined]
                progress_cb=progress_cb,
            )
            self._verify_transfer_item(item, files=files)
        elif op == "mkdir_remote":
            files.mkdir(item.dst)
        elif op == "mkdir_local":
            os.makedirs(item.dst, exist_ok=True)
        elif op == "delete_local":
            if os.path.isdir(item.dst):
                shutil.rmtree(item.dst, ignore_errors=True)
            else:
                try:
                    os.remove(item.dst)
                except FileNotFoundError:
                    pass
        else:
            raise RuntimeError(f"Unknown op: {op}")

    def _verify_transfer_item(self, item: TransferItem, *, files=None) -> None:
        if not get_transfer_checksum_verification_enabled():
            return
        files = files or self.session["files"]
        remote_hash = getattr(files, "sha256", None)
        if not callable(remote_hash):
            self._last_verification = VerificationState.UNSUPPORTED  # type: ignore[attr-defined]
            return
        local_path = item.src if item.op == "upload" else item.dst
        remote_path = item.dst if item.op == "upload" else item.src
        self._last_verification = VerificationState.VERIFYING  # type: ignore[attr-defined]
        try:
            remote_digest = remote_hash(remote_path)
        except Exception:
            self._last_verification = VerificationState.UNSUPPORTED  # type: ignore[attr-defined]
            return
        result = verify_transfer(local_path, remote_digest)
        self._last_verification = result.state  # type: ignore[attr-defined]
        if result.state is VerificationState.FAILED:
            raise RuntimeError(
                f"SHA-256 verification failed for {remote_path}: "
                f"local={result.local_digest}, remote={result.remote_digest}"
            )

    def shutdown(self) -> None:
        """Cancel any in-flight batch operation (best-effort).

        This does not add new UX; it only prevents orphan threads and
        persists remaining steps as a diagnostic artifact.
        """
        still_running: Dict[int, Tuple[QThread, _TransferPlanWorker]] = {}
        try:
            if self._active_worker is not None:
                try:
                    self._active_worker.cancel()
                except Exception:
                    pass
            if self._active_thread is not None:
                try:
                    self._active_thread.quit()
                except Exception:
                    pass
                try:
                    self._active_thread.wait(1500)
                except Exception:
                    pass
            planning_jobs = list(self._planning_jobs.items())
            for _job_id, (_thread, worker) in planning_jobs:
                worker.cancelled = True
            # Interrupt a planner blocked in the shared browsing SFTP channel
            # before the SSH transport is closed by MainWindow shutdown.
            try:
                files = (self.session or {}).get("files")
                ssh = getattr(files, "ssh", None)
                sftp = getattr(ssh, "sftp", None)
                if sftp is not None:
                    sftp.close()
            except Exception:
                pass
            for job_id, (thread, worker) in planning_jobs:
                try:
                    thread.quit()
                    thread.wait(1500)
                except Exception:
                    pass
                # A worker can still be alive here (e.g. blocked on a
                # synchronous SFTP call, or on a BlockingQueuedConnection
                # back to this now-shutting-down GUI thread). Never drop the
                # last Python reference to a QThread whose OS thread is still
                # running: PySide6 destroying it in that state is a fatal
                # native crash ("QThread: Destroyed while thread is still
                # running"). Keep it referenced; the `thread.finished` signal
                # already wired at creation calls `_planning_job_finished`,
                # which pops and `deleteLater()`s it once it actually stops.
                if thread.isRunning():
                    still_running[job_id] = (thread, worker)
            # Persist remaining plan if any.
            try:
                if self._active_plan:
                    remaining = self._active_plan[max(0, self._active_step - 1):]
                    if remaining:
                        self._persist_batch_state(remaining, title=self._active_title or "shutdown")
            except Exception:
                pass
        finally:
            self._unregister_instance()
            self._local_upload_plan_jobs.clear()
            self._planning_jobs = still_running
            self._active_thread = None
            self._active_worker = None
            self._active_plan = []
            self._active_step = 0
            self._active_title = ""

__all__ = [
    "RemoteTransferExecMixin",
    "_FileOpWorker",
]
