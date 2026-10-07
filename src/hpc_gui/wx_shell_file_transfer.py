"""wx shell file transfer workflows."""
from __future__ import annotations

from threading import Event, Thread
from pathlib import PurePosixPath
from hpc_gui.services.transfer_session_controller import TransferSessionController
import inspect
import os
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change


def _destination_exists(files, op: str, destination: str) -> bool:
    """Does the transfer destination already exist?

    A download writes to the local filesystem, so asking the remote backend
    whether the destination exists would both miss real conflicts and report
    phantom ones.
    """
    if op == "download":
        return os.path.exists(destination)
    probe = getattr(files, "exists", None)
    return bool(probe) and bool(probe(destination))


def _run_file_view_item(files, item, progress, *, conflict_decision=None):
    """Execute one wx file-view transfer item against a files backend.

    ``progress`` is the engine callback: backends that accept
    ``progress_cb`` receive it so mid-transfer progress stays visible and
    engine cancellation can interrupt an in-flight transfer instead of only
    taking effect between queued items.
    """
    if item.op == "upload":
        method = files.resume_upload if conflict_decision == "resume" else files.upload
        _call_transfer_with_progress(method, item.src, item.dst, progress)
    elif item.op == "download":
        method = files.resume_download if conflict_decision == "resume" else files.download
        _call_transfer_with_progress(method, item.src, item.dst, progress)
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
    from hpc_gui.services.transfer_integrity import VerificationState, verify_transfer

    try:
        from hpc_gui.config.storage import get_transfer_checksum_verification_enabled
        enabled = bool(get_transfer_checksum_verification_enabled())
    except Exception:
        enabled = False
    if not enabled:
        return VerificationState.OFF
    remote_hash = getattr(files, "sha256", None)
    if not callable(remote_hash):
        return VerificationState.UNSUPPORTED
    local_path = item.src if item.op == "upload" else item.dst
    remote_path = item.dst if item.op == "upload" else item.src
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
    from hpc_gui.config.storage import coerce_profile_transfer_parallelism

    session = session_state.get("session") or {}
    files = files_backend or session.get("files")
    if not files or not items:
        raise RuntimeError(t("common.no_connection"))

    def wx_conflict_resolver(item):
        import wx

        if session_state.get("conflict_policy") == "rename":
            target = PurePosixPath(item.dst)
            suffix = target.suffix
            stem = target.name[: -len(suffix)] if suffix else target.name
            for index in range(1, 10000):
                candidate = target.with_name(f"{stem} ({index}){suffix}")
                if not _destination_exists(files, item.op, str(candidate)):
                    return ("rename", str(candidate))
            return "cancel"

        from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog

        decision = {"value": "cancel"}
        ready = Event()

        def ask():
            try:
                dlg = create_transfer_conflict_dialog(parent, files, item)
                if not dlg:
                    decision["value"] = "cancel"
                    return
                dlg.ShowModal()
                raw = dlg._wx_conflict_result["value"]
                # if rename, raw is tuple
                if isinstance(raw, tuple) and raw and raw[0] == "rename":
                    decision["value"] = raw
                else:
                    # map string decisions
                    decision["value"] = raw if raw in {"overwrite", "skip", "resume", "cancel"} else "cancel"
                dlg.Destroy()
            finally:
                ready.set()

        try:
            wx.CallAfter(ask)
        except BaseException:
            return "cancel"
        ready.wait()
        return decision["value"]

    def run_item(item, progress, *, conflict_decision=None):
        _run_file_view_item(files, item, progress, conflict_decision=conflict_decision)

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
            transfer_window._wx_transfer_queue(event, item)

    def progress_event(item, done, total):
        if transfer_window:
            transfer_window._wx_transfer_progress(item, done, total)
        if on_progress:
            on_progress(item, done, total)

    profile = session.get("profile") if isinstance(session.get("profile"), dict) else {}
    parallel_limit = coerce_profile_transfer_parallelism(profile.get("transfer_parallelism", 1))
    controller = TransferSessionController(
        items,
        run_item,
        parallel_limit=parallel_limit,
        conflict_check=lambda item: _destination_exists(files, item.op, item.dst),
        conflict_resolver=conflict_resolver or session_state.get("conflict_resolver") or (wx_conflict_resolver if parent else None),
        verify=lambda item: _verify_transfer_item(files, item),
        on_queue=queue_event,
        on_progress=progress_event,
    )
    if _transfer_checksum_requested():
        controller.set_checksum_enabled(True)
    if transfer_window:
        transfer_window._wx_transfer_set_controller(controller)
    if session_state.get("conflict_policy"):
        controller.set_conflict_policy(session_state["conflict_policy"])
    sessions = session_state.setdefault("transfer_sessions", set())
    sessions.add(controller)
    controller.start()

    def forget_when_done():
        controller.engine.wait()
        sessions.discard(controller)
        if transfer_window:
            transfer_window._wx_transfer_finish()

    Thread(target=forget_when_done, daemon=True).start()
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
