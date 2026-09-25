"""W27 run: editor conflicts, content edge cases (EDITX-001..011, TODO-002).

FIX-A (DEF-W27-001/002): complete find/replace — find-previous, explicit
wrap readback, case-sensitivity option, visible empty/no-match diagnostics.
FIX-B (DEF-W27-003 / HPC-W11-TODO-002): stale async editor-open requests are
sequenced and ignored instead of clobbering the newer document.
FIX-C (DEF-W27-004): binary/large initial content is refused from the
editable control and blocks text saves until a safe document loads.
"""
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_editor_view import build_editor_panel


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


def _click(control):
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))


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
    wx.SafeYield()
    app.Destroy()


def _close(frame, app):
    try:
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


def _open(frame, **kwargs):
    kwargs.setdefault("is_local", False)
    panel = build_editor_panel(frame, **kwargs)
    frame.Show()
    wx.Yield()
    return panel


@pytest.mark.gui
@pytest.mark.wx
def test_w27_find_next_previous_wrap_and_selection(wx_app):
    """EDITX-001/002/007: next/previous move the selection; wrap is explicit."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="foo bar foo")
        controls = panel._wx_editor_controls
        controls["find_in"].SetValue("foo")
        assert panel._wx_editor_find_next() is True
        assert controls["editor"].GetStringSelection() == "foo"
        first = controls["editor"].GetSelection()
        assert first == (0, 3)
        assert panel._wx_editor_find_next() is True
        assert controls["editor"].GetSelection() == (8, 11)
        # Exhausted: wraps to the top with a visible readback.
        assert panel._wx_editor_find_next() is True
        assert controls["editor"].GetSelection() == (0, 3)
        assert "Wrap" in controls["status"].GetLabel()
        # Previous from the top wraps to the bottom occurrence.
        assert panel._wx_editor_find_previous() is True
        assert controls["editor"].GetSelection() == (8, 11)
        assert "Wrap" in controls["status"].GetLabel()
        # Previous without wrap clears the status.
        assert panel._wx_editor_find_previous() is True
        assert controls["editor"].GetSelection() == (0, 3)
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_find_empty_query_is_visible_noop(wx_app):
    """EDITX-006: empty search is a diagnosed no-op, never a silent edit."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="foo bar")
        controls = panel._wx_editor_controls
        controls["find_in"].SetValue("")
        assert panel._wx_editor_find_next() is False
        assert panel._wx_editor_find_previous() is False
        assert panel._wx_editor_replace_all() == 0
        assert panel._wx_editor_replace_current() is False
        assert "Enter text" in controls["status"].GetLabel()
        assert controls["editor"].GetValue() == "foo bar"
        assert not panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_match_case_toggle_controls_find_and_replace(wx_app):
    """EDITX-005/042: the Match-case option governs find and replace."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="Foo foo FOO")
        controls = panel._wx_editor_controls
        controls["find_in"].SetValue("foo")
        controls["replace_in"].SetValue("x")
        # Case-sensitive: only the exact lowercase occurrence counts.
        controls["match_case"].SetValue(True)
        assert panel._wx_editor_find_next() is True
        assert controls["editor"].GetSelection() == (4, 7)
        assert panel._wx_editor_replace_all() == 1
        assert controls["editor"].GetValue() == "Foo x FOO"
        assert panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_match_case_insensitive_replace_all(wx_app):
    """EDITX-005: with Match-case off, replace-all spans all case variants."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="Foo foo FOO")
        controls = panel._wx_editor_controls
        controls["find_in"].SetValue("foo")
        controls["replace_in"].SetValue("x")
        controls["match_case"].SetValue(False)
        assert panel._wx_editor_replace_all() == 3
        assert controls["editor"].GetValue() == "x x x"
        assert panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_replace_current_advances_and_marks_dirty(wx_app):
    """EDITX-003/008: replace-current consumes successive matches, dirty flips."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="foo foo")
        controls = panel._wx_editor_controls
        assert not panel._wx_editor_model.controller.active.dirty
        controls["find_in"].SetValue("foo")
        controls["replace_in"].SetValue("baz")
        assert panel._wx_editor_replace_current() is True
        assert controls["editor"].GetValue() == "baz foo"
        assert panel._wx_editor_model.controller.active.dirty
        assert panel._wx_editor_replace_current() is True
        assert controls["editor"].GetValue() == "baz baz"
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_replace_all_no_match_is_visible_noop(wx_app):
    """EDITX-004 negative path: no match reports instead of editing."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="foo bar")
        controls = panel._wx_editor_controls
        controls["find_in"].SetValue("zzz")
        controls["replace_in"].SetValue("x")
        assert panel._wx_editor_replace_all() == 0
        assert "No match" in controls["status"].GetLabel()
        assert controls["editor"].GetValue() == "foo bar"
        assert not panel._wx_editor_model.controller.active.dirty
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_editor_header_buttons_truthfully_enabled(wx_app):
    """EDITX-035: header actions are enabled only when a real callback backs them."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="x")
        header = panel._wx_editor_header
        assert header["open"].IsEnabled() is False
        assert header["lint"].IsEnabled() is False
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_editor_header_open_enabled_with_callback(wx_app):
    """EDITX-035: with a real open callback the Open action is available."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="x", on_open=lambda _p: None)
        assert panel._wx_editor_header["open"].IsEnabled() is True
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_save_as_cancel_is_side_effect_free(wx_app, tmp_path, monkeypatch):
    """EDITX-014/037: declining the Save-As overwrite prompt changes nothing."""
    source = tmp_path / "orig.sh"
    source.write_text("original", encoding="utf-8")
    target = tmp_path / "copy.sh"
    target.write_text("target-content", encoding="utf-8")
    monkeypatch.setattr(wx, "MessageBox", lambda *_a, **_k: wx.NO)
    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(frame, path=str(source), content="original", is_local=True)
        frame.Show()
        wx.Yield()
        panel._wx_editor_header["path"].SetValue(str(target))
        panel._wx_editor_controls["editor"].SetValue("edited")
        _click(panel._wx_editor_controls["save"])
        wx.Yield()
        assert source.read_text(encoding="utf-8") == "original"
        assert target.read_text(encoding="utf-8") == "target-content"
        assert panel._wx_editor_model.controller.active.dirty
        assert "cancelled" in panel._wx_editor_controls["status"].GetLabel().lower()
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_stale_open_request_is_ignored(wx_app):
    """TODO-002: a stale async open must not replace the newer document."""
    frame = wx.Frame(None)
    try:
        panel = _open(frame, path="/remote/a.sh", content="A")
        controls = panel._wx_editor_controls
        tabs = controls["doc_tabs"]
        assert tabs.GetPageCount() == 1
        stale_seq = panel._wx_editor_begin_open_request()
        fresh_seq = panel._wx_editor_begin_open_request()
        assert panel._wx_editor_load_document("/remote/b.sh", "B", request_seq=fresh_seq) == "opened"
        assert tabs.GetPageCount() == 2
        assert panel._wx_editor_model.controller.active.path == "/remote/b.sh"
        # The late-arriving stale request is refused without side effects.
        assert panel._wx_editor_load_document("/remote/stale.sh", "STALE", request_seq=stale_seq) == "stale-ignored"
        assert tabs.GetPageCount() == 2
        assert panel._wx_editor_model.controller.active.path == "/remote/b.sh"
        assert controls["editor"].GetValue() == "B"
        assert "stale" in controls["status"].GetLabel().lower()
    finally:
        _close(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_w27_initial_binary_content_refused_and_save_blocked(wx_app):
    """EDITX-009/010/011: binary initial content never enters the editor and
    can never be saved out as text."""
    writes = []

    def save_remote(path, content):
        writes.append((path, content))

    frame = wx.Frame(None)
    try:
        panel = build_editor_panel(
            frame, path="/remote/blob.bin", content="ab\x00cd",
            is_local=False, save_remote=save_remote,
        )
        frame.Show()
        wx.Yield()
        controls = panel._wx_editor_controls
        assert controls["editor"].GetValue() == ""
        assert "Binary" in controls["status"].GetLabel()
        assert panel._wx_editor_state["binary_refused"] is True
        _click(controls["save"])
        wx.Yield()
        assert writes == []
        assert "not saved as text" in controls["status"].GetLabel()
        # Loading a safe document restores editing.
        assert panel._wx_editor_load_document("/remote/ok.sh", "echo hi") == "opened"
        assert panel._wx_editor_state["binary_refused"] is False
        controls["editor"].SetValue("echo changed")
        _click(controls["save"])
        _pump(wx_app, lambda: not panel._wx_editor_state["in_flight"])
        assert writes == [("/remote/ok.sh", "echo changed")]
    finally:
        _close(frame, wx_app)
