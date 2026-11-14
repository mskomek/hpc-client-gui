from __future__ import annotations

import time

import pytest
import wx

from hpc_gui.core.i18n import load_language
from hpc_gui.plugin_engines.openfoam_lint.wx_page import create_wx_page


@pytest.fixture
def linter_app():
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="OpenFOAM Linter test")
    frame.Show()
    yield app, frame
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Close()
    for _ in range(3):
        app.ProcessPendingEvents()
        wx.Yield()
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Destroy()
    app.ProcessPendingEvents()
    wx.Yield()
    assert not wx.GetTopLevelWindows(), "wx top-level windows survived fixture teardown"
    app.Destroy()


def test_linter_wx_page_opens_with_supported_controls(linter_app):
    _app, frame = linter_app
    page = create_wx_page(frame)
    controller = page._hpc_trusted_tool_controller

    assert page.GetParent() is frame
    assert controller.edition.GetStringSelection() == "OpenFOAM.com / ESI"
    assert not controller.edition.IsEnabled()
    assert controller.version.GetCount() >= 1
    assert controller.run.IsEnabled()
    assert controller.cancel.IsEnabled() is False
    assert controller.rules.GetCount() > 0


def test_linter_wx_page_lists_every_rule_added_for_this_wave(linter_app):
    _app, frame = linter_app
    page = create_wx_page(frame)
    controller = page._hpc_trusted_tool_controller
    entries = [controller.rules.GetString(i) for i in range(controller.rules.GetCount())]

    for rule_id in (
        "OF-SEC-005",
        "OF-NUM-010",
        "OF-MESH-010",
        "OF-CROSS-005",
        "OF-CROSS-006",
        "OF-SOLVER-010",
    ):
        assert any(entry.startswith(rule_id) for entry in entries), rule_id


def test_linter_wx_page_runs_and_marks_changed_results_stale(linter_app, tmp_path):
    app, frame = linter_app
    case = tmp_path / "case"
    system = case / "system"
    system.mkdir(parents=True)
    control = system / "controlDict"
    control.write_text("application simpleFoam;\n", encoding="utf-8")
    page = create_wx_page(frame, initial_paths=[case])
    controller = page._hpc_trusted_tool_controller

    controller._run_lint(None)
    deadline = time.monotonic() + 5
    while controller.result is None and time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.MilliSleep(10)
    app.ProcessPendingEvents()

    assert controller.result is not None
    assert controller.export.IsEnabled()
    assert controller.diagnostics.GetItemCount() > 0
    assert controller.result.files_checked

    control.write_text("application pimpleFoam;\n", encoding="utf-8")
    controller._check_stale(None)

    assert controller._stale is True
    assert controller.export.IsEnabled() is False


def _reacting_case(root):
    """Minimal reactingFoam case used by the wx page check."""
    import os

    (root / "system").mkdir(parents=True)
    (root / "system" / "controlDict").write_text("application reactingFoam\n", encoding="utf-8")
    (root / "constant").mkdir(parents=True)
    (root / "constant" / "thermophysicalProperties").write_text(
        "thermoType { type hePsiThermo; mixture reactingMixture; }\n", encoding="utf-8"
    )
    (root / "constant" / "reactions").write_text(
        "species ( CH4 O2 N2 );\nreactions { }\n", encoding="utf-8"
    )
    (root / "constant" / "turbulenceProperties").write_text("simulationType laminar;\n", encoding="utf-8")
    zero = root / "0"
    zero.mkdir()
    for field in ("U", "p", "T", "CH4", "O2", "N2"):
        (zero / field).write_text("dimensions [0 0 0 0 0 0 0];\n", encoding="utf-8")
    surface = root / "constant" / "triSurface" / "body.stl"
    surface.parent.mkdir()
    surface.write_text("solid body\n", encoding="utf-8")
    points = root / "constant" / "polyMesh" / "points"
    points.parent.mkdir()
    points.write_text("0\n", encoding="utf-8")
    os.utime(surface, (2_000_000_000, 2_000_000_000))
    os.utime(points, (1_900_000_000, 1_900_000_000))
    return root


def test_linter_wx_page_runs_the_reacting_case(linter_app, tmp_path):
    app, frame = linter_app
    case = _reacting_case(tmp_path / "reacting")
    page = create_wx_page(frame, initial_paths=[case])
    controller = page._hpc_trusted_tool_controller

    controller._run_lint(None)
    deadline = time.monotonic() + 5
    while controller.result is None and time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.MilliSleep(10)
    app.ProcessPendingEvents()

    assert controller.result is not None
    rules = {
        controller.diagnostics.GetItem(index, 2).GetText()
        for index in range(controller.diagnostics.GetItemCount())
    }
    assert "OF-CROSS-006" in rules
    assert "OF-SOLVER-010" not in rules

