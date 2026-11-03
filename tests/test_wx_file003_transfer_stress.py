from __future__ import annotations

# Fixture parameters intentionally shadow the imported fixture declaration.
# ruff: noqa: F811


import pytest

pytestmark = [pytest.mark.wx]

from support.wx_file003_stress_support import (
    _AccountingFiles, Lifecycle as _Lifecycle,
    EXECUTED, METRICS, UNICODE_NAMES, _key, _local_frame, _pump,
    _record, _remote_frame, _rows, _select_only, _settle,
    threading, time, wx,
)
from support.wx_file003_stress_support import wx_app, _cleanup_windows_after_test  # noqa: F401
from mock_hpc_files import MockRemoteFilesBackend

@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.resource
def test_stress_h_file_transfer_items(wx_app, tmp_path):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    submitted = []
    completed = []
    failed = []
    pending = []
    all_started = []
    session_state = {}

    for batch_index in range(10):
        destinations = ["/remote/b%d-i%d.bin" % (batch_index, item) for item in range(10)]
        conflicting = {destinations[position] for position in (1, 2, 3, 4)}
        failing = {destinations[5]} if batch_index % 2 == 0 else set()
        files = _AccountingFiles(existing=conflicting, failing=failing)
        session_state["session"] = {"files": files}

        (tmp_path / "src.bin").write_text("payload", encoding="utf-8")
        plain_download = tmp_path / ("down-%d-plain.bin" % batch_index)
        resumed_download = tmp_path / ("down-%d-resume.bin" % batch_index)
        resumed_download.write_bytes(b"partial")  # a real local-side conflict

        items = []
        for position, destination in enumerate(destinations):
            if position == 7:
                items.append(TransferItem("download", "/remote/src.bin", str(plain_download)))
            elif position == 8:
                items.append(TransferItem("download", "/remote/src.bin", str(resumed_download)))
            else:
                items.append(TransferItem("upload", str(tmp_path / "src.bin"), destination))
        submitted.extend(id(item) for item in items)

        decisions = {
            destinations[1]: "overwrite",
            destinations[2]: "resume",
            destinations[3]: "skip",
            destinations[4]: ("rename", destinations[4] + ".renamed"),
            str(resumed_download): "resume",
        }
        cancel_at = destinations[6] if batch_index == 9 else None
        if cancel_at:
            files.existing.add(cancel_at)

        def resolver(item, _decisions=decisions, _cancel=cancel_at):
            if _cancel and item.dst == _cancel:
                return "cancel"
            return _decisions.get(item.dst, "overwrite")

        controller = _start_file_transfers(
            session_state,
            _Lifecycle(),
            items,
            conflict_resolver=resolver,
        )
        assert controller.engine.wait(10)
        completed.extend(id(item) for item in controller.engine.completed)
        failed.extend(id(item) for item, _error in controller.engine.failed)
        pending.extend(id(item) for item in controller.engine.pending)
        all_started.extend(files.started)
        # The resume decision must reach the direction-specific backend method.
        assert "resume_upload" in files.methods, files.methods
        if not cancel_at:
            # The cancel batch stops before the download items by design.
            assert "resume_download" in files.methods, files.methods

    executed = len(submitted)
    terminal = set(completed) | set(failed) | set(pending)
    METRICS["lost_transfers"] += len(set(submitted) - terminal)
    METRICS["duplicate_transfers"] += len(all_started) - len(set(all_started))
    if session_state.get("transfer_sessions"):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and session_state["transfer_sessions"]:
            _settle(wx_app, 2)
        METRICS["leaked_transfer_sessions"] += len(session_state["transfer_sessions"])

    _record("FILE transfer items", executed, 100)
    assert len(completed) + len(failed) + len(pending) == 100
    assert len(failed) >= 5 and len(completed) >= 80 and len(pending) >= 1
    assert METRICS["lost_transfers"] == 0
    assert METRICS["duplicate_transfers"] == 0
    assert METRICS["leaked_transfer_sessions"] == 0

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.slow
def test_stress_i_unicode_and_space_names(wx_app, tmp_path, monkeypatch):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    typed = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return typed["name"]

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    away = tmp_path / "away"
    away.mkdir()
    local_frame = _local_frame(wx_app, tmp_path)
    notebook = local_frame._wx_local_notebook
    listing = local_frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: "away" in _rows(listing))
    _select_only(listing, _rows(listing).index("away"))
    local_frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: notebook.GetPageCount() == 2)

    backend = MockRemoteFilesBackend()
    remote_frame = _remote_frame(wx_app, backend)

    executed = 0
    for index, name in enumerate(UNICODE_NAMES):
        safe_name = name.strip() or "fallback.txt"

        # --- local rename via F2 -------------------------------------------
        notebook.SetSelection(0)
        _settle(wx_app)
        seed = tmp_path / ("seed-%d.txt" % index)
        seed.write_text("x", encoding="utf-8")
        local_frame._wx_local_run_action("refresh")
        _pump(wx_app, lambda: seed.name in _rows(local_frame._wx_local_controls["listing"]))
        control = local_frame._wx_local_controls["listing"]
        _select_only(control, _rows(control).index(seed.name))
        typed["name"] = safe_name
        _key(control, wx.WXK_F2)
        _pump(wx_app, lambda: not local_frame._wx_local_state["mutation_in_flight"])
        _settle(wx_app)
        renamed = tmp_path / safe_name
        assert renamed.exists(), safe_name
        assert safe_name in _rows(local_frame._wx_local_controls["listing"])

        # --- local copy into the other tab via Ctrl+C / Ctrl+V --------------
        control = local_frame._wx_local_controls["listing"]
        _select_only(control, _rows(control).index(safe_name))
        _key(control, ord("C"), ctrl=True)
        notebook.SetSelection(1)
        _settle(wx_app)
        _key(local_frame._wx_local_controls["listing"], ord("V"), ctrl=True)
        _pump(wx_app, lambda: not local_frame._wx_local_state["mutation_in_flight"])
        _settle(wx_app)
        assert (away / safe_name).exists(), safe_name
        (away / safe_name).unlink()
        renamed.unlink()

        # --- remote rename and Copy Path ------------------------------------
        remote_source = "/work/remote-%d.txt" % index
        backend.entries[remote_source] = False
        remote_frame._wx_remote_run_action("refresh", ())
        remote_listing = remote_frame._wx_remote_controls["listing"]
        _pump(wx_app, lambda: ("remote-%d.txt" % index) in _rows(remote_listing))
        typed["name"] = safe_name
        remote_frame._wx_remote_run_action("rename", (remote_source,), "/work")
        _pump(wx_app, lambda: not remote_frame._wx_remote_state["busy"])
        _settle(wx_app)
        assert ("/work/" + safe_name) in backend.entries, safe_name
        assert remote_source not in backend.entries
        backend.entries.pop("/work/" + safe_name)

        # --- transfer item keeps the name intact ----------------------------
        files = _AccountingFiles()
        controller = _start_file_transfers(
            {"session": {"files": files}},
            _Lifecycle(),
            [TransferItem("upload", str(tmp_path / safe_name), "/work/" + safe_name)],
        )
        assert controller.engine.wait(5)
        assert files.started == ["/work/" + safe_name], files.started
        executed += 1

    _record("unicode/space names", executed, 50)

@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
def test_reconnect_session_snapshot_repeated(wx_app, tmp_path):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    class SessionFiles(_AccountingFiles):
        def __init__(self, label, block=None):
            super().__init__()
            self.label = label
            self.block = block

        def upload(self, source, destination):
            if self.block is not None:
                self.started.append("start:" + destination)
                self.block.wait(3)
            self._run(self.label, destination)

    rounds = 20
    for index in range(rounds):
        release = threading.Event()
        first = SessionFiles("S1", block=release)
        second = SessionFiles("S2")
        state = {"session": {"files": first}}
        controller_one = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "a.txt", "/one-%d.txt" % index)],
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not first.started:
            time.sleep(0.005)
        assert first.started, "first operation never started"

        state["session"] = {"files": second}  # reconnect mid-flight
        release.set()
        assert controller_one.engine.wait(5)

        controller_two = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "b.txt", "/two-%d.txt" % index)],
        )
        assert controller_two.engine.wait(5)

        # The in-flight operation must stay on its own snapshot, and the new
        # session must only ever see the operation started after the reconnect.
        if ("/one-%d.txt" % index) in second.started:
            METRICS["mixed_session_transfer_operations"] += 1
        if first.methods != ["S1"] or second.methods != ["S2"]:
            METRICS["mixed_session_transfer_operations"] += 1
        if ("/two-%d.txt" % index) in first.started:
            METRICS["mixed_session_transfer_operations"] += 1

    EXECUTED["reconnect session snapshots"] = (rounds, rounds)
    assert METRICS["mixed_session_transfer_operations"] == 0

@pytest.mark.reporting
@pytest.mark.semantic
def test_transfer_stress_metrics():
    assert all(name in EXECUTED for name in ("FILE transfer items", "unicode/space names", "reconnect session snapshots"))
    for name in ("lost_transfers", "duplicate_transfers", "leaked_transfer_sessions", "mixed_session_transfer_operations"):
        assert METRICS[name] == 0, f"{name} = {METRICS[name]}"
