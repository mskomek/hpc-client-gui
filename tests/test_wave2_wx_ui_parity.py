"""Wave 2 — wx.App UI Parity Tests.

These tests verify UI-level behavior that the model-layer tests cannot cover.
They all require wx.App and the _pump() helper pattern.
"""
# ruff: noqa
import time
from pathlib import Path
import pytest

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.gui, pytest.mark.wx]

from hpc_gui.wx_local_files import show_local_files
from hpc_gui.core.i18n import load_language, t


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
    for w in wx.GetTopLevelWindows():
        if w:
            w.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    assert not wx.GetTopLevelWindows(), "wx top-level windows must be destroyed before app teardown"
    app.Destroy()


def _local(app, path, **kwargs):
    show_local_files(path=path, **kwargs)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    return frame


def _context_action(listing, label, index=0):
    original_popup = listing.PopupMenu

    def dispatch(menu):
        item = next((item for item in menu.GetMenuItems() if item.GetItemLabelText() == label), None)
        assert item is not None, f"{label!r} action missing from context menu"
        listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))

    listing.PopupMenu = dispatch
    try:
        if index is None:
            point = listing.ClientToScreen(wx.Point(5, max(5, listing.GetSize().height - 5)))
        else:
            point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(index).y + 2))
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
        event.SetPosition(point)
        listing.ProcessEvent(event)
    finally:
        listing.PopupMenu = original_popup


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

    def test_rename_preserves_selection(self, wx_app, tmp_path, monkeypatch):
        """After renaming a file, the renamed file should be selected."""
        files = [
            "sonuç.txt",
            "ölçüm_日本語.txt",
            "standard.txt",
            "★_Favorites.txt",
            "research_İstanbul.txt",
        ]
        for name in files:
            (tmp_path / name).write_text(f"content of {name}", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == len(files))

        old_name = "ölçüm_日本語.txt"
        new_name = "yeniden_adlandır.txt"
        selected_index = next(
            index for index in range(listing.GetItemCount())
            if listing.GetItemText(index) == old_name
        )
        listing.Select(selected_index)
        assert listing.IsSelected(selected_index)
        monkeypatch.setattr(wx, "TextEntryDialog", lambda *args, **kwargs: _Dialog(new_name))

        _context_action(listing, t("dirs.rename"), selected_index)

        _pump(
            wx_app,
            lambda: any(listing.GetItemText(i) == new_name for i in range(listing.GetItemCount())),
        )
        renamed_index = next(
            index for index in range(listing.GetItemCount())
            if listing.GetItemText(index) == new_name
        )
        assert not (tmp_path / old_name).exists()
        assert (tmp_path / new_name).exists()
        assert listing.IsSelected(renamed_index), "Renamed file should remain selected in the visible listing"

    def test_invalid_rename_preserves_unicode_filename(self, wx_app, tmp_path, monkeypatch):
        """An invalid rename reports the error and preserves the visible Unicode row."""
        src = tmp_path / "日本語テスト.txt"
        src.write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        # Try to rename to empty name (should fail)
        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog(""))

        captured_errors = []

        def capture_error(msg, *args, **kwargs):
            captured_errors.append(msg)
            return wx.ID_OK

        monkeypatch.setattr(wx, "MessageBox", capture_error)

        _context_action(listing, t("dirs.rename"))

        assert captured_errors == ["Invalid name ''"]
        assert src.exists(), "File should not be renamed on error"
        assert listing.GetItemCount() == 1
        assert listing.GetItemText(0) == src.name


# ---------------------------------------------------------------------------
# Prompt 2: Context Menu Event Wiring
# ---------------------------------------------------------------------------

class TestContextMenuEventWiring:
    """Verify every context menu item has real event wiring."""

    def test_context_menu_edit_opens_editor(self, wx_app, tmp_path):
        """The Edit context-menu event hands the selected file to the editor."""
        (tmp_path / "test.txt").write_text("content", encoding="utf-8")

        opened = []
        frame = _local(wx_app, tmp_path, open_editor=opened.append)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        _context_action(listing, t("dirs.edit"))
        assert opened == [str((tmp_path / "test.txt").resolve())]

    def test_context_menu_rename_wired(self, wx_app, tmp_path, monkeypatch):
        """Rename menu item should trigger rename dialog."""
        (tmp_path / "old.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new.txt"))

        _context_action(listing, t("dirs.rename"))

        _pump(wx_app, lambda: (tmp_path / "new.txt").exists())

    def test_context_menu_copy_clipboard(self, wx_app, tmp_path):
        """Copy menu item should put file in clipboard."""
        (tmp_path / "copied.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        _context_action(listing, t("dirs.copy"))

        model = frame._wx_local_model
        assert len(model.clipboard) == 1, "Clipboard should have one item"
        assert model.clipboard[0].name == "copied.txt"
        assert model.clipboard_move is False, "Should be copy, not move"

    def test_context_menu_cut_clipboard(self, wx_app, tmp_path):
        """Cut menu item should put file in clipboard with move=True."""
        (tmp_path / "cut.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        model = frame._wx_local_model
        _context_action(listing, t("dirs.move"))

        assert len(model.clipboard) == 1, "Clipboard should have one item"
        assert model.clipboard_move is True, "Should be move (cut)"

    def test_context_menu_copy_path(self, wx_app, tmp_path):
        """Copy Path menu item should copy path to clipboard."""
        (tmp_path / "path_test.txt").write_text("content", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        listing.Select(0)

        _context_action(listing, t("dirs.copy_path"))
        data = wx.TextDataObject()
        try:
            assert wx.TheClipboard.Open()
            assert wx.TheClipboard.GetData(data)
            assert data.GetText() == str((tmp_path / "path_test.txt").resolve())
        finally:
            if wx.TheClipboard.IsOpened():
                wx.TheClipboard.Close()

    def test_background_new_folder_wired(self, wx_app, tmp_path, monkeypatch):
        """Background New Folder should create folder in current directory."""
        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() >= 0)

        monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new_unicode_フォルダ"))

        _context_action(listing, t("dirs.new_folder"), index=None)

        _pump(wx_app, lambda: (tmp_path / "new_unicode_フォルダ").is_dir())
        assert (tmp_path / "new_unicode_フォルダ").is_dir()

    def test_background_refresh_wired(self, wx_app, tmp_path):
        """Background Refresh should refresh the listing."""
        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() >= 0)

        count_before = listing.GetItemCount()

        # Add a new file
        (tmp_path / "new_file.txt").write_text("content", encoding="utf-8")

        _context_action(listing, t("dirs.refresh"), index=None)

        _pump(wx_app, lambda: listing.GetItemCount() > count_before)


# ---------------------------------------------------------------------------
# Prompt 3: Pane Labels and Roles
# ---------------------------------------------------------------------------

class TestPaneLabels:
    """Verify pane labels and roles are clear."""

    def test_local_window_title(self, wx_app, tmp_path):
        """Local browser window should have clear title."""
        frame = _local(wx_app, tmp_path)

        title = frame.GetTitle()
        assert title, "Window should have a title"
        # Title should indicate this is a local browser
        assert "local" in title.lower() or "file" in title.lower() or "dizin" in title.lower()

    def test_toolbar_buttons_are_present_and_labeled(self, wx_app, tmp_path):
        """The local browser toolbar exposes its visible controls."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        for key in ["refresh_btn", "btn_drives", "btn_back", "btn_parent"]:
            assert key in controls and controls[key], f"{key} should exist"
            assert controls[key].GetLabel().strip(), f"{key} should have a visible label"


# ---------------------------------------------------------------------------
# Prompt 4: Toolbar Alignment
# ---------------------------------------------------------------------------

class TestToolbarAlignment:
    """Verify toolbar alignment and button states."""

    def test_back_button_disabled_when_no_history(self, wx_app, tmp_path):
        """Back button should be disabled when no history."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        if "btn_back" in controls and controls["btn_back"]:
            btn_back = controls["btn_back"]
            # Initially no history, back should be disabled
            assert not btn_back.IsEnabled(), "Back button should be disabled initially"

    def test_parent_button_navigates_to_parent(self, wx_app, tmp_path):
        """The Parent toolbar button changes the path and visible listing."""
        child = tmp_path / "child"
        child.mkdir()
        (tmp_path / "parent.txt").write_text("parent", encoding="utf-8")
        frame = _local(wx_app, child)
        controls = frame._wx_local_controls
        listing = controls["listing"]
        button = controls["btn_parent"]
        assert button.IsEnabled()
        button.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
        _pump(wx_app, lambda: controls["path"].GetValue() == str(tmp_path.resolve()))
        _pump(wx_app, lambda: any(listing.GetItemText(i) == "parent.txt" for i in range(listing.GetItemCount())))

    def test_refresh_button_always_enabled(self, wx_app, tmp_path):
        """Refresh button should always be enabled."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        assert controls["refresh_btn"].IsEnabled(), "Refresh button should be enabled"


# ---------------------------------------------------------------------------
# Prompt 5: Text Field Labels
# ---------------------------------------------------------------------------

class TestTextFieldLabels:
    """Verify text fields have clear labels."""

    def test_path_bar_exists(self, wx_app, tmp_path):
        """Path bar should exist and show current directory."""
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls

        assert "path" in controls
        assert controls["path"].GetValue() == str(tmp_path.resolve())

    def test_path_bar_editable(self, wx_app, tmp_path):
        """Entering a path navigates the visible browser."""
        child = tmp_path / "child"
        child.mkdir()
        (child / "inside.txt").write_text("inside", encoding="utf-8")
        frame = _local(wx_app, tmp_path)
        controls = frame._wx_local_controls
        path_ctrl = controls["path"]
        assert path_ctrl.IsEditable()
        path_ctrl.SetValue(str(child))
        path_ctrl.ProcessEvent(wx.CommandEvent(wx.wxEVT_TEXT_ENTER, path_ctrl.GetId()))
        listing = controls["listing"]
        _pump(wx_app, lambda: path_ctrl.GetValue() == str(child.resolve()))
        _pump(wx_app, lambda: listing.GetItemCount() == 1)
        assert listing.GetItemText(0) == "inside.txt"


# ---------------------------------------------------------------------------
# Prompt 6: Status/Progress Feedback
# ---------------------------------------------------------------------------

class TestDirectoryListing:
    """Verify the visible file listing reflects the current directory."""

    def test_listing_displays_all_files(self, wx_app, tmp_path):
        """The visible listing contains every file in the current directory."""
        for i in range(5):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}", encoding="utf-8")

        frame = _local(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: listing.GetItemCount() == 5)

        assert {listing.GetItemText(index) for index in range(listing.GetItemCount())} == {
            f"file_{i}.txt" for i in range(5)
        }
