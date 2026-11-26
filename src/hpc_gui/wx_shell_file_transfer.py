"""wx shell file transfer workflows."""
from __future__ import annotations

from threading import Event
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.services.transfer_controller import TransferCancelled
from hpc_gui.services.transfer_conflict_policy import (
    available_rename_destination, conflict_target, destination_exists, read_conflict_metadata, resolve_conflict_action,
)
import inspect
from hpc_gui.core.i18n import t


def _destination_exists(files, op: str, destination: str) -> bool:
    """Probe the destination namespace, not the source namespace."""
    return destination_exists(files, op, destination)

def _run_file_view_item(files, item, progress, *, conflict_decision=None):
    """Execute one wx file-view transfer item against a files backend.

    ``progress`` is the engine callback: backends that accept
    ``progress_cb`` receive it so mid-transfer progress stays visible and
    engine cancellation can interrupt an in-flight transfer instead of only
    taking effect between queued items.
    """
    if item.op == "upload":
        method = files.resume_upload if conflict_decision == "resume" else files.upload
        try:
            _call_transfer_with_progress(method, item.src, item.dst, progress)
        except TransferCancelled:
            raise
        except Exception as error:
            raise RuntimeError(f"Upload failed ({item.src} -> {item.dst}): {error}") from error
    elif item.op == "download":
        method = files.resume_download if conflict_decision == "resume" else files.download
        try:
            _call_transfer_with_progress(method, item.src, item.dst, progress)
        except TransferCancelled:
            raise
        except Exception as error:
            raise RuntimeError(f"Download failed ({item.src} -> {item.dst}): {error}") from error
    elif item.op == "mkdir_remote":
        try:
            files.mkdir(item.dst)
        except Exception as error:
            raise RuntimeError(f"Remote directory creation failed ({item.dst}): {error}") from error
    else:
        raise RuntimeError(f"unsupported transfer item: {item.op}")
    progress(1, 1)


def _call_transfer_with_progress(method, src, dst, progress) -> None:
    """Invoke a backend transfer method, forwarding engine progress.

    Backends accepting ``progress_cb`` (SSHFilesBackend upload/download and
    resume variants) receive the engine callback so per-chunk progress stays
    visible and ``cancel_all`` raises ``TransferCancelled`` inside the chunk
    loop instead of only taking effect between queued items. Legacy backends
    without that parameter keep the old positional call.
    """
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        signature = None
    if signature is not None and "progress_cb" in signature.parameters:
        method(src, dst, progress_cb=progress)
    else:
        method(src, dst)


def _cancel_transfer_sessions(session_state) -> int:
    """Cancel every in-flight file-transfer session (HPC-W06-XFER-013).

    A disconnect must invalidate remote transfers predictably instead of
    leaving them blocked on a dead transport until a socket timeout.  Returns
    the number of sessions cancelled.  Never raises.
    """
    cancelled = 0
    try:
        sessions = list((session_state or {}).get("transfer_sessions") or ())
    except Exception:
        return 0
    for session in sessions:
        try:
            cancel = getattr(session, "cancel", None)
            if callable(cancel):
                cancel()
                cancelled += 1
            else:
                engine = getattr(session, "engine", None)
                fallback = getattr(engine, "cancel_all", None) if engine is not None else None
                if callable(fallback):
                    fallback()
                    cancelled += 1
        except Exception:
            continue
    return cancelled


def _verify_transfer_item(files, item):
    """Opt-in post-transfer SHA-256 verification (HPC-W06-TODO-043).

    Mirrors the Qt ``remote_dir_panel._verify_transfer_item`` semantics for
    the wx file-view path: disabled unless the stored
    ``transfer_checksum_verification_enabled`` setting is true; backends
    without a ``sha256`` probe (or a failing probe) yield an ``UNSUPPORTED``
    passthrough; a digest mismatch raises so the engine records ``FAILED``
    instead of success.  Returns the :class:`VerificationState`.
    """
    from hpc_gui.services.transfer_integrity import VerificationState

    try:
        from hpc_gui.config.storage import get_transfer_checksum_verification_enabled
        enabled = bool(get_transfer_checksum_verification_enabled())
    except Exception:
        enabled = False
    if not enabled:
        return VerificationState.OFF
    local_path = item.src if item.op == "upload" else item.dst
    remote_path = item.dst if item.op == "upload" else item.src
    return _verify_transfer_bytes(files, local_path, remote_path)


def _verify_transfer_bytes(files, local_path, remote_path):
    """Compare transferred bytes, before ASCII conversion discards raw data."""
    from hpc_gui.services.transfer_integrity import VerificationState, verify_transfer

    remote_hash = getattr(files, "sha256", None)
    if not callable(remote_hash):
        return VerificationState.UNSUPPORTED
    try:
        remote_digest = remote_hash(remote_path)
    except Exception:
        return VerificationState.UNSUPPORTED
    result = verify_transfer(local_path, remote_digest)
    if result.state is VerificationState.FAILED:
        raise RuntimeError(
            f"SHA-256 verification failed for {remote_path}: "
            f"local={result.local_digest}, remote={result.remote_digest}"
        )
    return result.state


def _transfer_checksum_requested() -> bool:
    try:
        from hpc_gui.config.storage import get_transfer_checksum_verification_enabled
        return bool(get_transfer_checksum_verification_enabled())
    except Exception:
        return False


def _start_file_transfers(session_state, lifecycle, items, *, on_progress=None, conflict_resolver=None, files_backend=None, parent=None):
    """Queue file-view transfers through the shared transfer lifecycle."""
    from hpc_gui.wx_transfer_workspace import create_transfer_progress
    from hpc_gui.services.upload_plan import transfer_limits

    session = session_state.get("session") or {}
    files = files_backend or session.get("files")
    if not files or not items:
        raise RuntimeError(t("common.no_connection"))

    generation = session_state.get("generation")
    requested_mode = session_state.get("ftp_transfer_type")
    mode_enabled = requested_mode is not None

    def target_for(item):
        return conflict_target(files, item.op, item.dst, include_partial=mode_enabled)

    def current():
        return (
            session_state.get("session") is session
            and session_state.get("generation") == generation
            and not getattr(lifecycle, "shutdown_started", False)
            and not controller.engine.cancel_requested
        )

    def conflict_evaluator(item, action):
        source, target = read_conflict_metadata(files, item, target_path=target_for(item))
        return resolve_conflict_action(
            action, source_size=source.size, target_size=target.size,
            source_mtime=source.mtime, target_mtime=target.mtime,
        )

    def automatic_rename(item):
        if not current():
            return "cancel"
        candidate = available_rename_destination(files, item.op, item.dst, include_partial=mode_enabled)
        return ("rename", candidate) if candidate is not None and current() else "cancel"

    def wx_conflict_resolver(item):
        from hpc_gui.wx_conflict_bridge import request_conflict_decision

        return request_conflict_decision(
            parent, files, item, current, read_conflict_metadata(files, item, target_path=target_for(item)),
        )

    def execute(backend, item, progress, conflict_decision):
        if mode_enabled and item.op in {"upload", "download"}:
            from hpc_gui.services.transfer_mode_execution import execute_with_mode

            def verify_bytes(local, remote):
                item.verification_state = _verify_transfer_bytes(backend, local, remote)

            item.effective_mode = execute_with_mode(
                backend, item, progress, requested_mode, conflict_decision, _run_file_view_item,
                verify_bytes=verify_bytes if controller.checksum_enabled else None,
            )
        else:
            _run_file_view_item(backend, item, progress, conflict_decision=conflict_decision)

    def run_item(item, progress, *, conflict_decision=None):
        # FTP advertises serial queueing, but the browser/control connection
        # must still be independent of each transfer. SSH handles channel
        # isolation internally, so it does not need a second backend wrapper.
        opener = getattr(files, "open_transfer_backend", None)
        if item.op not in {"upload", "download"} or not callable(opener):
            execute(files, item, progress, conflict_decision)
            return
        backend = opener()
        if backend is None or backend is files:
            raise RuntimeError("Transfer backend factory did not return an isolated backend")
        try:
            execute(backend, item, progress, conflict_decision)
        finally:
            backend.close()

    transfer_window = None
    # Prefer embedded transfers panel when shell has one and caller is the shell frame
    embedded = session_state.get("embedded_transfers_panel")
    use_embedded = False

    def _embedded_alive(win):
        if win is None:
            return False
        try:
            import wx as _wx

            if not _wx.Window.FindWindowById(win.GetId()):
                return False
            if hasattr(win, "IsBeingDeleted") and win.IsBeingDeleted():
                return False
            st = getattr(win, "_wx_transfer_state", None)
            if isinstance(st, dict) and st.get("closed"):
                return False
            return True
        except Exception:
            return False

    if embedded and _embedded_alive(embedded):
        previous = getattr(embedded, "_wx_transfer_state", {}).get("controller")
        previous_engine = getattr(previous, "engine", None)
        if previous_engine is not None and (previous_engine.running or previous_engine.pending or previous_engine.failed):
            # A second batch must not replace a live or resumable queue owner.
            if parent is None:
                import wx

                parent = wx.GetTopLevelParent(embedded)
            embedded = None
    if embedded and _embedded_alive(embedded):
        # Route shell's own file transfers to the embedded panel; keep detached path for external parents
        if parent is not None and hasattr(parent, "_wx_shell_controls"):
            transfer_window = embedded
            use_embedded = True
        elif parent is None:
            transfer_window = embedded
            use_embedded = True
    if not use_embedded and parent:
        import wx

        ready = Event()

        def create_window():
            nonlocal transfer_window
            transfer_window = create_transfer_progress(parent)
            ready.set()

        try:
            if wx.IsMainThread():
                create_window()
            else:
                wx.CallAfter(create_window)
                ready.wait(2)
        except (AssertionError, RuntimeError):
            pass

    def queue_event(event, item):
        if transfer_window:
            if event == "failed":
                error = next(
                    (message for failed, message in controller.engine.failed if failed is item),
                    "Transfer failed without a backend error message.",
                )
                item.error_message = str(error)
            transfer_window._wx_transfer_queue(event, item, owner=controller)

    def progress_event(item, done, total):
        if transfer_window:
            transfer_window._wx_transfer_progress(item, done, total, owner=controller)
        if on_progress:
            on_progress(item, done, total)

    profile = session.get("profile") if isinstance(session.get("profile"), dict) else {}
    configured_parallel_limit, parallel_limit = transfer_limits(files, profile)
    sessions = session_state.setdefault("transfer_sessions", set())

    def register_run():
        sessions.add(controller)

    def finish_run():
        sessions.discard(controller)
        if transfer_window:
            transfer_window._wx_transfer_finish(owner=controller)

    custom_resolver = conflict_resolver or session_state.get("conflict_resolver")
    controller = TransferSessionController(
        items,
        run_item,
        parallel_limit=parallel_limit,
        conflict_check=lambda item: (
            item.op in {"upload", "download"}
            and target_for(item) is not None
        ),
        conflict_resolver=custom_resolver or (wx_conflict_resolver if parent else None),
        conflict_rename=automatic_rename if parent and custom_resolver is None else None,
        conflict_evaluator=conflict_evaluator,
        verify=None if mode_enabled else lambda item: _verify_transfer_item(files, item),
        on_queue=queue_event,
        on_progress=progress_event,
        on_start=register_run,
        on_done=finish_run,
    )
    controller.configured_parallel_limit = configured_parallel_limit
    if _transfer_checksum_requested():
        controller.set_checksum_enabled(True)
    if transfer_window:
        transfer_window._wx_transfer_set_controller(controller)
    if session_state.get("conflict_policy"):
        controller.set_conflict_policy(session_state["conflict_policy"])
    controller.start()
    if lifecycle is not None:
        register_cleanup = lifecycle.register_cleanup
        try:
            supports_worker_safety = "worker_safe" in inspect.signature(register_cleanup).parameters
        except (TypeError, ValueError):
            supports_worker_safety = False
        if supports_worker_safety:
            register_cleanup(controller.cancel, worker_safe=True)
        else:
            register_cleanup(controller.cancel)
        if transfer_window:
            lifecycle.register_cleanup(lambda: transfer_window._wx_transfer_close(None))
    return controller
