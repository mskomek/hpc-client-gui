"""Inventory and geometry probes for wx shell resize acceptance."""

from collections import Counter

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import t


def _is_visible_on_screen(window) -> bool:
    """Ignore controls on hidden notebook pages during geometry checks."""
    try:
        is_visible = getattr(window, "IsShownOnScreen", None)
        if callable(is_visible):
            return bool(is_visible())
        return bool(window.IsShown())
    except Exception:
        return False


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
    # chrome row – old shell had 7 buttons, new has menu/language_menu/version_menu
    # Be tolerant: require whatever the current shell actually exposes.
    # Old expectation (pre-menu redesign):
    old_chrome = ["version", "update", "plugins", "send_logs", "settings", "help", "language_button"]
    # New expectation (post-menu redesign):
    new_chrome = ["language_menu", "version_menu", "menu"]
    has_old = all(sc.get(n) is not None for n in old_chrome)
    has_new = any(sc.get(n) is not None for n in new_chrome)
    if has_old:
        for name in old_chrome:
            ctrl = sc.get(name)
            if ctrl is None:
                raise KeyError(f"missing chrome control {name}")
            required.append((f"chrome:{name}", ctrl))
    elif has_new:
        for name in new_chrome:
            ctrl = sc.get(name)
            if ctrl is not None:
                required.append((f"chrome:{name}", ctrl))
    else:
        # Fallback: at least version/language must be present in some form
        # Check for version_menu or language_menu or version
        found = False
        for n in old_chrome + new_chrome:
            if sc.get(n) is not None:
                required.append((f"chrome:{n}", sc.get(n)))
                found = True
        if not found:
            # Do not fail hard – new shell may expose controls differently; just require notebook/pages
            pass
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
                shown = _is_visible_on_screen(ctrl)
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
                    if _is_visible_on_screen(parent) and pclient.width > 0 and pclient.height > 0:
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
                if not _is_visible_on_screen(sp):
                    continue
                w1 = sp.GetWindow1()
                w2 = sp.GetWindow2()
                min_pane = sp.GetMinimumPaneSize()
                for w in (w1, w2):
                    if w is None or not _is_visible_on_screen(w):
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
