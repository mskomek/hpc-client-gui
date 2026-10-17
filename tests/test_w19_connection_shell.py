"""W19 embedded shell navigation and reconnect acceptance tests."""

import pytest

pytest_plugins = ("w19_connection_fixtures",)

from w19_connection_support import FakeSsh, _attached_ssh, _fake_session, wx

pytestmark = [pytest.mark.gui, pytest.mark.wx]


# ---------------------------------------------------------------------------
# GUI: shell tab order / NAV routing / keyboard+focus (SHELL-* TODOs)
# ---------------------------------------------------------------------------


CANONICAL_TAB_ORDER = (
    "APP-CONNECT",
    "NAV-TERMINAL",
    "NAV-JOBS",
    "NAV-DIRECTORIES",
    "NAV-FILES",
    "NAV-EDITOR",
    "NAV-LOGS",
)


def _build_shell(wx_app):
    from hpc_gui.wx_shell import create_shell_frame

    frame, lifecycle, session_state = create_shell_frame(wx_app)
    frame.Show()
    wx_app.ProcessPendingEvents()
    return frame, lifecycle, session_state


def test_shell_tab_order_is_canonical(wx_app):
    """TODO SHELL-NAV-001: one frozen main-tab order."""
    from hpc_gui.wx_shell import create_shell_frame

    frame, _, _ = create_shell_frame(wx_app)
    try:
        frame.Show()
        wx_app.ProcessPendingEvents()
        notebook = frame._wx_shell_controls["notebook"]
        pages = frame._wx_shell_controls["pages"]
        assert notebook.GetPageCount() == len(CANONICAL_TAB_ORDER)
        indices = [notebook.FindPage(pages[key]["page"]) for key in CANONICAL_TAB_ORDER]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)
    finally:
        # The real shell owns nested wx.Notebook children. EVT_CLOSE runs
        # page/lifecycle callbacks before native Destroy; calling Destroy
        # directly bypasses that contract and can crash wxGTK teardown.
        frame.Close()


def test_nav_actions_route_to_embedded_pages(wx_app):
    """TODO SHELL-NAV-002: NAV-* selects the existing embedded page."""
    from hpc_gui.wx_shell import _dispatch

    frame, lifecycle, session_state = _build_shell(wx_app)
    try:
        notebook = frame._wx_shell_controls["notebook"]
        pages = frame._wx_shell_controls["pages"]
        before = len(wx.GetTopLevelWindows())
        for key in ("NAV-TERMINAL", "NAV-JOBS", "NAV-DIRECTORIES", "NAV-FILES", "NAV-EDITOR", "NAV-LOGS", "APP-CONNECT"):
            _dispatch(key, frame, lifecycle, session_state)
            wx_app.ProcessPendingEvents()
            assert notebook.GetSelection() == notebook.FindPage(pages[key]["page"]), key
        assert len(wx.GetTopLevelWindows()) == before
    finally:
        # The real shell owns nested wx.Notebook children. EVT_CLOSE runs
        # page/lifecycle callbacks before native Destroy; calling Destroy
        # directly bypasses that contract and can crash wxGTK teardown.
        frame.Close()


def test_keyboard_tab_navigation_and_focus_restoration(wx_app):
    """TODO SHELL-TABS-001/002: tabs reachable, selection + focus deterministic."""
    from hpc_gui.wx_shell import _dispatch

    frame, lifecycle, session_state = _build_shell(wx_app)
    try:
        notebook = frame._wx_shell_controls["notebook"]
        pages = frame._wx_shell_controls["pages"]
        count = notebook.GetPageCount()
        assert count == len(CANONICAL_TAB_ORDER)
        for index in list(range(count)) + [0, count - 1]:
            notebook.SetSelection(index)
            wx_app.ProcessPendingEvents()
            assert notebook.GetSelection() == index
        _dispatch("NAV-TERMINAL", frame, lifecycle, session_state)
        wx_app.ProcessPendingEvents()
        terminal_page = pages["NAV-TERMINAL"]["page"]
        assert notebook.GetSelection() == notebook.FindPage(terminal_page)
        focus = wx.Window.FindFocus()
        assert focus is not None
        ancestor = focus
        while ancestor is not None and ancestor is not terminal_page:
            ancestor = ancestor.GetParent()
        assert ancestor is terminal_page
    finally:
        # The real shell owns nested wx.Notebook children. EVT_CLOSE runs
        # page/lifecycle callbacks before native Destroy; calling Destroy
        # directly bypasses that contract and can crash wxGTK teardown.
        frame.Close()


# ---------------------------------------------------------------------------
# session rebinding across reconnect / profile switch
# ---------------------------------------------------------------------------


def test_reconnect_rebinds_all_domains_through_canonical_session(wx_app):
    """REQ CONN-010..014: terminal/jobs/remote see the new canonical session."""
    from hpc_gui.wx_shell import _connection_callbacks
    from hpc_gui.wx_lifecycle import WxLifecycleController

    frame, lifecycle_state, session_state = _build_shell(wx_app)
    lifecycle = WxLifecycleController()
    try:
        cbs = _connection_callbacks(session_state, frame, lifecycle)
        ssh_a, ssh_b = FakeSsh(), FakeSsh()
        session_a = _fake_session(name="lab-a", ssh=ssh_a)
        session_b = _fake_session(name="lab-b", ssh=ssh_b)
        cbs["on_connected"](session_a)
        terminal = session_state.get("_embedded_terminal_panel")
        assert terminal is not None
        assert _attached_ssh(terminal) is ssh_a
        cbs["on_connected"](session_b)
        assert session_state["session"] is session_b
        assert _attached_ssh(terminal) is ssh_b
        assert session_state["generation"] >= 2
    finally:
        # The real shell owns nested wx.Notebook children. EVT_CLOSE runs
        # page/lifecycle callbacks before native Destroy; calling Destroy
        # directly bypasses that contract and can crash wxGTK teardown.
        frame.Close()


def test_profile_switch_invalidates_navigation_and_filters(monkeypatch):
    """TODO HPC-W02-TODO-002: stores/filters follow the new profile.

    Private navigation state is intentionally unavailable without an OS
    keyring. The tested boundary is per-profile routing, so provide a fake
    encrypted-store backend, never weakening production keyring requirements.
    """
    from hpc_gui.services.remote_navigation_store import navigation_store_for_profile
    from hpc_gui.wx_shell import _remote_files_callbacks

    monkeypatch.setattr(
        "hpc_gui.services.remote_navigation_store.is_available", lambda: True
    )
    monkeypatch.setattr(
        "hpc_gui.services.remote_navigation_store.load_private_profile_data",
        lambda profile_id, namespace, default: dict(default),
    )
    store_a = navigation_store_for_profile("profile-alpha")
    store_b = navigation_store_for_profile("profile-beta")
    assert store_a is not store_b
    session_state = {"session": None, "generation": 0}

    def filters_for(profile_id, file_filters):
        session_state["session"] = {
            "profile": {"id": profile_id, "file_filters": file_filters},
            "files": object(),
        }
        cbs = _remote_files_callbacks(session_state, None, None)
        return cbs["provider_filters"](), cbs["navigation_store"]()

    filters_a, resolved_a = filters_for("profile-alpha", ["*.out"])
    filters_b, resolved_b = filters_for("profile-beta", ["*.log"])
    assert tuple(filters_a) == ("*.out",)
    assert tuple(filters_b) == ("*.log",)
    assert resolved_a is store_a
    assert resolved_b is store_b
