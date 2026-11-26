"""Startup changelog and small-screen contracts on the V2 wx runtime."""
from __future__ import annotations

import pytest

from hpc_gui import __version__
from hpc_gui.services.changelog import chronological_changelog
from hpc_gui.wx_shell_sizing import shell_sizes
from hpc_gui.wx_startup_notices import show_startup_notices


@pytest.mark.unit
@pytest.mark.semantic
@pytest.mark.resource
def test_main_window_fits_small_screen():
    class Display:
        def GetClientArea(self):
            return type("Area", (), {"width": 800, "height": 600})()

    class Wx:
        def Display(self, _index):
            return Display()

    default, minimum = shell_sizes(Wx())
    assert default == (800, 600)
    assert minimum == (800, 600)
    # V2 clamps to the available desktop, rather than the Qt-specific margins.


@pytest.mark.unit
@pytest.mark.semantic
def test_changelog_sections_are_rendered_newest_first():
    text = "# Changelog\n\n## v1.1.0\n- newest\n\n## v1.0.0\n- oldest"
    rendered = chronological_changelog(text)
    assert rendered.index("## v1.1.0") < rendered.index("## v1.0.0")


@pytest.mark.unit
@pytest.mark.semantic
def test_startup_changelog_is_shown_once_per_version(monkeypatch, tmp_path):
    from hpc_gui.config.storage import (
        get_last_seen_changelog_version, set_ui_pref_bool,
    )
    import hpc_gui.wx_startup_notices as notices

    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path))
    set_ui_pref_bool("show_welcome", False)
    monkeypatch.setattr(notices, "load_changelog_text",
                        lambda: "# Changelog\n\n## v1.1.1\n- new\n\n## v1.1.0\n- old")

    class Owner:
        def IsBeingDeleted(self):
            return False

    shown = []

    def present(parent, title, text, **kwargs):
        shown.append(text)
        return False

    owner = Owner()
    show_startup_notices(owner, present=present)
    show_startup_notices(owner, present=present)
    assert len(shown) == 1
    assert shown[0].index("## v1.1.1") < shown[0].index("## v1.1.0")
    assert get_last_seen_changelog_version() == __version__
