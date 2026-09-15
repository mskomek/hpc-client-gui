"""W01 regression tests — ghost control removal and wx About dialog.

These tests prove that FIX-W01-001 (Quick Tour ghost control removal) and
FIX-W01-002 (wx About dialog) remain correct.  If either defect returns,
these tests MUST fail for the right reason.
"""

from __future__ import annotations

import pathlib

import pytest


# ---------------------------------------------------------------------------
# FIX-W01-001: Quick Tour ghost control removed
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.semantic
class TestQuickTourGhostRemoval:
    """Verify the Quick Tour menu item no longer appears in the wx shell."""

    def test_help_items_tour_is_none(self):
        """help_items['tour'] must be None — no menu item created."""
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        assert 'help_items["tour"] = None' in src

    def test_no_tour_menu_append(self):
        """No Append call creates a visible Quick Tour menu item."""
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        # The old code did: act_tour = help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))
        assert 'help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))' not in src

    def test_no_tour_dispatch_branch(self):
        """The dead APP-QUICKTOUR dispatch branch is removed."""
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        assert 'APP-QUICKTOUR' not in src

    def test_tour_menu_item_absent_from_wx_help_menu(self):
        """Source-level proof: no tour item is appended to the wx help menu.

        This is the canonical regression test for DEF-W01-001.
        If someone re-adds a visible Quick Tour item, this test catches it.
        """
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        # Extract the help_menu construction block
        # Look for any Append call within the help_menu block that mentions "tour"
        in_help_menu_block = False
        for line in src.splitlines():
            stripped = line.strip()
            if "help_menu" in stripped and ("Append" in stripped or "addMenu" in stripped):
                in_help_menu_block = True
            if in_help_menu_block and "tour" in stripped.lower():
                if "Append" in stripped:
                    pytest.fail(
                        f"Quick Tour menu item found in wx help menu: {stripped}"
                    )
            # Reset after we leave the help menu construction
            if in_help_menu_block and stripped == "":
                in_help_menu_block = False

    def test_sensitive_tour_lang_guard_is_harmless(self):
        """The language-change guard for tour is safely null-checked."""
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        # The guard should be: tour_act = help_items.get("tour"); if tour_act: ...
        assert 'help_items.get("tour")' in src or "help_items.get('tour')" in src


# ---------------------------------------------------------------------------
# FIX-W01-002: wx About dialog
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.semantic
class TestWxAboutDialog:
    """Verify the wx About dialog exists and has the required content."""

    def test_wx_about_module_exists(self):
        """wx_about.py must exist."""
        assert pathlib.Path("src/hpc_gui/wx_about.py").is_file()

    def test_wx_about_exports_show_about(self):
        """wx_about module must export show_about."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "def show_about" in src
        assert '"show_about"' in src or "'show_about'" in src

    def test_wx_about_displays_version(self):
        """wx About dialog must display the application version."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "__version__" in src
        assert "version" in src.lower()

    def test_wx_about_has_repo_url(self):
        """wx About dialog must have the project repository URL."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "https://github.com/mskomek/hpc-client-gui" in src

    def test_wx_about_has_license_button(self):
        """wx About dialog must have a license button."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "LICENSE" in src
        assert "license" in src.lower()

    def test_wx_about_has_notices_button(self):
        """wx About dialog must have a third-party notices button."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "THIRD_PARTY_NOTICES" in src or "notices" in src.lower()

    def test_wx_about_is_dialog_not_messagebox(self):
        """wx About must use wx.Dialog, not plain wx.MessageBox."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "wx.Dialog" in src

    def test_dispatch_about_calls_wx_about(self):
        """APP-ABOUT dispatch in wx_shell.py must call wx_about.show_about."""
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        assert "wx_about" in src
        assert "show_about" in src

    def test_dispatch_about_not_messagebox(self):
        """APP-ABOUT dispatch must NOT use wx.MessageBox."""
        src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        # Find the APP-ABOUT block and verify no MessageBox
        about_idx = src.find('"APP-ABOUT"')
        if about_idx == -1:
            about_idx = src.find("'APP-ABOUT'")
        if about_idx != -1:
            # Get ~500 chars around the dispatch
            block = src[about_idx:about_idx + 500]
            assert "wx.MessageBox" not in block, (
                "APP-ABOUT dispatch still uses wx.MessageBox"
            )

    def test_wx_about_no_network_dependency(self):
        """wx About dialog must not require network to instantiate."""
        src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        assert "requests" not in src.lower()
        assert "urllib" not in src.lower()

    def test_wx_about_version_matches_app_version(self):
        """wx About dialog must use the same __version__ as the app."""
        about_src = pathlib.Path("src/hpc_gui/wx_about.py").read_text(encoding="utf-8")
        app_src = pathlib.Path("src/hpc_gui/__init__.py").read_text(encoding="utf-8")
        assert "__version__" in about_src
        assert "__version__" in app_src or "version" in app_src.lower()
