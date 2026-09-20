"""W12 — Real SFTP semantics validation.

Laboratory strategy (mirrors W11): hermetic tests below use small fake
transports at a legitimate boundary (the paramiko SFTP client behind
``SSHFilesBackend``, the files backend behind the wx file-view ``run_item``);
real-wire behavior is proven by ``tests/support/mock_ssh_server.py``-adjacent
suites plus the authorized containerized lab run ``EV-W12-EXT-001``.

Requirement map (all owned by W12):
  HPC-W03-SFTP-001  whole Workstream B contract (this module + lab matrix)
  HPC-W03-SFTP-002  create directory            (lab matrix EV-W12-EXT-001)
  HPC-W03-SFTP-003  upload small text file      (lab matrix)
  HPC-W03-SFTP-004  list + metadata             (lab matrix)
  HPC-W03-SFTP-005  download + bytes/hash       (lab matrix)
  HPC-W03-SFTP-006  rename                      (DEF-W12-001 + lab matrix)
  HPC-W03-SFTP-007  overwrite with confirmation (REQ tests + lab matrix)
  HPC-W03-SFTP-008  cancel an overwrite         (REQ tests + lab matrix)
  HPC-W03-SFTP-009  delete file                 (lab matrix)
  HPC-W03-SFTP-010  remove directory            (lab matrix)
  HPC-W03-SFTP-011  spaces + Unicode path       (lab matrix)
  HPC-W03-SFTP-012  permission-denied path      (DEF-W12-001 + lab matrix)
  HPC-W03-SFTP-013  missing target/path         (DEF-W12-001 + lab matrix)
  HPC-W03-SFTP-014  disconnect mid-transfer     (DEF-W12-002 + lab matrix)
  HPC-W03-SFTP-015  local/remote hash capture   (lab matrix)

Defect regressions (counted W12 remediations):
  DEF-W12-001  SSHFilesBackend.rename bypassed _translate_remote_errors, so a
               missing/denied rename surfaced as a bare paramiko error with
               ``filename=None`` (no attributable path).
  DEF-W12-002  wx file-view run_item never forwarded the engine progress
               callback into backend upload/download, so mid-transfer progress
               stayed invisible and cancel_all could not interrupt an
               in-flight transfer (bytes kept flowing until completion).
"""

from __future__ import annotations

import errno
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.transfer_controller import TransferCancelled, TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_shell import _run_file_view_item


# ---------------------------------------------------------------------------
# Fakes (legitimate boundaries only)
# ---------------------------------------------------------------------------

class _FakeSFTP:
    """Stands in for the paramiko SFTP client behind SSHFilesBackend.

    Real code exercised: SSHFilesBackend.rename incl. error translation.
    Mocked boundary: the SFTP wire client only.
    What this does NOT prove: real-server errno mapping (covered by the
    authorized lab matrix EV-W12-EXT-001).
    """

    def __init__(self, *, rename_error: Exception | None = None):
        self.rename_error = rename_error
        self.rename_calls: list[tuple[str, str]] = []

    def rename(self, src: str, dst: str) -> None:
        self.rename_calls.append((src, dst))
        if self.rename_error is not None:
            raise self.rename_error


def _backend_with_sftp(sftp: _FakeSFTP) -> SSHFilesBackend:
    backend = SSHFilesBackend.__new__(SSHFilesBackend)
    backend.ssh = type("SSH", (), {"sftp": sftp})()
    return backend


class _FakeFiles:
    """Stands in for a files backend behind the wx file-view run_item.

    Real code exercised: _run_file_view_item dispatch/progress plumbing.
    Mocked boundary: the backend transfer methods only.
    """

    def __init__(self, *, chunks: int = 3, support_progress: bool = True):
        self.chunks = chunks
        self.support_progress = support_progress
        self.upload_calls: list[tuple[str, str]] = []
        self.progress_seen: list[tuple[int, int]] = []

    def _run(self, src: str, dst: str, progress_cb=None) -> None:
        self.upload_calls.append((src, dst))
        if progress_cb is None:
            return
        for done in range(1, self.chunks + 1):
            progress_cb(done, self.chunks)

    if True:  # keep method shape explicit for signature probing
        pass

    def upload(self, src: str, dst: str, progress_cb=None) -> None:
        if not self.support_progress and progress_cb is not None:
            raise AssertionError("backend without progress support got progress_cb")
        self._run(src, dst, progress_cb)

    def download(self, src: str, dst: str, progress_cb=None) -> None:
        self._run(src, dst, progress_cb)


# ---------------------------------------------------------------------------
# DEF-W12-001 — rename errors carry the source path
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.regression
def test_rename_missing_attaches_source_path() -> None:
    """REQ-SFTP-006/013: rename of a missing source reports WHICH path failed."""
    sftp = _FakeSFTP(rename_error=FileNotFoundError(errno.ENOENT, "No such file"))
    backend = _backend_with_sftp(sftp)
    with pytest.raises(FileNotFoundError) as excinfo:
        backend.rename("/remote/missing-src.txt", "/remote/dst.txt")
    assert excinfo.value.filename == "/remote/missing-src.txt"
    assert sftp.rename_calls == [("/remote/missing-src.txt", "/remote/dst.txt")]


@pytest.mark.unit
@pytest.mark.regression
def test_rename_denied_attaches_source_path() -> None:
    """REQ-SFTP-006/012: denied rename reports WHICH path was denied."""
    sftp = _FakeSFTP(rename_error=PermissionError(errno.EACCES, "Permission denied"))
    backend = _backend_with_sftp(sftp)
    with pytest.raises(PermissionError) as excinfo:
        backend.rename("/remote/locked.txt", "/remote/dst.txt")
    assert excinfo.value.filename == "/remote/locked.txt"


@pytest.mark.unit
def test_rename_success_uses_sftp_atomic_path() -> None:
    """Happy path: rename delegates to the SFTP channel exactly once."""
    sftp = _FakeSFTP()
    backend = _backend_with_sftp(sftp)
    backend.rename("/remote/a.txt", "/remote/b.txt")
    assert sftp.rename_calls == [("/remote/a.txt", "/remote/b.txt")]


class _DeniedSFTP:
    """SFTP client whose stat/open raise bare errors like paramiko does."""

    def stat(self, _path: str):
        raise PermissionError(errno.EACCES, "Permission denied")

    def open(self, _path: str, _mode: str):
        raise PermissionError(errno.EACCES, "Permission denied")

    def close(self) -> None:
        pass


class _DeniedOpenSFTP:
    """stat succeeds but open is denied (existing yet unreadable entry)."""

    def stat(self, _path: str):
        return type("Attr", (), {"st_size": 6, "st_mtime": 0})()

    def open(self, _path: str, _mode: str):
        raise PermissionError(errno.EACCES, "Permission denied")

    def close(self) -> None:
        pass


def _backend_with_transfer_sftp(sftp) -> SSHFilesBackend:
    backend = SSHFilesBackend.__new__(SSHFilesBackend)

    class _SSH:
        def open_transfer_sftp(self):
            return sftp

    backend.ssh = _SSH()
    return backend


@pytest.mark.unit
@pytest.mark.regression
def test_upload_denied_attaches_remote_path(tmp_path) -> None:
    """REQ-SFTP-003/012: denied upload reports WHICH remote path was denied."""
    local = tmp_path / "up.txt"
    local.write_bytes(b"payload\n")
    backend = _backend_with_transfer_sftp(_DeniedSFTP())
    with pytest.raises(PermissionError) as excinfo:
        backend.upload(str(local), "/remote/locked/up.txt")
    assert excinfo.value.filename == "/remote/locked/up.txt"


@pytest.mark.unit
@pytest.mark.regression
def test_download_denied_attaches_remote_path(tmp_path) -> None:
    """REQ-SFTP-005/012: denied download reports WHICH remote path was denied.

    stat succeeds (the entry exists and is visible) but the open is denied,
    which is exactly the path that used to surface paramiko's bare error.
    """
    backend = _backend_with_transfer_sftp(_DeniedOpenSFTP())
    with pytest.raises(PermissionError) as excinfo:
        backend.download("/remote/locked/file.txt", str(tmp_path / "down.txt"))
    assert excinfo.value.filename == "/remote/locked/file.txt"


# ---------------------------------------------------------------------------
# DEF-W12-002 — wx file-view run_item forwards progress (mid-transfer state)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.regression
def test_run_item_forwards_progress_to_backend() -> None:
    """REQ-SFTP-014: per-chunk progress reaches the engine mid-transfer."""
    files = _FakeFiles(chunks=3)
    seen: list[tuple[int, int]] = []
    item = TransferItem("upload", "/local/a.txt", "/remote/a.txt")
    _run_file_view_item(files, item, lambda d, t: seen.append((d, t)))
    assert (1, 3) in seen and (3, 3) in seen
    assert seen[-1] == (1, 1)  # completion marker still emitted
    assert files.upload_calls == [("/local/a.txt", "/remote/a.txt")]


@pytest.mark.unit
@pytest.mark.regression
def test_run_item_cancel_interrupts_inflight_upload() -> None:
    """REQ-SFTP-014 lifecycle: engine cancel aborts the transfer promptly."""
    files = _FakeFiles(chunks=100)

    def cancelling_progress(done: int, total: int) -> None:
        if done >= 2:
            raise TransferCancelled()

    item = TransferItem("upload", "/local/big.bin", "/remote/big.bin")
    with pytest.raises(TransferCancelled):
        _run_file_view_item(files, item, cancelling_progress)
    # Only a bounded prefix ran before the interrupt fired.
    assert files.upload_calls == [("/local/big.bin", "/remote/big.bin")]


@pytest.mark.unit
def test_run_item_supports_backend_without_progress_param() -> None:
    """Compat: backends without progress_cb still work (no crash, completes)."""

    class _LegacyFiles:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def upload(self, src: str, dst: str) -> None:
            self.calls.append((src, dst))

    legacy = _LegacyFiles()
    seen: list[tuple[int, int]] = []
    item = TransferItem("upload", "/local/a.txt", "/remote/a.txt")
    _run_file_view_item(legacy, item, lambda d, t: seen.append((d, t)))
    assert legacy.calls == [("/local/a.txt", "/remote/a.txt")]
    assert seen == [(1, 1)]


@pytest.mark.unit
def test_run_item_rejects_unsupported_op() -> None:
    """Negative path: non-transfer ops fail loudly, never silently succeed."""
    files = _FakeFiles()
    item = TransferItem("delete", "/remote/a.txt", "/remote/a.txt")
    with pytest.raises(RuntimeError, match="unsupported transfer item"):
        _run_file_view_item(files, item, lambda _d, _t: None)
    assert files.upload_calls == []


# ---------------------------------------------------------------------------
# REQ-SFTP-007/008 — overwrite confirmation + cancel leaves bytes intact
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_conflict_cancel_leaves_remote_bytes_intact() -> None:
    """Cancel-an-overwrite must not touch the destination (no side effect)."""
    remote = {"/remote/report.txt": b"original-bytes"}

    def run_item(item: TransferItem, progress) -> None:
        raise AssertionError("backend must not run on cancel")

    controller = TransferSessionController(
        [TransferItem("upload", "/local/report.txt", "/remote/report.txt")],
        run_item,
        conflict_check=lambda item: item.dst in remote,
        conflict_resolver=lambda item: "cancel",
    )
    controller.engine.start()
    assert controller.engine.wait(5)
    assert remote["/remote/report.txt"] == b"original-bytes"
    assert [error for _item, error in controller.engine.failed] == ["cancelled"]
    assert controller.engine.completed == []


@pytest.mark.unit
def test_conflict_overwrite_replaces_remote_bytes() -> None:
    """Happy path: confirmed overwrite replaces the destination bytes."""
    remote = {"/remote/report.txt": b"original-bytes"}

    def run_item(item: TransferItem, progress) -> None:
        remote[item.dst] = b"new-bytes"
        progress(1, 1)

    controller = TransferSessionController(
        [TransferItem("upload", "/local/report.txt", "/remote/report.txt")],
        run_item,
        conflict_check=lambda item: item.dst in remote,
        conflict_resolver=lambda item: "overwrite",
    )
    controller.engine.start()
    assert controller.engine.wait(5)
    assert remote["/remote/report.txt"] == b"new-bytes"
    assert controller.engine.failed == []


# ---------------------------------------------------------------------------
# GUI proof — real wx conflict-dialog events (Cancel / Overwrite)
# ---------------------------------------------------------------------------

wx = pytest.importorskip("wx", reason="wx GUI proof requires wxPython")
pytestmark_gui = [pytest.mark.gui, pytest.mark.wx]


@pytest.fixture
def wx_app():
    from hpc_gui.core.i18n import load_language

    load_language("en")
    app = wx.App.Get()
    owned = app is None
    if owned:
        app = wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        try:
            window.Destroy()
        except Exception:
            pass
    try:
        app.ProcessPendingEvents()
    except Exception:
        pass
    if owned:
        try:
            app.Destroy()
        except Exception:
            pass


@pytest.mark.gui
@pytest.mark.wx
def test_wx_conflict_dialog_cancel_button_returns_cancel(wx_app) -> None:
    """GUI-001: real Cancel click resolves the conflict as cancel."""
    from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog

    parent = wx.Frame(None)
    try:
        item = TransferItem("upload", "/local/a.txt", "/remote/a.txt")
        dlg = create_transfer_conflict_dialog(parent, None, item)
        assert dlg is not None
        cancel_btn = dlg._wx_conflict_controls["cancel"]
        clicked: list[str] = []

        def pump_until(predicate, timeout_s: float = 5.0) -> bool:
            import time

            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                wx_app.ProcessPendingEvents()
                wx_app.Yield(True)
                if predicate():
                    return True
                time.sleep(0.01)
            return predicate()

        wx_app.ProcessPendingEvents()
        cancel_btn.Command(wx.CommandEvent(wx.wxEVT_BUTTON, cancel_btn.GetId()))
        assert pump_until(lambda: dlg._wx_conflict_result["value"] == "cancel")
        clicked.append(dlg._wx_conflict_result["value"])
        dlg.Destroy()
        assert clicked == ["cancel"]
    finally:
        parent.Destroy()
        wx_app.ProcessPendingEvents()


@pytest.mark.gui
@pytest.mark.wx
def test_wx_conflict_dialog_overwrite_button_returns_overwrite(wx_app) -> None:
    """GUI-002: real Overwrite click resolves the conflict as overwrite."""
    from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog

    parent = wx.Frame(None)
    try:
        item = TransferItem("upload", "/local/a.txt", "/remote/a.txt")
        dlg = create_transfer_conflict_dialog(parent, None, item)
        assert dlg is not None
        overwrite_btn = dlg._wx_conflict_controls["overwrite"]

        def pump_until(predicate, timeout_s: float = 5.0) -> bool:
            import time

            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                wx_app.ProcessPendingEvents()
                wx_app.Yield(True)
                if predicate():
                    return True
                time.sleep(0.01)
            return predicate()

        wx_app.ProcessPendingEvents()
        overwrite_btn.Command(wx.CommandEvent(wx.wxEVT_BUTTON, overwrite_btn.GetId()))
        assert pump_until(lambda: dlg._wx_conflict_result["value"] == "overwrite")
        dlg.Destroy()
    finally:
        parent.Destroy()
        wx_app.ProcessPendingEvents()
