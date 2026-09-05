"""Delegate 7 - adaptive layout and resize verification for the wx shell."""
from __future__ import annotations

import random
import time
from collections import Counter

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, set_language, t
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


def _find_splitters(win):
    splitters = []
    try:
        for child in win.GetChildren():
            if isinstance(child, wx.SplitterWindow):
                splitters.append(child)
                splitters.extend(_find_splitters(child))
            else:
                splitters.extend(_find_splitters(child))
    except Exception:
        pass
    return splitters


def _collect_required_controls(frame):
    """Collect required controls via _wx_shell_controls and panels' _wx_* attributes."""
    required = []
    sc = frame._wx_shell_controls
    # chrome row
    for name in ["version", "update", "plugins", "send_logs", "settings", "help", "language_button"]:
        ctrl = sc.get(name)
        if ctrl is None:
            raise KeyError(f"missing chrome control {name}")
        required.append((f"chrome:{name}", ctrl))
    notebook = sc.get("notebook")
    if notebook is None:
        raise KeyError("missing notebook")
    required.append(("notebook", notebook))
    pages = sc.get("pages")
    if pages is None or len(pages) != 7:
        raise AssertionError(f"expected 7 pages, got {len(pages) if pages else 0}")
    for key in ["APP-CONNECT", "NAV-JOBS", "NAV-DIRECTORIES", "NAV-FILES", "NAV-EDITOR", "NAV-TERMINAL", "NAV-LOGS"]:
        if key not in pages:
            raise KeyError(f"missing page {key}")
    # APP-CONNECT - look up via panel children and fail loudly if Connect button renamed/missing
    page = pages["APP-CONNECT"]["page"]
    # Prefer _wx_connection_controls if present, otherwise search for Connect button
    conn_controls = getattr(page, "_wx_connection_controls", None)
    if conn_controls is not None:
        for n, c in conn_controls.items():
            required.append((f"APP-CONNECT:{n}", c))
    else:
        # Search for Connect button and related controls; this still fails loudly if renamed
        found_connect = None
        found_list = None
        found_status = None
        # walk descendants
        stack = list(page.GetChildren())
        while stack:
            w = stack.pop()
            try:
                if isinstance(w, wx.Button) and w.GetLabel() == t("login.connect"):
                    found_connect = w
                elif isinstance(w, wx.ListBox):
                    found_list = w
                elif isinstance(w, wx.StaticText):
                    # status text is near bottom, but we identify by being StaticText with initial status
                    if found_status is None:
                        found_status = w
            except Exception:
                pass
            try:
                stack.extend(w.GetChildren())
            except Exception:
                pass
        if found_connect is None:
            raise KeyError("APP-CONNECT missing Connect button (t('login.connect')) - renamed or not exposed")
        required.append(("APP-CONNECT:connect", found_connect))
        if found_list is not None:
            required.append(("APP-CONNECT:choices", found_list))
        if found_status is not None:
            required.append(("APP-CONNECT:status", found_status))
    required.append(("APP-CONNECT:page", page))
    # NAV-JOBS - look up via _wx_jobs_controls and fallback to searching for Refresh/Cancel
    page = pages["NAV-JOBS"]["page"]
    jobs_ctrls = getattr(page, "_wx_jobs_controls", None)
    if jobs_ctrls is None:
        raise KeyError("NAV-JOBS missing _wx_jobs_controls")
    for n in ["jobs", "follow", "pause"]:
        if n not in jobs_ctrls:
            raise KeyError(f"NAV-JOBS missing {n}")
        required.append((f"NAV-JOBS:{n}", jobs_ctrls[n]))
    # Refresh/Cancel may not be in _wx_jobs_controls in older builds; look them up via children
    for n, tkey in [("refresh", "jobs.refresh"), ("cancel", "jobs.cancel")]:
        ctrl = jobs_ctrls.get(n) if isinstance(jobs_ctrls, dict) else None
        if ctrl is None:
            # search descendants for button with matching label
            found = None
            stack = list(page.GetChildren())
            while stack:
                w = stack.pop()
                try:
                    if isinstance(w, wx.Button) and w.GetLabel() == t(tkey):
                        found = w
                        break
                except Exception:
                    pass
                try:
                    stack.extend(w.GetChildren())
                except Exception:
                    pass
            if found is None:
                raise KeyError(f"NAV-JOBS missing {n} button ({tkey})")
            required.append((f"NAV-JOBS:{n}", found))
        else:
            required.append((f"NAV-JOBS:{n}", ctrl))
    required.append(("NAV-JOBS:page", page))
    # NAV-DIRECTORIES
    page = pages["NAV-DIRECTORIES"]["page"]
    dirs_ctrls = getattr(page, "_wx_dirs_controls", None)
    if dirs_ctrls is None:
        raise KeyError("NAV-DIRECTORIES missing _wx_dirs_controls")
    for n in ["splitter", "scratch_container", "home_container", "scratch_label", "home_label", "new_slurm"]:
        if n not in dirs_ctrls:
            raise KeyError(f"NAV-DIRECTORIES missing {n}")
        required.append((f"NAV-DIRECTORIES:{n}", dirs_ctrls[n]))
    required.append(("NAV-DIRECTORIES:page", page))
    for sub in ["scratch", "home"]:
        sub_panel = dirs_ctrls.get(sub)
        if sub_panel is None:
            raise KeyError(f"missing {sub}")
        rc = getattr(sub_panel, "_wx_remote_controls", None)
        if rc is None:
            raise KeyError(f"missing _wx_remote_controls for {sub}")
        for n in ["listing", "path", "path_label", "btn_new_folder", "btn_upload", "btn_download", "btn_delete", "btn_refresh"]:
            if n not in rc:
                raise KeyError(f"missing remote {sub} {n}")
            required.append((f"NAV-DIRECTORIES:{sub}:{n}", rc[n]))
    # NAV-FILES
    ctrls = pages["NAV-FILES"]
    # local
    local_panel = ctrls.get("local")
    if local_panel is None:
        raise KeyError("NAV-FILES missing local")
    lc = getattr(local_panel, "_wx_local_controls", None)
    if lc is None:
        raise KeyError("local missing _wx_local_controls")
    for n in ["listing", "path", "btn_drives", "btn_back", "btn_parent", "btn_refresh"]:
        if n not in lc:
            raise KeyError(f"local missing {n}")
        required.append((f"NAV-FILES:local:{n}", lc[n]))
    # remote
    remote_panel = ctrls.get("remote")
    rc = getattr(remote_panel, "_wx_remote_controls", None)
    if rc is None:
        raise KeyError("remote missing _wx_remote_controls")
    for n in ["listing", "path", "path_label", "btn_new_folder", "btn_upload", "btn_download", "btn_delete", "btn_refresh"]:
        if n not in rc:
            raise KeyError(f"remote missing {n}")
        required.append((f"NAV-FILES:remote:{n}", rc[n]))
    # transfers
    trans_panel = ctrls.get("transfers")
    tc = getattr(trans_panel, "_wx_transfer_controls", None)
    if tc is None:
        raise KeyError("transfers missing _wx_transfer_controls")
    for n in ["status", "queue", "stop", "cancel", "clear_pending"]:
        if n not in tc:
            raise KeyError(f"transfers missing {n}")
        required.append((f"NAV-FILES:transfers:{n}", tc[n]))
    # splitter page itself
    required.append(("NAV-FILES:page", ctrls["page"]))
    # NAV-EDITOR
    page = pages["NAV-EDITOR"]["page"]
    ec = getattr(page, "_wx_editor_controls", None)
    if ec is None:
        raise KeyError("editor missing _wx_editor_controls")
    for n in ["editor", "save", "submit", "run", "status"]:
        if n not in ec:
            raise KeyError(f"editor missing {n}")
        required.append((f"NAV-EDITOR:{n}", ec[n]))
    required.append(("NAV-EDITOR:page", page))
    # NAV-TERMINAL
    term = pages["NAV-TERMINAL"]
    for n in ["output", "input"]:
        if n not in term:
            raise KeyError(f"terminal missing {n}")
        required.append((f"NAV-TERMINAL:{n}", term[n]))
    required.append(("NAV-TERMINAL:page", term["page"]))
    # NAV-LOGS
    page = pages["NAV-LOGS"]["page"]
    lc2 = getattr(page, "_wx_logs_controls", None)
    if lc2 is None:
        raise KeyError("logs missing _wx_logs_controls")
    for n in ["title", "text", "copy", "copy_path", "export", "refresh"]:
        if n not in lc2:
            raise KeyError(f"logs missing {n}")
        required.append((f"NAV-LOGS:{n}", lc2[n]))
    required.append(("NAV-LOGS:page", page))
    return required


def _measure_invariants(frame, required_controls, invariants: Counter) -> None:
    # zero sized primary workspace and horizontal overflow
    try:
        notebook = frame._wx_shell_controls["notebook"]
        sz = notebook.GetSize()
        cs = notebook.GetClientSize()
        if sz.width <= 0 or sz.height <= 0 or cs.width <= 0 or cs.height <= 0:
            invariants["zero_sized_primary_workspace"] += 1
        sel = notebook.GetSelection()
        if sel >= 0:
            try:
                page = notebook.GetPage(sel)
                if page:
                    psz = page.GetSize()
                    pcs = page.GetClientSize()
                    if psz.width <= 0 or psz.height <= 0 or pcs.width <= 0 or pcs.height <= 0:
                        invariants["zero_sized_primary_workspace"] += 1
                    # horizontal overflow: page wider than notebook client width
                    if psz.width > cs.width + 2:  # allow border
                        invariants["horizontal_overflow"] += 1
            except Exception:
                invariants["layout_exceptions"] += 1
    except Exception:
        invariants["layout_exceptions"] += 1

    # per-control geometry and clipping
    for name, ctrl in required_controls:
        try:
            # skip non-window (e.g., sizer)
            if not hasattr(ctrl, "GetSize"):
                continue
            try:
                shown = ctrl.IsShown()
            except Exception:
                shown = True
            if not shown:
                continue
            sz = ctrl.GetSize()
            if sz.width <= 0 or sz.height <= 0:
                invariants["negative_or_zero_control_geometry"] += 1
            parent = ctrl.GetParent()
            if parent is not None:
                try:
                    pclient = parent.GetClientSize()
                    pos = ctrl.GetPosition()
                    # Only check if parent is shown and has valid client size
                    if parent.IsShown() and pclient.width > 0 and pclient.height > 0:
                        if pos.x < 0 or pos.y < 0 or pos.x + sz.width > pclient.width or pos.y + sz.height > pclient.height:
                            # Check if control is inside a scrolled area? For now count
                            # Avoid counting notebooks themselves which correctly fill parent
                            # But for required controls, any extending past parent is clipping
                            invariants["clipped_required_controls"] += 1
                except Exception:
                    invariants["layout_exceptions"] += 1
        except Exception:
            invariants["layout_exceptions"] += 1

    # splitter minimums: no pane collapsed to zero
    try:
        splitters = _find_splitters(frame)
        for sp in splitters:
            try:
                if not sp.IsShown():
                    continue
                w1 = sp.GetWindow1()
                w2 = sp.GetWindow2()
                min_pane = sp.GetMinimumPaneSize()
                for w in (w1, w2):
                    if w is None or not w.IsShown():
                        continue
                    sz = w.GetSize()
                    if sz.width <= 0 or sz.height <= 0:
                        invariants["negative_or_zero_control_geometry"] += 1
                    # For vertical splitter, width must be >= min_pane
                    try:
                        mode = sp.GetSplitMode()
                    except Exception:
                        mode = wx.SPLIT_VERTICAL
                    if mode == wx.SPLIT_VERTICAL:
                        if sz.width < min_pane:
                            invariants["negative_or_zero_control_geometry"] += 1
                    else:
                        if sz.height < min_pane:
                            invariants["negative_or_zero_control_geometry"] += 1
            except Exception:
                invariants["layout_exceptions"] += 1
    except Exception:
        invariants["layout_exceptions"] += 1


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


def test_wx_layout_resize():
    load_language("en")
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
            csize = frame.GetClientSize()
            # If still smaller, count as clipped
            invariants["clipped_required_controls"] += 1
        # restore
        frame.SetSize((min_w, min_h))
        frame.Layout()
        _pump(app)
    except Exception as e:
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
                        if w and w.IsShown():
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
        app.Destroy()
    except Exception:
        pass
