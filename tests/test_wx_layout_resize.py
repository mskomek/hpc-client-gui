"""Delegate 7 - adaptive layout and resize verification for the wx shell."""
from __future__ import annotations

import random
import time
from collections import Counter

import pytest

wx = pytest.importorskip("wx")

from _wx_layout_resize_support import (
    _collect_required_controls,
    _find_splitters,
    _is_visible_on_screen,
    _measure_invariants,
)
from hpc_gui.core.i18n import load_language, set_language
from hpc_gui.wx_shell import create_shell_frame

METRICS = Counter()
EXECUTED: dict[str, tuple[int, int]] = {}
ZERO_INVARIANTS = (
    "negative_or_zero_control_geometry",
    "zero_sized_primary_workspace",
    "clipped_required_controls",
    "horizontal_overflow",
    "layout_exceptions",
    "detached_frames_during_resize",
)

ACCEPTANCE_SIZES = [(960, 640), (1200, 800), (1366, 768), (1440, 900), (1920, 1080)]


def _record(name: str, executed: int, required: int) -> None:
    EXECUTED[name] = (executed, required)
    assert executed >= required, f"{name}: executed {executed}, required {required}"


def _pump(app, rounds: int = 2) -> None:
    for _ in range(rounds):
        app.ProcessPendingEvents()
        wx.MilliSleep(1)
    app.ProcessPendingEvents()


def _close(app, frame, lifecycle):
    try:
        frame.Close()
    except Exception:
        pass
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.SafeYield()
        wx.MilliSleep(2)
        try:
            if lifecycle.shutdown_started:
                break
        except Exception:
            break
    for _ in range(6):
        app.ProcessPendingEvents()
        wx.SafeYield()
        wx.MilliSleep(2)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.slow
def test_wx_layout_resize():
    load_language("en")
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App(False)
    frame, lifecycle, session = create_shell_frame(app, tray_factory=lambda _parent: None)
    frame.Show()
    _pump(app, rounds=6)

    invariants = Counter({
        "negative_or_zero_control_geometry": 0,
        "zero_sized_primary_workspace": 0,
        "clipped_required_controls": 0,
        "horizontal_overflow": 0,
        "layout_exceptions": 0,
        "detached_frames_during_resize": 0,
    })
    executed = {"english": 0, "turkish": 0, "total_resize": 0, "tab_selections": 0}

    # Verify minimum size is set
    min_size = frame.GetMinSize()
    # Collect required controls - will fail loudly if renamed
    required = _collect_required_controls(frame)
    notebook = frame._wx_shell_controls["notebook"]
    baseline_windows = set(wx.GetTopLevelWindows())

    # Build deterministic resize sequence
    rng = random.Random(0)
    # min width/height for random generation
    min_w = min_size.width if min_size.width > 0 else 960
    min_h = min_size.height if min_size.height > 0 else 640
    # Ensure at least 960x640
    min_w = max(min_w, 960)
    min_h = max(min_h, 640)
    random_sizes = []
    for _ in range(195):
        w = rng.randint(min_w, 1920)
        h = rng.randint(min_h, 1080)
        random_sizes.append((w, h))
    all_sizes = ACCEPTANCE_SIZES + random_sizes
    rng.shuffle(all_sizes)
    all_sizes = all_sizes[:200]
    assert len(all_sizes) >= 200

    for size in all_sizes:
        try:
            frame.SetSize(size)
        except Exception:
            invariants["layout_exceptions"] += 1
        try:
            frame.Layout()
        except Exception:
            invariants["layout_exceptions"] += 1
        _pump(app)
        # detached frames check
        current = set(wx.GetTopLevelWindows())
        new = current - baseline_windows
        for w in new:
            try:
                if w is frame:
                    continue
                if w.IsShown():
                    # Only count if not a child of frame (detached)
                    # In wx_shell, chrome windows are parented to frame but still top-level
                    # We count any new top-level that is visible and not the shell
                    invariants["detached_frames_during_resize"] += 1
            except Exception:
                invariants["layout_exceptions"] += 1
        # select each tab in turn and measure
        for tab_idx in range(notebook.GetPageCount()):
            try:
                notebook.SetSelection(tab_idx)
                frame.Layout()
                _pump(app, rounds=2)
                executed["tab_selections"] += 1
                _measure_invariants(frame, required, invariants)
            except Exception:
                invariants["layout_exceptions"] += 1
        executed["total_resize"] += 1
    executed["english"] = executed["total_resize"]

    # Minimum size: resizes below it are clamped rather than clipping
    try:
        min_s = frame.GetMinSize()
        assert min_s.width > 0 and min_s.height > 0, "MinSize not set"
        small = (max(100, min_s.width - 60), max(100, min_s.height - 60))
        frame.SetSize(small)
        frame.Layout()
        _pump(app, rounds=4)
        actual = frame.GetSize()
        # wx may include decorations; check client size or compare with tolerance
        # The invariant is clamped: actual should not be smaller than min_s
        if actual.width < min_s.width - 2 or actual.height < min_s.height - 2:
            # Check client size instead
            # If still smaller, count as clipped
            invariants["clipped_required_controls"] += 1
        # restore
        frame.SetSize((min_w, min_h))
        frame.Layout()
        _pump(app)
    except Exception:
        invariants["layout_exceptions"] += 1
        raise

    # Translated-label growth (GUI-DPI-001): same sweep in Turkish
    try:
        set_language("tr")
        _pump(app)
        # re-collect? labels changed but controls same objects; reuse required
        rng2 = random.Random(1)
        random_sizes_tr = []
        for _ in range(195):
            w = rng2.randint(min_w, 1920)
            h = rng2.randint(min_h, 1080)
            random_sizes_tr.append((w, h))
        all_sizes_tr = ACCEPTANCE_SIZES + random_sizes_tr
        rng2.shuffle(all_sizes_tr)
        all_sizes_tr = all_sizes_tr[:200]
        for size in all_sizes_tr:
            try:
                frame.SetSize(size)
                frame.Layout()
                _pump(app)
            except Exception:
                invariants["layout_exceptions"] += 1
            for tab_idx in range(notebook.GetPageCount()):
                try:
                    notebook.SetSelection(tab_idx)
                    frame.Layout()
                    _pump(app, rounds=2)
                    executed["tab_selections"] += 1
                    _measure_invariants(frame, required, invariants)
                except Exception:
                    invariants["layout_exceptions"] += 1
            executed["total_resize"] += 1
        executed["turkish"] = 200
        set_language("en")
        _pump(app)
    except Exception:
        invariants["layout_exceptions"] += 1
        raise

    # Splitter minimums at smallest supported size (GUI-GEOMETRY-002)
    try:
        frame.SetSize((min_w, min_h))
        frame.Layout()
        _pump(app, rounds=4)
        for tab_idx in range(notebook.GetPageCount()):
            notebook.SetSelection(tab_idx)
            frame.Layout()
            _pump(app, rounds=2)
            splitters = _find_splitters(frame)
            for sp in splitters:
                try:
                    w1 = sp.GetWindow1()
                    w2 = sp.GetWindow2()
                    for w in (w1, w2):
                        if w and _is_visible_on_screen(w):
                            sz = w.GetSize()
                            if sz.width <= 0 or sz.height <= 0:
                                invariants["negative_or_zero_control_geometry"] += 1
                except Exception:
                    invariants["layout_exceptions"] += 1
    except Exception:
        invariants["layout_exceptions"] += 1

    # Record executed
    _record("resize operations (english)", executed["english"], 200)
    _record("resize operations (turkish)", executed["turkish"], 200)
    _record("total resize operations", executed["total_resize"], 400)
    _record("tab selections", executed["tab_selections"], 2800)

    # Scoreboard in same style as test_wx_file003_final_stress.py
    print("\nWX layout resize scoreboard:")
    for name, (executed_val, required_val) in EXECUTED.items():
        print(f"  {name}: {executed_val}/{required_val}")
    print("WX layout resize measured invariants:")
    for name in ZERO_INVARIANTS:
        print(f"  {name}: {METRICS[name] if METRICS[name] else invariants[name]}")
        # sync METRICS for external
        METRICS[name] = invariants[name]
    for name in ZERO_INVARIANTS:
        print(f"  {name}: {invariants[name]}")

    assert invariants["negative_or_zero_control_geometry"] == 0, f"negative_or_zero {invariants['negative_or_zero_control_geometry']}"
    assert invariants["zero_sized_primary_workspace"] == 0
    assert invariants["clipped_required_controls"] == 0, f"clipped {invariants['clipped_required_controls']}"
    assert invariants["horizontal_overflow"] == 0
    assert invariants["layout_exceptions"] == 0, f"layout_exceptions {invariants['layout_exceptions']}"
    assert invariants["detached_frames_during_resize"] == 0

    # Minimum size assertion
    assert frame.GetMinSize().width > 0 and frame.GetMinSize().height > 0

    # Cleanup: Destroy shell and SafeYield to reclaim USER objects
    _close(app, frame, lifecycle)
    try:
        for w in list(wx.GetTopLevelWindows()):
            if w:
                try:
                    w.Destroy()
                except Exception:
                    pass
        app.ProcessPendingEvents()
        wx.SafeYield()
        if owns_app:
            app.Destroy()
    except Exception:
        pass


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.regression
def test_local_files_toolbar_wraps_at_splitter_minimum(monkeypatch):
    from hpc_gui import wx_shell_layout

    monkeypatch.setattr(wx_shell_layout, "load_settings", lambda: {})
    monkeypatch.setattr(wx_shell_layout, "update_settings", lambda _patch: None)
    load_language("en")
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App(False)
    frame, lifecycle, session = create_shell_frame(
        app, tray_factory=lambda _parent: None
    )
    frame.SetSize((1355, 929))
    frame.Show()
    _pump(app, rounds=6)

    try:
        notebook = frame._wx_shell_controls["notebook"]
        files_page = frame._wx_shell_controls["pages"]["NAV-FILES"]["page"]
        page_index = next(
            index
            for index in range(notebook.GetPageCount())
            if notebook.GetPage(index) is files_page
        )
        notebook.SetSelection(page_index)
        _pump(app, rounds=4)

        splitter = session["_embedded_files_panes_splitter"]
        splitter.SetSashPosition(splitter.GetMinimumPaneSize())
        frame.Layout()
        _pump(app, rounds=4)

        local_panel = session["_embedded_local_files_panel"]
        toolbar = local_panel.GetSizer().GetItem(0).GetSizer()
        assert isinstance(toolbar, wx.WrapSizer)
        client_width = local_panel.GetClientSize().width
        assert client_width > 0
        for name in ("btn_drives", "btn_back", "btn_forward", "btn_parent", "btn_refresh"):
            button = local_panel._wx_local_controls[name]
            assert button.IsShownOnScreen(), name
            size = button.GetSize()
            position = button.GetPosition()
            assert size.width > 0 and size.height > 0, name
            assert position.x >= 0 and position.x + size.width <= client_width + 2, name
    finally:
        _close(app, frame, lifecycle)
        if owns_app:
            try:
                app.Destroy()
            except Exception:
                pass
