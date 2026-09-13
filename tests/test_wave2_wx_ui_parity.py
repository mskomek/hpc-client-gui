"""Wave 2 — wx.App UI Parity Tests.

These tests verify UI-level behavior that the model-layer tests cannot cover.
They all require wx.App and the _pump() helper pattern.
"""
# ruff: noqa
import time
from pathlib import Path
import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_local_files import show_local_files
from hpc_gui.core.i18n import load_language

pytestmark = pytest.mark.resource


def _pump(app, pred, timeout=2):
    dl = time.monotonic() + timeout
    while time.monotonic() < dl:
        app.ProcessPendingEvents()
        if pred():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert pred()


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        if window:
            window.Destroy()
    for _ in range(10):
        app.ProcessPendingEvents()
        wx.SafeYield()
        if not wx.GetTopLevelWindows():
            break
        wx.MilliSleep(10)
    assert not wx.GetTopLevelWindows(), "wx test windows remained after teardown"
    app.Destroy()


def _local(app, path):
    show_local_files(path=path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 0)
    return frame


class _Dialog:
    def __init__(self, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass


# ---------------------------------------------------------------------------
# Prompt 1: Selection Preservation After Rename
# ---------------------------------------------------------------------------

class TestSelectionPreservation:
    """Verify selection is preserved after rename operations."""

    @pytest.mark.wx
    @pytest.mark.gui
    @pytest.mark.regression
    def test_rename_preserves_selection(self, wx_app, tmp_path, monkeypatch):
        """Renaming through the visible menu keeps the new row selected."""
        source_name = "ölçüm_日本語.txt"
        target_name = "yeniden_adlandır.txt"
        (tmp_path / source_name).write_text("selected", encoding="utf-8")
        (tmp_path / "other.txt").write_text("other", encoding="utf-8")
        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 2)
        source_index = next(
            index for index in range(listing.GetItemCount())
            if listing.GetItemText(index) == source_name
        )
        listing.Select(source_index)
        assert listing.IsSelected(source_index)
        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog(target_name))

        orig = listing.PopupMenu

        def choose_rename(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "Rename":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    return

        listing.PopupMenu = choose_rename
        try:
            point = listing.ClientToScreen(
                wx.Point(5, listing.GetItemRect(source_index).y + 2)
            )
            event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
            event.SetPosition(point)
            listing.ProcessEvent(event)
        finally:
            listing.PopupMenu = orig

        _pump(
            wx_app,
            lambda: any(
                listing.GetItemText(index) == target_name
                for index in range(listing.GetItemCount())
            ),
        )
        target_index = next(
            index for index in range(listing.GetItemCount())
            if listing.GetItemText(index) == target_name
        )
        assert listing.IsSelected(target_index)

    @pytest.mark.wx
    @pytest.mark.gui
    def test_invalid_rename_shows_error_and_preserves_unicode_source(
        self, wx_app, tmp_path, monkeypatch,
    ):
        """Invalid rename leaves the Unicode source intact and reports an error."""
        src = tmp_path / "日本語テスト.txt"
        src.write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        # Try to rename to empty name (should fail)
        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog(""))

        captured_errors = []
        orig_show = wx.MessageBox

        def capture_error(msg, *args, **kwargs):
            captured_errors.append(msg)
            return wx.ID_OK

        monkeypatch.setattr(wx, "MessageBox", capture_error)

        orig = listing.PopupMenu
        def choose_rename(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "Rename":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        listing.PopupMenu = choose_rename

        point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(0).y + 2))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
        listing.PopupMenu = orig

        _pump(wx_app, lambda: bool(captured_errors))
        assert len(captured_errors) == 1
        assert captured_errors[0]
        assert src.exists(), "File should not be renamed on error"


# ---------------------------------------------------------------------------
# Prompt 2: Context Menu Event Wiring
# ---------------------------------------------------------------------------

@pytest.mark.gui
class TestContextMenuEventWiring:
    """Verify every context menu item has real event wiring."""

    @pytest.mark.wx
    def test_context_menu_open_wired(self, wx_app, tmp_path, monkeypatch):
        """Open menu item should trigger file open."""
        from hpc_gui import wx_local_files

        (tmp_path / "test.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        opened = []
        monkeypatch.setattr(
            wx_local_files, "reveal_in_file_manager", lambda path: opened.append(path)
        )
        orig = listing.PopupMenu

        def choose_open(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "Open":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break

        listing.PopupMenu = choose_open
        try:
            point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(0).y + 2))
            event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
            event.SetPosition(point)
            listing.ProcessEvent(event)
        finally:
            listing.PopupMenu = orig
        assert opened == [tmp_path / "test.txt"]

    @pytest.mark.wx
    def test_context_menu_rename_wired(self, wx_app, tmp_path, monkeypatch):
        """Rename menu item should trigger rename dialog."""
        (tmp_path / "old.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new.txt"))

        orig = listing.PopupMenu
        def choose_rename(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "Rename":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        listing.PopupMenu = choose_rename

        point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(0).y + 2))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
        listing.PopupMenu = orig

        _pump(wx_app, lambda: (tmp_path / "new.txt").exists())

    @pytest.mark.wx
    def test_context_menu_copy_clipboard(self, wx_app, tmp_path):
        """Copy menu item should put file in clipboard."""
        (tmp_path / "copied.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        orig = listing.PopupMenu
        def choose_copy(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "Copy":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        listing.PopupMenu = choose_copy

        point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(0).y + 2))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
        listing.PopupMenu = orig

        model = frame._wx_local_model
        assert len(model.clipboard) == 1, "Clipboard should have one item"
        assert model.clipboard[0].name == "copied.txt"
        assert model.clipboard_move is False, "Should be copy, not move"

    @pytest.mark.wx
    def test_context_menu_cut_clipboard(self, wx_app, tmp_path):
        """Cut menu item should put file in clipboard with move=True."""
        from hpc_gui.core.i18n import t

        (tmp_path / "cut.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        model = frame._wx_local_model
        orig = listing.PopupMenu

        def choose_cut(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == t("dirs.move"):
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break

        listing.PopupMenu = choose_cut
        try:
            point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(0).y + 2))
            event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
            event.SetPosition(point)
            listing.ProcessEvent(event)
        finally:
            listing.PopupMenu = orig

        assert len(model.clipboard) == 1, "Clipboard should have one item"
        assert model.clipboard_move is True, "Should be move (cut)"

    @pytest.mark.wx
    def test_context_menu_copy_path(self, wx_app, tmp_path):
        """Copy Path menu item should copy path to clipboard."""
        (tmp_path / "path_test.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        if wx.TheClipboard.IsOpened():
            wx.TheClipboard.Close()

        chosen = []
        orig = listing.PopupMenu
        def choose_copy_path(menu):
            for item in menu.GetMenuItems():
                label = item.GetItemLabelText()
                if "copy" in label.casefold() and "path" in label.casefold():
                    chosen.append(label)
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        listing.PopupMenu = choose_copy_path

        point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(0).y + 2))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
        listing.PopupMenu = orig

        assert chosen, "Copy Path action was not present in the context menu"
        assert wx.TheClipboard.Open()
        try:
            clipboard_text = wx.TextDataObject()
            assert wx.TheClipboard.GetData(clipboard_text)
            assert clipboard_text.GetText() == str(tmp_path / "path_test.txt")
        finally:
            wx.TheClipboard.Close()

    @pytest.mark.wx
    def test_background_new_folder_wired(self, wx_app, tmp_path, monkeypatch):
        """Background New Folder should create folder in current directory."""
        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() >= 0)

        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new_unicode_フォルダ"))

        orig = listing.PopupMenu
        def choose_new_folder(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "New Folder":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        listing.PopupMenu = choose_new_folder

        size = listing.GetSize()
        point = listing.ClientToScreen(wx.Point(5, max(5, size.height - 5)))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
        listing.PopupMenu = orig

        _pump(wx_app, lambda: (tmp_path / "new_unicode_フォルダ").is_dir())
        assert (tmp_path / "new_unicode_フォルダ").is_dir()

    @pytest.mark.wx
    def test_background_refresh_wired(self, wx_app, tmp_path):
        """Background Refresh should refresh the listing."""
        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() >= 0)

        count_before = listing.GetItemCount()

        # Add a new file
        (tmp_path / "new_file.txt").write_text("content", encoding="utf-8")

        orig = listing.PopupMenu
        def choose_refresh(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText() == "Refresh":
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        listing.PopupMenu = choose_refresh

        size = listing.GetSize()
        point = listing.ClientToScreen(wx.Point(5, max(5, size.height - 5)))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
        listing.PopupMenu = orig

        _pump(wx_app, lambda: listing.GetItemCount() > count_before)


# ---------------------------------------------------------------------------
# Prompt 3: Pane Labels and Roles
# ---------------------------------------------------------------------------

@pytest.mark.gui
class TestPaneLabels:
    """Verify pane labels and roles are clear."""

    @pytest.mark.wx
    def test_local_window_title(self, wx_app, tmp_path):
        """Local browser window should have clear title."""
        frame = _local(wx_app, tmp_path)

        title = frame.GetTitle()
        assert title, "Window should have a title"
        # Title should indicate this is a local browser
        assert "local" in title.lower() or "file" in title.lower() or "dizin" in title.lower()

    @pytest.mark.wx
    def test_toolbar_buttons_have_visible_affordance(self, wx_app, tmp_path):
        """Each toolbar control is visible and has a tooltip or a text label."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        for key in ["refresh_btn", "btn_drives", "btn_back", "btn_parent"]:
            button = controls[key]
            assert button.IsShownOnScreen(), f"Button {key} should be visible"
            assert button.GetToolTip() or button.GetLabel(), (
                f"Button {key} should have a tooltip or text label"
            )


# ---------------------------------------------------------------------------
# Prompt 4: Toolbar Alignment
# ---------------------------------------------------------------------------

@pytest.mark.gui
class TestToolbarAlignment:
    """Verify toolbar alignment and button states."""

    @pytest.mark.wx
    def test_back_button_disabled_when_no_history(self, wx_app, tmp_path):
        """Back button should be disabled when no history."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        assert not controls["btn_back"].IsEnabled()

    @pytest.mark.wx
    def test_parent_button_navigates_to_parent_directory(self, wx_app, tmp_path):
        """The visible parent button navigates from a nested folder."""
        parent = tmp_path / "parent"
        nested = parent / "child"
        nested.mkdir(parents=True)
        frame = _local(wx_app, nested)
        controls = frame._wx_local_controls
        button = controls["btn_parent"]
        assert button.IsEnabled()
        button.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
        _pump(wx_app, lambda: controls["path"].GetValue() == str(parent.resolve()))
        assert frame._wx_local_model.current_path == parent.resolve()

    @pytest.mark.wx
    def test_refresh_button_always_enabled(self, wx_app, tmp_path):
        """Refresh button should always be enabled."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        assert controls["refresh_btn"].IsEnabled()


# ---------------------------------------------------------------------------
# Prompt 5: Text Field Labels
# ---------------------------------------------------------------------------

@pytest.mark.gui
class TestTextFieldLabels:
    """Verify text fields have clear labels."""

    @pytest.mark.wx
    def test_path_bar_exists(self, wx_app, tmp_path):
        """Path bar should exist and show current directory."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        path_ctrl = controls["path"]
        assert path_ctrl.GetValue() == str(Path(tmp_path).resolve())

    @pytest.mark.wx
    def test_path_bar_editable(self, wx_app, tmp_path):
        """Path bar should be editable for direct path entry."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        assert controls["path"].IsEditable()


# ---------------------------------------------------------------------------
# Prompt 6: Status/Progress Feedback
# ---------------------------------------------------------------------------

@pytest.mark.gui
class TestStatusFeedback:
    """Verify the directory listing renders the expected file count."""

    @pytest.mark.wx
    def test_listing_renders_all_files(self, wx_app, tmp_path):
        """The visible listing should contain each file in the directory."""
        for i in range(5):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 5)

        # Verify listing shows all files
        assert listing.GetItemCount() == 5
