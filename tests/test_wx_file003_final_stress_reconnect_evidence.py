"""GUI-FILE-003 reconnect, Unicode, and predecessor-evidence stress groups."""

from __future__ import annotations

import threading

import time

import subprocess

import sys

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language

from hpc_gui.wx_local_files import show_local_files

from hpc_gui.wx_remote_files import WxRemoteDirectoryModel

from hpc_gui.wx_remote_files_view import show_remote_files

from mock_hpc_files import MockRemoteFilesBackend

from support.wx_file003_stress import EXECUTED, METRICS, _record

def _pump(app, predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()

def _settle(app, window=None, rounds: int = 6) -> None:
    if window is not None:
        window.SetSize(wx.Size(1100, 760))
        window.Show()
        window.Layout()
        window.SendSizeEvent()
    for _ in range(rounds):
        app.ProcessPendingEvents()
        # wx frees closed frames during idle processing, so a loop that only
        # pumps pending events keeps them in GetTopLevelWindows() forever.
        wx.SafeYield()
        if window is not None:
            window.Layout()
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    wx.SafeYield()

@pytest.fixture(scope="module")
def wx_app():
    load_language("en")
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App.Get()
        if app is None:
            app = wx.App(False)
    yield app
    _destroy_windows(app)
    if owns_app:
        app.Destroy()

@pytest.fixture(autouse=True)
def _cleanup_windows_after_test(wx_app):
    load_language("en")
    baseline = {id(window) for window in wx.GetTopLevelWindows()}
    yield
    _destroy_windows(wx_app, baseline)

def _destroy_windows(app, baseline=None):
    baseline = baseline or set()
    for window in wx.GetTopLevelWindows():
        if window and id(window) not in baseline:
            window.Destroy()
    _settle(app)

def _local_frame(app, path):
    show_local_files(path=path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 0)
    _settle(app, frame, rounds=3)
    return frame

def _remote_frame(app, backend, path="/work", loader=None):
    show_remote_files(
        model=WxRemoteDirectoryModel(path),
        loader=loader or backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    _settle(app, frame, rounds=3)
    return frame

def _key(listing, code, *, ctrl=False, shift=False):
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(code)
    event.SetControlDown(ctrl)
    event.SetShiftDown(shift)
    listing.ProcessEvent(event)

def _select_only(listing, *rows):
    for index in range(listing.GetItemCount()):
        listing.Select(index, False)
    for row in rows:
        listing.Select(row)

def _rows(listing):
    return [listing.GetItemText(index) for index in range(listing.GetItemCount())]

class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)

UNICODE_NAMES = [
    "plain.txt",
    "with space.txt",
    "  double  space  .txt",
    "türkçe ğüşöçı.txt",
    "TÜRKÇE İĞÜŞÖÇ.txt",
    "café-résumé.txt",
    "naïve façade.txt",
    "Ünlü Öğrenci Şubesi.txt",
    "кириллица файл.txt",
    "日本語のファイル.txt",
    "中文文件名.txt",
    "한국어 파일.txt",
    "(parens) name.txt",
    "[brackets] name.txt",
    "{braces} name.txt",
    "it's an apostrophe.txt",
    "rock & roll.txt",
    "dash-and_underscore.txt",
    "plus+equals=sign.txt",
    "percent%20literal.txt",
    "hash#tag.txt",
    "at@sign.txt",
    "dollar$sign.txt",
    "exclamation!.txt",
    "comma,separated.txt",
    "semicolon;here.txt",
    "tilde~name.txt",
    "back`tick.txt",
    "caret^name.txt",
    "emoji 🚀 rocket.txt",
    "emoji 🇹🇷 flag.txt",
    "mixed Ünicode 日本 файл.txt",
    "trailing space name .txt",
    "  leading space.txt",
    "ÇÖĞÜŞİ upper.txt",
    "çöğüşı lower.txt",
    "ß eszett.txt",
    "ñ tilde-n.txt",
    "å ø æ nordic.txt",
    "ελληνικά.txt",
    "עברית.txt",
    "العربية.txt",
    "ไทย.txt",
    "tiếng việt.txt",
    "čeština šžý.txt",
    "polski ąćęłńóśźż.txt",
    "magyar őű.txt",
    "român ăâîșț.txt",
    "very  many   spaces.txt",
    "final ünïcödé çase.txt",
]

class _AccountingFiles:
    """Records every backend-started transfer id exactly as it happens."""

    def __init__(self, existing=(), failing=()):
        self.lock = threading.Lock()
        self.existing = set(existing)
        self.failing = set(failing)
        self.started = []
        self.methods = []

    def exists(self, path):
        return path in self.existing

    def _run(self, method, identity):
        with self.lock:
            self.started.append(identity)
            self.methods.append(method)
        if identity in self.failing:
            raise OSError("transfer failed for " + identity)

    def upload(self, source, destination):
        self._run("upload", destination)

    def download(self, source, destination):
        self._run("download", destination)

    def resume_upload(self, source, destination):
        self._run("resume_upload", destination)

    def resume_download(self, source, destination):
        self._run("resume_download", destination)

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

@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.regression
def test_editor_wx_lifecycle_predecessor_preserves_context_menu_runtime():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_wx_editor_window_parity.py",
            "tests/test_wx_embedded_terminal.py",
            "tests/test_wx_file003_final_stress.py::test_stress_a_right_click_retarget",
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, f"child failed {result.returncode}:\n{result.stdout}\n{result.stderr}"
