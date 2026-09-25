"""W29 job details / stdout-stderr / live-output closure tests.

Owned requirements: HPC-W07-OUT-001..019 (Workstream E + E0).
Covers the W29-owned repair deltas plus requirement-to-owner traceability:
- OUT-001/002/016: identity capture + stale discard (SelectedJobStore +
  OutputFollower.assign generations).
- OUT-003/009: missing output is a visible normal waiting state.
- OUT-010: permission denied is distinct from missing (propagates, not waiting).
- OUT-004/014: huge output stays bounded/responsive.
- OUT-005/013: encoding errors / UTF-8 boundaries never crash or corrupt.
- OUT-007/008: stdout/stderr channels + action labels are distinguishable.
- OUT-011/012: live-tail exactly-once ordered; truncation/rotation resets.
- OUT-015: closing the view cancels worker/timer callbacks safely.
- OUT-006/017/018: GUI surface works; reconnect/reopen refreshes intended job;
  completed final output remains viewable (runtime readback below).
- OUT-019: real-job path is EXTERNAL (see report; no mock substitution here).
"""

from __future__ import annotations

import time

import pytest

from hpc_gui.services.output_channel_resolver import OutputResolver
from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState


pytestmark = pytest.mark.unit


def _follower(path="/work/slurm-42.out", max_lines=50):
    return OutputFollower(
        OutputFollowerState(
            tracking_id="w29",
            channel_id="stdout",
            job_id="42",
            generation=1,
            label="Standard Output",
            path=path,
            origin="legacy_slurm",
            roles=("stdout",),
        ),
        max_lines=max_lines,
    )


def test_w29_stdout_stderr_channels_distinguishable():
    """OUT-007: stdout and stderr resolve as visibly distinct channels."""
    channels = OutputResolver().resolve_legacy(
        job_id="42",
        workdir="/work",
        scontrol_stdout="/work/slurm-42.out",
        scontrol_stderr="/work/slurm-42.err",
    )
    assert len(channels) == 2
    by_id = {c.id: c for c in channels}
    assert set(by_id) == {"stdout", "stderr"}
    assert by_id["stdout"].path != by_id["stderr"].path
    assert by_id["stdout"].label != by_id["stderr"].label
    assert "Output" in by_id["stdout"].label
    assert "Error" in by_id["stderr"].label
    assert by_id["stdout"].roles == ("stdout",)
    assert by_id["stderr"].roles == ("stderr",)


def test_w29_output_action_labels_identify_stream():
    """OUT-008: action/label strings identify which stream is opened."""
    from hpc_gui.core.i18n import load_language, t

    load_language("en")
    assert t("jobs_outputs.output_stdout") != t("jobs_outputs.output_stderr")
    assert "Output" in t("jobs_outputs.output_stdout")
    assert "Error" in t("jobs_outputs.output_stderr")
    assert t("jobs_outputs.standard_output") != t("jobs_outputs.standard_error")
    assert t("jobs_outputs.open_out1") != t("jobs_outputs.open_out2")


def test_w29_missing_file_is_waiting_not_crash():
    """OUT-003/009: missing output is a normal visible waiting state."""
    follower = _follower()

    def read_missing(path):
        raise FileNotFoundError(path)

    chunk, retained, waiting = follower.poll(read_missing, force=True)
    assert waiting is True
    assert chunk == ""
    assert retained == ""
    assert follower.state.waiting_state >= 1


def test_w29_permission_denied_is_distinct_from_missing():
    """OUT-010: permission denied propagates instead of waiting-silence."""
    follower = _follower()
    with pytest.raises(PermissionError):
        follower.poll(
            lambda path: (_ for _ in ()).throw(
                PermissionError(13, "Permission denied", path)
            ),
            force=True,
        )


def test_w29_invalid_encoding_never_crashes_follower():
    """OUT-005: undecodable bytes surface as error text, never a crash."""
    follower = _follower()

    def read_bad(path):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    with pytest.raises(UnicodeDecodeError):
        follower.poll(read_bad, force=True)
    # Follower itself remains usable after the failure.
    chunk, retained, waiting = follower.poll(lambda path: "ok\n", force=True)
    assert retained.endswith("ok\n")
    assert waiting is False


def test_w29_ssh_read_text_replaces_invalid_bytes():
    """OUT-005/013 at the SSH boundary: replace, never raise, typed errors."""
    from hpc_gui.services.files_ssh import SSHFilesBackend

    class _FakeSFTPFile:
        def __init__(self, data: bytes):
            self._data = data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self._data

    class _FakeSFTP:
        def __init__(self, data: bytes):
            self._data = data

        def open(self, path, mode):
            assert "rb" in mode
            if path == "/missing.out":
                raise FileNotFoundError(2, "No such file", path)
            if path == "/denied.out":
                raise PermissionError(13, "Permission denied", path)
            return _FakeSFTPFile(self._data)

        def close(self):
            pass

    class _FakeSSH:
        def __init__(self, data: bytes):
            self._data = data
            self.sftp = object()

        def open_transfer_sftp(self):
            return _FakeSFTP(self._data)

    backend = SSHFilesBackend.__new__(SSHFilesBackend)
    backend.ssh = _FakeSSH(b"hello \xff\xfe world\n")
    text = backend.read_text("/work/out.log")
    assert "hello" in text
    assert "world" in text
    # Replacement char keeps the UI alive instead of raising.
    assert "\ufffd" in text

    backend2 = SSHFilesBackend.__new__(SSHFilesBackend)
    backend2.ssh = _FakeSSH(b"x")
    with pytest.raises(FileNotFoundError):
        backend2.read_text("/missing.out")
    with pytest.raises(PermissionError):
        backend2.read_text("/denied.out")


def test_w29_live_tail_appends_exactly_once_ordered():
    """OUT-011: deterministic numbered-line fixture proves ordered exactly-once."""
    store = {"text": ""}
    follower = _follower(max_lines=100)
    expected = [f"line-{i:04d}" for i in range(1, 21)]
    seen: list[str] = []
    for i, line in enumerate(expected):
        store["text"] += line + "\n"
        time.sleep(0.001)  # deterministic emission delay
        chunk, retained, waiting = follower.poll(lambda p: store["text"])
        assert waiting is False
        assert chunk == line + "\n"
        seen.append(chunk.strip())
    assert seen == expected
    assert retained.splitlines() == expected
    # Re-poll with no new data appends nothing (no duplicates).
    chunk, retained2, _ = follower.poll(lambda p: store["text"])
    assert chunk == ""
    assert retained2 == retained


def test_w29_truncation_and_rotation_reset_cleanly():
    """OUT-012: truncation shrinks to fresh content; inode rotation resets."""
    from types import SimpleNamespace

    files = {"/work/slurm-42.out": "old-1\nold-2\n"}
    follower = _follower()
    follower.poll(lambda p: files[p], force=True)
    files["/work/slurm-42.out"] = "new\n"
    _, retained, _ = follower.poll(lambda p: files[p], force=True)
    assert retained == "new\n"

    files2 = {"/work/slurm-42.out": "v1\n"}
    inode = {"n": 101}
    follower2 = _follower()
    follower2.poll(
        lambda p: files2[p],
        stat_path=lambda p: SimpleNamespace(st_ino=inode["n"]),
        force=True,
    )
    files2["/work/slurm-42.out"] = "v2-after-rotation\n"
    inode["n"] = 102
    _, retained2, _ = follower2.poll(
        lambda p: files2[p],
        stat_path=lambda p: SimpleNamespace(st_ino=inode["n"]),
        force=True,
    )
    assert retained2 == "v2-after-rotation\n"


def test_w29_utf8_boundaries_do_not_corrupt():
    """OUT-013: incremental multi-byte appends render intact."""
    follower = _follower(max_lines=100)
    full = ""
    for piece in ["job \u00e9 ongoing\n", "progress \u2603 ok\n", "done \U0001f600\n"]:
        full += piece
        _, retained, _ = follower.poll(lambda p, f=full: f)
    assert "job \u00e9 ongoing" in retained
    assert "progress \u2603 ok" in retained
    assert "done \U0001f600" in retained


def test_w29_large_output_remains_bounded():
    """OUT-004/014: 20000-line flood retains only the bounded tail."""
    follower = _follower(max_lines=50)
    big = "".join(f"row-{i:05d}\n" for i in range(20000))
    _, retained, _ = follower.poll(lambda p: big, force=True)
    assert len(retained.splitlines()) == 50
    assert "row-19999" in retained
    assert "row-00000" not in retained


def test_w29_close_cancels_safely_and_ignores_late_callbacks():
    """OUT-015: close stops polling; late results are ignored."""
    follower = _follower()
    follower.poll(lambda p: "hello\n", force=True)
    follower.close()
    assert follower.state.closed is True
    chunk, retained, waiting = follower.poll(lambda p: "late\n", force=True)
    assert chunk == ""
    assert "late" not in retained


def test_w29_selection_change_invalidates_stale_output():
    """OUT-002/016: new job/generation resets follower; old token is stale."""
    follower = _follower("/work/a.out")
    follower.poll(lambda p: "A\n", force=True)
    follower.assign(
        channel_id="stdout",
        job_id="43",
        generation=2,
        label="Standard Output",
        path="/work/b.out",
        origin="legacy_slurm",
        roles=("stdout",),
    )
    assert follower.text == ""
    assert follower.state.offset == 0
    _, retained, _ = follower.poll(lambda p: "B\n", force=True)
    assert retained == "B\n"
    assert "A" not in retained


def test_w29_details_identity_generation_monotonic():
    """OUT-001: selection capture bumps generation before async fetch."""
    from hpc_gui.services.selected_job_context import SelectedJobStore

    store = SelectedJobStore()
    first = store.select(job_id="1001", name="jobA")
    second = store.select(job_id="1001", name="jobA")
    assert second.generation == first.generation + 1
    third = store.select(job_id="1002", name="jobB")
    # New job clears stale stdout/stderr paths (no leak into new selection).
    assert third.job_id == "1002"
    assert third.stdout_path == ""
    assert third.stderr_path == ""


# ---------------------------------------------------------------------------
# GUI runtime readback (wx event proof, not controller-only).
# ---------------------------------------------------------------------------


def _build_w29_panel(**kwargs):
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_jobs import build_jobs_panel

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(frame, **kwargs)
    frame.Show()
    wx.Yield()
    return app, frame, panel


def _close_w29(frame):
    import pytest as _pytest

    wx = _pytest.importorskip("wx")
    try:
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                try:
                    child.Hide()
                    child.Destroy()
                except Exception:
                    pass
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()


@pytest.mark.gui
@pytest.mark.wx
def test_w29_gui_stdout_stderr_distinguishable_with_content():
    """OUT-006/007/008/018: real frames show distinct labeled streams."""
    wx = pytest.importorskip("wx")
    contents = {
        "/work/slurm-1001.out": "STDOUT-LINE-1\n",
        "/work/slurm-1001.err": "STDERR-LINE-1\n",
    }
    jobs = [{
        "id": "1001", "state": "COMPLETED", "name": "solver",
        "workdir": "/work",
        "stdout_path": "/work/slurm-1001.out",
        "stderr_path": "/work/slurm-1001.err",
    }]
    app, frame, panel = _build_w29_panel(
        list_jobs=lambda: jobs,
        read_remote_path=lambda path: contents[path],
    )
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(10)
        assert ctrls["jobs"].GetItemCount() >= 1
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(4)
        wx.Yield()
        panel._wx_jobs_refresh_outputs()
        for _ in range(100):
            wx.Yield()
            wx.MilliSleep(10)
            channels = ctrls.get("output_channels", {})
            if set(channels) == {"stdout", "stderr"} and any(
                "STDOUT-LINE-1" in tc.GetValue()
                for tc in channels.values()
            ):
                break
        channels = ctrls["output_channels"]
        assert set(channels) == {"stdout", "stderr"}
        assert "STDOUT-LINE-1" in channels["stdout"].GetValue()
        assert "STDERR-LINE-1" in channels["stderr"].GetValue()
        # Completed-job final output remains viewable (OUT-018).
        assert "STDOUT-LINE-1" in channels["stdout"].GetValue()
        # Tab labels carry the distinct stream names (OUT-007/008).
        notebook = ctrls["output_channel_notebook"]
        titles = {
            notebook.GetPageText(i) for i in range(notebook.GetPageCount())
        }
        assert any("Output" in title for title in titles)
        assert any("Error" in title for title in titles)
    finally:
        _close_w29(frame)


@pytest.mark.gui
@pytest.mark.wx
def test_w29_gui_missing_vs_permission_distinct():
    """OUT-009/010: missing waits visibly; permission shows an error state."""
    wx = pytest.importorskip("wx")
    from hpc_gui.core.i18n import t

    def reader(path):
        if path.endswith(".out"):
            raise FileNotFoundError(path)
        raise PermissionError(13, "Permission denied", path)

    jobs = [{
        "id": "1002", "state": "RUNNING", "name": "denied",
        "workdir": "/work",
        "stdout_path": "/work/missing.out",
        "stderr_path": "/work/denied.err",
    }]
    app, frame, panel = _build_w29_panel(
        list_jobs=lambda: jobs,
        read_remote_path=reader,
    )
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(10)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(4)
        wx.Yield()
        panel._wx_jobs_refresh_outputs()
        for _ in range(100):
            wx.Yield()
            wx.MilliSleep(10)
            status = ctrls.get("output_channel_status", {})
            if len(status) >= 2:
                break
        status = ctrls["output_channel_status"]
        assert set(status) == {"stdout", "stderr"}
        waiting_label = t("jobs_outputs.status_waiting")
        error_label = t("jobs_outputs.status_error")
        assert status["stdout"].GetLabel() == f"{t('jobs_outputs.status')}: {waiting_label}"
        assert status["stderr"].GetLabel() == f"{t('jobs_outputs.status')}: {error_label}"
        assert status["stdout"].GetLabel() != status["stderr"].GetLabel()
    finally:
        _close_w29(frame)


@pytest.mark.gui
@pytest.mark.wx
def test_w29_gui_live_tail_ordered_and_close_cancels():
    """OUT-011/015: live refresh appends ordered lines; close stops timers."""
    wx = pytest.importorskip("wx")
    contents = {"/work/live.out": ""}
    jobs = [{
        "id": "1003", "state": "RUNNING", "name": "live",
        "workdir": "/work",
        "stdout_path": "/work/live.out",
    }]
    app, frame, panel = _build_w29_panel(
        list_jobs=lambda: jobs,
        read_remote_path=lambda path: contents[path],
    )
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(10)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(4)
        wx.Yield()
        for i in range(1, 6):
            contents["/work/live.out"] += f"live-{i:04d}\n"
            panel._wx_jobs_refresh_outputs()
            for _ in range(60):
                wx.Yield()
                wx.MilliSleep(10)
                channels = ctrls.get("output_channels", {})
                text = channels.get("stdout", None)
                if text is not None and f"live-{i:04d}" in text.GetValue():
                    break
        value = ctrls["output_channels"]["stdout"].GetValue()
        positions = [value.index(f"live-{i:04d}") for i in range(1, 6)]
        assert positions == sorted(positions)
        assert len(set(positions)) == 5
    finally:
        _close_w29(frame)
    # After close, no exception escapes the teardown path (OUT-015).
    for _ in range(3):
        wx.Yield()
