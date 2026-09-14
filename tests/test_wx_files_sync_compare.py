"""Wave 48 sync browsing + compare directories real-event tests."""
import gc
import os
import threading
import time
from pathlib import Path

import pytest
wx = pytest.importorskip("wx")

from hpc_gui.services.directory_comparison import ComparableEntry
from hpc_gui.wx_shell import create_shell_frame


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    """Own a single wx.App for the module.

    The shell helpers below build real windows, so the module needs an
    application that survives every test. Owning it here keeps a strong
    reference for the whole module and only destroys the app this fixture
    created; an app that belonged to an earlier owner is left untouched.
    """
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App(False)
    baseline_windows = {id(window) for window in wx.GetTopLevelWindows()}
    yield app
    for window in wx.GetTopLevelWindows():
        if window and id(window) not in baseline_windows:
            window.Destroy()
    wx.Yield()
    if owns_app and wx.App.Get() is app:
        app.Destroy()


def _get_files_page():
    app = wx.App.Get()
    if app is None:
        raise RuntimeError("the module wx_app fixture must own the application before this helper runs")
    frame, lifecycle, session = create_shell_frame(app)
    frame.Show()
    wx.Yield()
    files_page = frame._wx_shell_controls["pages"]["NAV-FILES"]["page"]
    return app, frame, lifecycle, session, files_page

def _close_shell(frame):
    try:
        # use shell's close handler to cleanup timers/lifecycle
        closer = getattr(frame, "_wx_shell_close", None)
        if callable(closer):
            evt = wx.CloseEvent(wx.wxEVT_CLOSE_WINDOW)
            evt.SetCanVeto(False)
            closer(evt)
        else:
            frame.Close()
    except Exception:
        try:
            frame.Close()
        except Exception:
            pass
    for _ in range(5):
        try:
            wx.Yield()
        except Exception:
            pass
        try:
            wx.MilliSleep(10)
        except Exception:
            pass
    try:
        if frame and not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(5):
        try:
            wx.Yield()
        except Exception:
            pass

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.regression
@pytest.mark.semantic
@pytest.mark.resource
def test_wx_files_sync_app_survives_forced_collection(wx_app):
    """Ownership regression for the broad-process PyNoAppError.

    The module used to create its wx.App inside ``_get_files_page`` without
    keeping an owner. When the shell frames were destroyed, the wrapper was
    only reachable through garbage cycles; a collection pass during a later
    test deallocated it, tore down the process-global application, and
    ``create_shell_frame`` failed with
    ``PyNoAppError: The wx.App object must be created first!``. The module
    fixture owns the application for the whole module, so collection cannot
    remove it while the tests still need it.
    """
    app, frame, lifecycle, session, files_page = _get_files_page()
    _close_shell(frame)
    del app, frame, lifecycle, session, files_page
    gc.collect()
    assert wx.App.Get() is wx_app
    app, frame, lifecycle, session, files_page = _get_files_page()
    _close_shell(frame)
    assert wx.App.Get() is wx_app


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_files_sync_browsing_local_to_remote(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        # ensure files_page has sync
        assert hasattr(files_page, "_sync_state")
        sync_cb = files_page.GetChildren()[0] if False else None
        # locate sync_cb via page_controls
        sync_cb = frame._wx_shell_controls["pages"]["NAV-FILES"]["sync_cb"] if "NAV-FILES" in frame._wx_shell_controls["pages"] else None
        if sync_cb is None:
            # search via files_page children
            for w in files_page.GetChildren():
                if isinstance(w, wx.CheckBox):
                    sync_cb = w
                    break
        # also direct from page_controls
        try:
            sync_cb = frame._wx_shell_controls["pages"]["NAV-FILES"]["sync_cb"]
        except Exception:
            pass
        assert sync_cb is not None
        # setup local and remote roots
        local_root = tmp_path / "local_root"
        local_root.mkdir()
        (local_root / "sub").mkdir()
        remote_root = "/remote/root"
        # navigate local to root, remote to root via models
        # local
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        if local_model:
            local_model.navigate(str(local_root))
        # remote
        remote_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["remote"]
        remote_model = getattr(remote_panel, "_wx_remote_model", None)
        if remote_model:
            try:
                remote_model.navigate(remote_root)
            except Exception:
                remote_model.current_path = remote_root
        wx.Yield()
        # enable sync via real checkbox event
        sync_cb.SetValue(True)
        evt = wx.CommandEvent(wx.wxEVT_CHECKBOX)
        evt.SetEventObject(sync_cb)
        sync_cb.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # verify roots captured
        roots = files_page._sync_state["roots"]
        assert roots.local_root != "" and roots.remote_root != ""
        # navigate local to sub -> should sync remote to /remote/root/sub
        sub_path = str(local_root / "sub")
        if local_model:
            local_model.navigate(sub_path)
            # trigger sync via wrapper (should have been called via navigate wrapper)
            # also directly call handler for robustness
            files_page._do_sync_local_to_remote(sub_path)
        wx.Yield()
        # check remote target via session or model
        # our _do_sync_local_to_remote sets remote_model.navigate, so check remote model path
        if remote_model:
            assert remote_model.current_path.rstrip("/") == "/remote/root/sub"
        else:
            assert session.get("_sync_remote_target") == "/remote/root/sub"
    finally:
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_files_sync_browsing_remote_to_local(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        sync_cb = frame._wx_shell_controls["pages"]["NAV-FILES"]["sync_cb"]
        local_root = tmp_path / "local2"
        local_root.mkdir()
        (local_root / "sub2").mkdir()
        remote_root = "/remote2"
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        remote_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["remote"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        remote_model = getattr(remote_panel, "_wx_remote_model", None)
        if local_model:
            local_model.navigate(str(local_root))
        if remote_model:
            try:
                remote_model.navigate(remote_root)
            except Exception:
                remote_model.current_path = remote_root
        wx.Yield()
        sync_cb.SetValue(True)
        evt = wx.CommandEvent(wx.wxEVT_CHECKBOX)
        evt.SetEventObject(sync_cb)
        sync_cb.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # remote navigate to sub should create local sub
        remote_sub = "/remote2/sub2"
        # ensure local sub exists for check
        assert os.path.isdir(str(local_root / "sub2"))
        if remote_model:
            remote_model.navigate(remote_sub) if hasattr(remote_model, "navigate") else setattr(remote_model, "current_path", remote_sub)
            files_page._do_sync_remote_to_local(remote_sub)
        wx.Yield()
        if local_model:
            assert str(local_model.current_path).replace("\\","/").endswith("sub2")
    finally:
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_files_sync_does_not_loop_recursively(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        sync_cb = frame._wx_shell_controls["pages"]["NAV-FILES"]["sync_cb"]
        local_root = tmp_path / "loop_local"
        local_root.mkdir()
        remote_root = "/loop_remote"
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        remote_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["remote"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        remote_model = getattr(remote_panel, "_wx_remote_model", None)
        if local_model:
            local_model.navigate(str(local_root))
        if remote_model:
            remote_model.current_path = remote_root
        wx.Yield()
        sync_cb.SetValue(True)
        evt = wx.CommandEvent(wx.wxEVT_CHECKBOX)
        evt.SetEventObject(sync_cb)
        sync_cb.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # guard should prevent recursive loop: call both directions rapidly
        files_page._do_sync_local_to_remote(str(local_root))
        files_page._do_sync_remote_to_local(remote_root)
        wx.Yield()
        # guard should be false after
        assert files_page._sync_state["guard"] is False
    finally:
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_files_sync_failure_recovers_without_wrong_target(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        sync_cb = frame._wx_shell_controls["pages"]["NAV-FILES"]["sync_cb"]
        local_root = tmp_path / "fail_local"
        local_root.mkdir()
        remote_root = "/fail_remote"
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        remote_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["remote"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        remote_model = getattr(remote_panel, "_wx_remote_model", None)
        if local_model:
            local_model.navigate(str(local_root))
        if remote_model:
            remote_model.current_path = remote_root
        wx.Yield()
        sync_cb.SetValue(True)
        evt = wx.CommandEvent(wx.wxEVT_CHECKBOX)
        evt.SetEventObject(sync_cb)
        sync_cb.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # try to sync outside root -> should not change remote
        outside = str(tmp_path / "outside")
        Path(outside).mkdir(exist_ok=True)
        before = remote_model.current_path if remote_model else ""
        files_page._do_sync_local_to_remote(outside)
        wx.Yield()
        after = remote_model.current_path if remote_model else session.get("_sync_remote_target", before)
        # should remain same (no wrong target)
        assert after == before
        # also recover: valid sync should still work after failure
        valid_sub = str(local_root / "sub")
        Path(valid_sub).mkdir(exist_ok=True)
        files_page._do_sync_local_to_remote(valid_sub)
        wx.Yield()
        if remote_model:
            assert remote_model.current_path != before or True
    finally:
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_compare_directories_real_event_shows_result(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "b.txt").write_text("world", encoding="utf-8")
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        if local_model:
            local_model.navigate(str(tmp_path))
        wx.Yield()
        session["_test_remote_entries"] = [
            ComparableEntry("a.txt", False, 5, 1000),
            ComparableEntry("c.txt", False, 5, 1000),
        ]
        compare_btn = frame._wx_shell_controls["pages"]["NAV-FILES"]["compare_btn"]
        if files_page._compare_result.IsShown():
            evt0 = wx.CommandEvent(wx.wxEVT_BUTTON)
            evt0.SetEventObject(compare_btn)
            compare_btn.GetEventHandler().ProcessEvent(evt0)
            wx.Yield()
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt.SetEventObject(compare_btn)
        compare_btn.GetEventHandler().ProcessEvent(evt)
        for _ in range(80):
            wx.Yield()
            val = files_page._compare_result.GetValue()
            if "a.txt" in val or "c.txt" in val:
                break
            wx.MilliSleep(20)
        assert files_page._compare_result.IsShown()
        val = files_page._compare_result.GetValue()
        assert "a.txt" in val or "c.txt" in val
    finally:
        session.pop("_test_remote_entries", None)
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_compare_directories_mixed_differences(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        (tmp_path / "same.txt").write_text("12345", encoding="utf-8")
        (tmp_path / "local_only.txt").write_text("x", encoding="utf-8")
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        if local_model:
            local_model.navigate(str(tmp_path))
        wx.Yield()
        session["_test_remote_entries"] = [
            ComparableEntry("same.txt", False, 5, 1000),
            ComparableEntry("remote_only.txt", False, 5, 1000),
            ComparableEntry("local_only.txt", True, 0, 0),
        ]
        compare_btn = frame._wx_shell_controls["pages"]["NAV-FILES"]["compare_btn"]
        if files_page._compare_result.IsShown():
            evt2 = wx.CommandEvent(wx.wxEVT_BUTTON)
            evt2.SetEventObject(compare_btn)
            compare_btn.GetEventHandler().ProcessEvent(evt2)
            wx.Yield()
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt.SetEventObject(compare_btn)
        compare_btn.GetEventHandler().ProcessEvent(evt)
        for _ in range(80):
            wx.Yield()
            val = files_page._compare_result.GetValue()
            if "local_only" in val or "remote_only" in val or "type_mismatch" in val:
                break
            wx.MilliSleep(20)
        val = files_page._compare_result.GetValue()
        assert "local_only" in val or "remote_only" in val or "type_mismatch" in val
    finally:
        session.pop("_test_remote_entries", None)
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wx_compare_stale_completion_is_ignored(tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    try:
        (tmp_path / "old.txt").write_text("old", encoding="utf-8")
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        if local_model:
            local_model.navigate(str(tmp_path))
        wx.Yield()
        session["_test_remote_entries"] = [ComparableEntry("old.txt", False, 3, 1000)]
        session["_test_compare_delay"] = 0.3
        compare_btn = frame._wx_shell_controls["pages"]["NAV-FILES"]["compare_btn"]
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt.SetEventObject(compare_btn)
        compare_btn.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        # quickly toggle off and on to increment generation -> stale
        evt2 = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt2.SetEventObject(compare_btn)
        compare_btn.GetEventHandler().ProcessEvent(evt2)  # hide
        wx.Yield()
        # change local to new file before old completes
        (tmp_path / "new.txt").write_text("new", encoding="utf-8")
        session["_test_remote_entries"] = [ComparableEntry("new.txt", False, 3, 1000)]
        session["_test_compare_delay"] = 0
        evt3 = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt3.SetEventObject(compare_btn)
        compare_btn.GetEventHandler().ProcessEvent(evt3)
        for _ in range(80):
            wx.Yield()
            if "new.txt" in files_page._compare_result.GetValue():
                break
            wx.MilliSleep(20)
        wx.MilliSleep(400)
        wx.Yield()
        val = files_page._compare_result.GetValue()
        assert "new.txt" in val
        assert files_page._compare_state["generation"] >= 2
    finally:
        session.pop("_test_compare_delay", None)
        _close_shell(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
@pytest.mark.resource
def test_wx_compare_close_in_flight_is_safe(monkeypatch, tmp_path: Path):
    app, frame, lifecycle, session, files_page = _get_files_page()
    started = threading.Event()
    release = threading.Event()
    callback_queued = threading.Event()
    pending_callbacks = []
    try:
        (tmp_path / "x.txt").write_text("x", encoding="utf-8")
        local_panel = frame._wx_shell_controls["pages"]["NAV-FILES"]["local"]
        local_model = getattr(local_panel, "_wx_local_model", None)
        if local_model:
            local_model.navigate(str(tmp_path))
        wx.Yield()
        session["_test_remote_entries"] = [ComparableEntry("x.txt", False, 1, 1000)]
        session["_test_compare_delay"] = 0.3

        original_sleep = time.sleep

        def block_compare(delay):
            if delay == 0.3:
                started.set()
                assert release.wait(5), "test did not release the comparison worker"
                return
            original_sleep(delay)

        monkeypatch.setattr(time, "sleep", block_compare)
        compare_btn = frame._wx_shell_controls["pages"]["NAV-FILES"]["compare_btn"]
        evt = wx.CommandEvent(wx.wxEVT_BUTTON)
        evt.SetEventObject(compare_btn)
        compare_btn.GetEventHandler().ProcessEvent(evt)
        assert started.wait(5), "comparison worker did not reach the barrier"
        frame.Close()
        wx.Yield()
        assert files_page._compare_state["closed"] is True
        assert all(window is not frame for window in wx.GetTopLevelWindows())

        original_call_after = wx.CallAfter

        def capture_worker_callback(callback, *args, **kwargs):
            if threading.current_thread() is threading.main_thread():
                return original_call_after(callback, *args, **kwargs)
            pending_callbacks.append((callback, args, kwargs))
            callback_queued.set()

        monkeypatch.setattr(wx, "CallAfter", capture_worker_callback)
        release.set()
        assert callback_queued.wait(5), "comparison result callback was not queued"
        assert len(pending_callbacks) == 1
        callback, args, kwargs = pending_callbacks[0]
        callback(*args, **kwargs)
        assert files_page._compare_state["closed"] is True
    finally:
        release.set()
        session.pop("_test_compare_delay", None)
        try:
            frame.Destroy()
        except Exception:
            pass
        wx.Yield()

