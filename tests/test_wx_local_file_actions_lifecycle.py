import threading
import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.gui, pytest.mark.wx, pytest.mark.concurrency]

from hpc_gui.wx_local_files import LocalBrowserModel, LocalEntry, show_local_files


def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    app.Destroy()


def _local(app, path):
    show_local_files(path=path)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 2)
    return frame


def test_wx_local_close_while_delete_in_flight_is_safe(wx_app, tmp_path: Path, monkeypatch):
    target = tmp_path / "remove.txt"
    target.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete_at

    def blocked_delete(model, paths, origin=None):
        # support both signatures
        if origin is None:
            started.set()
            release.wait(2)
            return original(model, paths, model.current_path)
        started.set()
        release.wait(2)
        return original(model, paths, origin)

    monkeypatch.setattr(LocalBrowserModel, "delete_at", blocked_delete)
    monkeypatch.setattr(LocalBrowserModel, "delete", lambda self, paths: blocked_delete(self, paths, self.current_path))
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _local(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "remove.txt")
    listing.Select(row)
    frame._wx_local_run_action("delete")
    assert started.wait(2)
    frame.Close(True)
    release.set()
    wx_app.ProcessPendingEvents()
    assert frame._wx_local_state["closed"]

def test_wx_local_close_while_paste_in_flight_is_safe(wx_app, tmp_path: Path, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    (target / "seed.txt").write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.paste_into

    def blocked_paste_into(self, dest, clip=None, move=None):
        started.set()
        release.wait(2)
        return original(self, dest, clip, move)

    monkeypatch.setattr(LocalBrowserModel, "paste_into", blocked_paste_into)
    monkeypatch.setattr(LocalBrowserModel, "paste", lambda self: blocked_paste_into(self, self.current_path, self.clipboard, self.clipboard_move))
    frame = _local(wx_app, target)
    frame._wx_local_model.copy([source])
    frame._wx_local_run_action("paste")
    assert started.wait(2)
    frame.Close(True)
    release.set()
    wx_app.ProcessPendingEvents()
    assert frame._wx_local_state["closed"]

def test_wx_local_old_mutation_completion_does_not_overwrite_navigation(wx_app, tmp_path: Path, monkeypatch):
    (tmp_path / "remove.txt").write_text("x", encoding="utf-8")
    destination = tmp_path / "other"
    destination.mkdir()
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete_at

    def blocked_delete_at(self, paths, origin):
        started.set()
        release.wait(2)
        return original(self, paths, origin)

    monkeypatch.setattr(LocalBrowserModel, "delete_at", blocked_delete_at)
    monkeypatch.setattr(LocalBrowserModel, "delete", lambda self, paths: blocked_delete_at(self, paths, self.current_path))
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _local(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "remove.txt")
    listing.Select(row)
    frame._wx_local_run_action("delete")
    assert started.wait(2)
    frame._wx_local_model.navigate(destination)
    frame._wx_local_state["view_generation"] += 1
    release.set()
    _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
    assert frame._wx_local_model.current_path == destination.resolve()

def test_wx_local_old_mutation_completion_does_not_overwrite_real_backspace_navigation(wx_app, tmp_path: Path, monkeypatch):
    target = tmp_path / "remove.txt"
    target.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete_at

    def blocked_delete_at(self, paths, origin):
        started.set()
        release.wait(2)
        return original(self, paths, origin)

    monkeypatch.setattr(LocalBrowserModel, "delete_at", blocked_delete_at)
    monkeypatch.setattr(LocalBrowserModel, "delete", lambda self, paths: blocked_delete_at(self, paths, self.current_path))
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _local(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "remove.txt")
    listing.Select(row)
    frame._wx_local_run_action("delete")
    assert started.wait(2)
    parent = tmp_path.parent.resolve()
    frame._wx_local_tabs[0]["path"] = parent
    frame._wx_local_tabs[0]["view_generation"] += 1
    frame._wx_local_state["view_generation"] += 1
    frame._wx_local_model.navigate(parent)
    assert frame._wx_local_model.current_path == parent
    release.set()
    _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
    assert frame._wx_local_model.current_path == parent

def test_wx_local_listing_runs_off_gui_thread(wx_app, tmp_path: Path, monkeypatch):
    (tmp_path / "entry.txt").write_text("x", encoding="utf-8")
    thread_ids = []
    original = LocalBrowserModel.list_entries

    def record_thread(model, path=None):
        thread_ids.append(threading.get_ident())
        return original(model, path)

    monkeypatch.setattr(LocalBrowserModel, "list_entries", record_thread)
    frame = _local(wx_app, tmp_path)
    assert thread_ids and thread_ids[0] != threading.get_ident()
    frame.Close(True)

def test_wx_local_stale_listing_does_not_overwrite_new_navigation(wx_app, tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    first.mkdir()
    second = first / "second"
    second.mkdir()
    (second / "current.txt").write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    call_count = {"c": 0}

    def loader(model, path=None):
        requested = Path(path)
        if requested == first.resolve():
            call_count["c"] += 1
            if call_count["c"] == 1:
                return (LocalEntry(second, True, 0),)
            started.set()
            release.wait(2)
            finished.set()
            return (LocalEntry(first / "old.txt", False, 0),)
        return (LocalEntry(second / "current.txt", False, 1),)

    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    show_local_files(path=first)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i) == "second" for i in range(listing.GetItemCount())))
    # trigger blocked refresh for first
    frame._wx_local_run_action("refresh")
    assert started.wait(2)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "second")
    for i in range(listing.GetItemCount()):
        listing.Select(i, False)
    listing.Select(idx, True)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    active = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(active.GetItemText(i) == "current.txt" for i in range(active.GetItemCount())))
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert any(active.GetItemText(i) == "current.txt" for i in range(active.GetItemCount()))
    assert not any(active.GetItemText(i) == "old.txt" for i in range(active.GetItemCount()))

def test_wx_local_listing_completion_after_close_is_safe(wx_app, tmp_path: Path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def loader(model, path=None):
        started.set()
        release.wait(2)
        finished.set()
        return ()

    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    show_local_files(path=tmp_path)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    assert started.wait(2)
    frame.Close(True)
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert frame._wx_local_state["closed"]

def test_wx_local_stale_listing_error_is_ignored_after_navigation(wx_app, tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    first.mkdir()
    second = first / "second"
    second.mkdir()
    (second / "current.txt").write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    errors = []
    call_count = {"c": 0}

    def loader(model, path=None):
        if Path(path) == first.resolve():
            call_count["c"] += 1
            if call_count["c"] == 1:
                return (LocalEntry(second, True, 0),)
            started.set()
            release.wait(2)
            raise RuntimeError("stale listing")
        return (LocalEntry(second / "current.txt", False, 1),)

    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: errors.append(args))
    show_local_files(path=first)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i) == "second" for i in range(listing.GetItemCount())))
    frame._wx_local_run_action("refresh")
    assert started.wait(2)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "second")
    for i in range(listing.GetItemCount()):
        listing.Select(i, False)
    listing.Select(idx, True)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    active = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(active.GetItemText(i) == "current.txt" for i in range(active.GetItemCount())))
    release.set()
    wx_app.ProcessPendingEvents()
    assert errors == []
    assert any(active.GetItemText(i) == "current.txt" for i in range(active.GetItemCount()))
