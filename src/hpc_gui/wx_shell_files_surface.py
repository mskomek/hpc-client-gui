"""Compose the embedded local/remote file workspace and its sync controls."""
from __future__ import annotations

import os
from pathlib import Path
from threading import Thread

from hpc_gui.services.directory_comparison import ComparableEntry, compare_directory_entries
from hpc_gui.services.synchronized_browsing import (
    SyncRoots, local_to_remote, normalize_local_root, normalize_remote_root, remote_to_local,
)
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_directories_view import build_directories_panel
from hpc_gui.wx_local_files import build_local_files_panel
from hpc_gui.wx_remote_files_view import build_remote_files_panel
from hpc_gui.wx_transfer_workspace import build_transfers_panel
from hpc_gui.wx_shell_files import _local_files_callbacks, _remote_files_callbacks
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


def build_files_surface(wx, frame, notebook, page_controls, session_state, lifecycle, t):
    # Files (header row + splitter with local left, remote right + transfers bottom)
    files_page = wx.Panel(notebook)
    files_sizer = wx.BoxSizer(wx.VERTICAL)
    # header row: Transfer type [Auto v] Effective: Binary  Synchronized browsing  Compare directories
    #                                         Upload selected  Download selected
    # Use WrapSizer so narrow windows wrap.
    files_header = wx.WrapSizer(wx.HORIZONTAL)
    transfer_type_label = wx.StaticText(files_page, label=t("ftp.transfer_type"))
    transfer_choice = wx.Choice(files_page, choices=[t("ftp.mode_auto"), t("ftp.mode_binary"), t("ftp.mode_ascii")])
    # restore from session_state if present
    try:
        saved_mode = str(session_state.get("ftp_transfer_type", "auto")).lower()
        sel_idx = {"auto": 0, "binary": 1, "ascii": 2}.get(saved_mode, 0)
        transfer_choice.SetSelection(sel_idx)
    except Exception:
        transfer_choice.SetSelection(0)
    # effective label
    def _current_effective_mode():
        try:
            idx = transfer_choice.GetSelection()
            if idx == 1:
                return t("ftp.mode_binary")
            if idx == 2:
                return t("ftp.mode_ascii")
            return t("ftp.mode_auto")
        except Exception:
            return t("ftp.mode_auto")
    effective_label = wx.StaticText(files_page, label=t("ftp.effective_type").format(mode=_current_effective_mode()))
    sync_cb = wx.CheckBox(files_page, label=t("ftp.sync_browsing"))
    # enabled even without connection for test seam; real guard inside handlers
    try:
        sync_cb.SetToolTip(t("ftp.sync_browsing"))
    except Exception:
        pass
    compare_btn = wx.Button(files_page, label=t("ftp.compare_directories"))
    compare_btn.SetToolTip(t("ftp.compare_directories_tooltip") if t("ftp.compare_directories_tooltip") != "[ftp.compare_directories_tooltip]" else "Compare directories")
    # keep enabled for seam; handlers check session/connection if needed but allow fake backends in tests
    upload_selected_btn = wx.Button(files_page, label=t("ftp.upload_selected"))
    download_selected_btn = wx.Button(files_page, label=t("ftp.download_selected"))
    files_header.Add(transfer_type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(transfer_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(effective_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(sync_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    files_header.Add(compare_btn, 0, wx.ALL, 4)
    files_header.AddStretchSpacer(1)
    files_header.Add(upload_selected_btn, 0, wx.ALL, 4)
    files_header.Add(download_selected_btn, 0, wx.ALL, 4)
    files_sizer.Add(files_header, 0, wx.EXPAND | wx.ALL, 4)
    transfer_splitter = wx.SplitterWindow(files_page)
    transfer_splitter.SetMinimumPaneSize(140)
    top_splitter = wx.SplitterWindow(transfer_splitter)
    _local = _local_files_callbacks(session_state, frame, lifecycle)
    _remote = _remote_files_callbacks(session_state, frame, lifecycle)
    local_panel = build_local_files_panel(top_splitter, **_local)
    session_state["_embedded_local_files_panel"] = local_panel
    remote_panel = build_remote_files_panel(top_splitter, **_remote)
    session_state["_embedded_remote_files_panel"] = remote_panel
    top_splitter.SplitVertically(local_panel, remote_panel, 340)
    top_splitter.SetMinimumPaneSize(300)
    # TODO-031: keep the Local/Remote split proportionally balanced on resize
    # instead of pinning the local pane to the fixed 340px initial sash.
    top_splitter.SetSashGravity(0.5)
    from hpc_gui.wx_transfer_workspace import build_transfers_panel

    transfers_panel = build_transfers_panel(transfer_splitter)
    # store for routing in _start_file_transfers
    session_state["embedded_transfers_panel"] = transfers_panel
    # Give the transfers list room for its column headers, and let a taller
    # window grow the browsers rather than the transfers area.
    transfer_splitter.SplitHorizontally(top_splitter, transfers_panel, -220)
    transfer_splitter.SetSashGravity(0.7)
    files_sizer.Add(transfer_splitter, 1, wx.EXPAND)
    files_page.SetSizer(files_sizer)
    session_state["_embedded_files_page"] = files_page
    def _on_transfer_choice(_evt):
        try:
            idx = transfer_choice.GetSelection()
            mode_key = ["auto", "binary", "ascii"][idx] if 0 <= idx < 3 else "auto"
            session_state["ftp_transfer_type"] = mode_key
            effective_label.SetLabel(t("ftp.effective_type").format(mode=_current_effective_mode()))
            files_page.Layout()
        except Exception:
            pass
    transfer_choice.Bind(wx.EVT_CHOICE, _on_transfer_choice)
    # Upload/Download selected must call same operation callbacks the remote panel toolbar already uses
    def _header_upload(_evt):
        # Same implementation the local toolbar uses; no second upload path.
        run = getattr(local_panel, "_wx_local_run_action", None)
        if callable(run):
            run("upload")

    def _header_download(_evt):
        # Same implementation the remote toolbar uses; no second download path.
        # Mirror _on_toolbar_download: forward the panel's current selection
        # plus its directory (DEF-W04-002: a bare run("download") never
        # matched run_action(action, selected, target_dir) and raised
        # TypeError on every header click, leaving a silent no-op).
        run = getattr(remote_panel, "_wx_remote_run_action", None)
        if not callable(run):
            return
        try:
            tabs = getattr(remote_panel, "_wx_remote_tabs", None) or []
            notebook = getattr(remote_panel, "_wx_remote_notebook", None)
            sel_idx = notebook.GetSelection() if notebook is not None else 0
            tstate = tabs[sel_idx] if 0 <= sel_idx < len(tabs) else (tabs[0] if tabs else None)
            if tstate is not None:
                listing = tstate.get("listing")
                entries = tstate.get("entries") or ()
                selected = tuple(
                    entry.path
                    for idx, entry in enumerate(entries)
                    if listing is not None and listing.IsSelected(idx)
                )
                run("download", selected, tstate.get("path", "/"))
                return
        except Exception:
            pass
        run("download", (), "/")

    upload_selected_btn.Bind(wx.EVT_BUTTON, _header_upload)
    download_selected_btn.Bind(wx.EVT_BUTTON, _header_download)
    notebook.AddPage(files_page, t("tabs.ftp"), False)
    page_controls["NAV-FILES"] = {"page": files_page, "local": local_panel, "remote": remote_panel, "transfers": transfers_panel, "splitter": transfer_splitter, "header": files_header, "transfer_type_label": transfer_type_label, "transfer_choice": transfer_choice, "effective_label": effective_label, "sync_cb": sync_cb, "compare_btn": compare_btn, "upload_selected": upload_selected_btn, "download_selected": download_selected_btn, "current_effective_mode": _current_effective_mode}
    # --- Sync browsing & Compare directories wiring (Wave 48) ---
    _sync_state = {"enabled": False, "roots": SyncRoots(), "guard": False, "generation": 0}
    _compare_state = {"generation": 0, "in_flight": False, "closed": False}
    # comparison visible result area (initially hidden, shown when compare active)
    _compare_result = wx.TextCtrl(files_page, style=wx.TE_READONLY | wx.TE_MULTILINE)
    _compare_result.SetMinSize(wx.Size(-1, 80))
    _compare_result.Hide()
    files_sizer.Add(_compare_result, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    # expose for tests
    files_page._sync_state = _sync_state
    files_page._compare_state = _compare_state
    files_page._compare_result = _compare_result
    def _current_local_dir() -> str:
        try:
            m = getattr(local_panel, "_wx_local_model", None) or getattr(local_panel, "_local_model", None)
            if m is not None and hasattr(m, "current_path"):
                return str(m.current_path)
            # fallback to panel attribute
            if hasattr(local_panel, "GetParent"):
                # try to read from tabs
                pass
        except Exception:
            pass
        try:
            return str(Path.cwd())
        except Exception:
            return ""
    def _current_remote_dir() -> str:
        try:
            m = getattr(remote_panel, "_wx_remote_model", None) or getattr(remote_panel, "_remote_model", None)
            # remote model current_path
            if m is not None and hasattr(m, "current_path"):
                return str(m.current_path)
        except Exception:
            pass
        return "/"
    def _do_sync_local_to_remote(local_path: str):
        if not _sync_state["enabled"] or _sync_state["guard"]:
            return
        roots = _sync_state["roots"]
        target = local_to_remote(local_path, roots)
        if target is None:
            try:
                sync_cb.SetToolTip(t("ftp.sync_outside_root"))
            except Exception:
                pass
            return
        try:
            sync_cb.SetToolTip(t("ftp.sync_browsing"))
        except Exception:
            pass
        _sync_state["guard"] = True
        try:
            # navigate remote panel if possible
            # try via host method or model
            rm = getattr(remote_panel, "_wx_remote_model", None)
            if rm is not None and hasattr(rm, "navigate"):
                try:
                    rm.navigate(target)
                except Exception:
                    # restore guard and show failure without wrong target
                    _sync_state["guard"] = False
                    return
                # also try to refresh view if available
                try:
                    if hasattr(remote_panel, "_refresh"):
                        remote_panel._refresh()
                    elif hasattr(remote_panel, "Refresh"):
                        remote_panel.Refresh()
                except Exception:
                    pass
            else:
                # fallback: set session remote path via state
                session_state["_sync_remote_target"] = target
        finally:
            _sync_state["guard"] = False
    def _do_sync_remote_to_local(remote_path: str):
        if not _sync_state["enabled"] or _sync_state["guard"]:
            return
        roots = _sync_state["roots"]
        target = remote_to_local(remote_path, roots)
        if target is None:
            try:
                sync_cb.SetToolTip(t("ftp.sync_remote_outside_root"))
            except Exception:
                pass
            return
        if not os.path.isdir(target):
            try:
                sync_cb.SetToolTip(t("ftp.sync_local_root_unavailable"))
            except Exception:
                pass
            return
        try:
            sync_cb.SetToolTip(t("ftp.sync_browsing"))
        except Exception:
            pass
        _sync_state["guard"] = True
        try:
            lm = getattr(local_panel, "_wx_local_model", None)
            if lm is not None and hasattr(lm, "navigate"):
                try:
                    lm.navigate(target)
                except Exception:
                    _sync_state["guard"] = False
                    return
                try:
                    if hasattr(local_panel, "_refresh"):
                        local_panel._refresh()
                except Exception:
                    pass
            else:
                session_state["_sync_local_target"] = target
        finally:
            _sync_state["guard"] = False
    def _on_sync_toggle(evt):
        checked = sync_cb.GetValue()
        _sync_state["enabled"] = bool(checked)
        if checked:
            # capture current dirs as roots
            try:
                local_dir = _current_local_dir()
                remote_dir = _current_remote_dir()
                # allow test injection via session_state override
                local_dir = session_state.get("_test_local_root", local_dir)
                remote_dir = session_state.get("_test_remote_root", remote_dir)
                # normalize
                local_root = normalize_local_root(local_dir) if local_dir else ""
                remote_root = normalize_remote_root(remote_dir) if remote_dir else ""
                _sync_state["roots"] = SyncRoots(local_root, remote_root)
                _sync_state["generation"] += 1
                session_state["_sync_roots"] = _sync_state["roots"]
                try:
                    sync_cb.SetToolTip(t("ftp.sync_browsing"))
                except Exception:
                    pass
            except Exception as e:
                _sync_state["enabled"] = False
                sync_cb.SetValue(False)
                try:
                    sync_cb.SetToolTip(str(e))
                except Exception:
                    pass
        else:
            _sync_state["roots"] = SyncRoots()
            try:
                sync_cb.SetToolTip(t("ftp.sync_browsing"))
            except Exception:
                pass
        evt.Skip()
    sync_cb.Bind(wx.EVT_CHECKBOX, _on_sync_toggle)
    # expose sync helpers for tests and for panel navigation hooks
    files_page._do_sync_local_to_remote = _do_sync_local_to_remote
    files_page._do_sync_remote_to_local = _do_sync_remote_to_local
    files_page._on_sync_toggle = _on_sync_toggle
    # hook local/remote panel navigation if possible by wrapping model navigate
    try:
        lm = getattr(local_panel, "_wx_local_model", None)
        if lm is not None and hasattr(lm, "navigate"):
            _orig_local_nav = lm.navigate
            def _wrapped_local_nav(path, _orig=_orig_local_nav):
                res = _orig(path)
                # after local nav, trigger sync
                try:
                    _do_sync_local_to_remote(str(path))
                except Exception:
                    pass
                return res
            lm.navigate = _wrapped_local_nav
    except Exception:
        pass
    try:
        rm = getattr(remote_panel, "_wx_remote_model", None)
        if rm is not None and hasattr(rm, "navigate"):
            _orig_remote_nav = rm.navigate
            def _wrapped_remote_nav(path, _orig=_orig_remote_nav):
                res = _orig(path)
                try:
                    _do_sync_remote_to_local(str(path))
                except Exception:
                    pass
                return res
            rm.navigate = _wrapped_remote_nav
    except Exception:
        pass
    # Compare directories wiring
    def _fetch_local_entries():
        # try via local model
        try:
            lm = getattr(local_panel, "_wx_local_model", None)
            if lm is not None and hasattr(lm, "current_path"):
                cur = Path(str(lm.current_path))
                if cur.is_dir():
                    entries = []
                    for p in cur.iterdir():
                        try:
                            st = p.stat()
                            entries.append(ComparableEntry(p.name, p.is_dir(), int(st.st_size) if p.is_file() else 0, int(st.st_mtime)))
                        except Exception:
                            entries.append(ComparableEntry(p.name, p.is_dir(), 0, 0))
                    return entries
        except Exception:
            pass
        return []
    def _fetch_remote_entries():
        # via session files or test injection
        test_entries = session_state.get("_test_remote_entries")
        if test_entries is not None:
            return list(test_entries)
        try:
            # try remote model
            rm = getattr(remote_panel, "_wx_remote_model", None)
            if rm is not None:
                # attempt to list via files service if available
                sess = session_state.get("session") or {}
                files = sess.get("files")
                if files and hasattr(files, "iterdir_entries"):
                    cur = getattr(rm, "current_path", "/")
                    raw = list(files.iterdir_entries(str(cur)))
                    entries = []
                    for r in raw:
                        # r may be dict or object with name/is_dir/size/mtime
                        if isinstance(r, dict):
                            entries.append(ComparableEntry(str(r.get("name", "")), bool(r.get("is_dir")), int(r.get("size",0)), int(r.get("mtime",0))))
                        else:
                            entries.append(ComparableEntry(str(getattr(r, "path", getattr(r, "name", ""))).rsplit("/",1)[-1], bool(getattr(r,"is_dir", False)), int(getattr(r,"size",0)), int(getattr(r,"mtime",0))))
                    return entries
        except Exception:
            pass
        return []
    def _render_compare(result):
        # visible result
        if _compare_state.get("closed"):
            return
        # check generation staleness
        # result is ComparisonResult
        try:
            lines = []
            # local statuses
            for name, status in sorted(result.local.items()):
                lines.append(f"{name}: {status.value}")
            for name, status in sorted(result.remote.items()):
                lines.append(f"{name}: {status.value} (remote)")
            if not lines:
                lines.append(t("ftp.compare_directories_tooltip") if t("ftp.compare_directories_tooltip") != "[ftp.compare_directories_tooltip]" else "No differences")
            text = "\n".join(lines)
            _compare_result.SetValue(text)
            _compare_result.Show()
            files_page.Layout()
        except Exception:
            pass
    def _on_compare(evt):
        # toggle handler for button (not checkbox)
        # we treat button as toggle: if currently showing, hide, else compute
        is_shown = _compare_result.IsShown()
        if is_shown:
            _compare_result.Hide()
            files_page.Layout()
            _compare_state["generation"] += 1
            evt.Skip()
            return
        # start compare in background
        _compare_state["generation"] += 1
        gen = _compare_state["generation"]
        _compare_state["in_flight"] = True
        _compare_result.SetValue(t("ftp.compare_directories_tooltip"))
        _compare_result.Show()
        files_page.Layout()
        def worker(current_gen=gen):
            try:
                local_entries = _fetch_local_entries()
                remote_entries = _fetch_remote_entries()
                import time
                delay = float(session_state.get("_test_compare_delay", 0))
                if delay:
                    time.sleep(delay)
                result = compare_directory_entries(local_entries, remote_entries)
                import wx as _wx
                def apply():
                    if _compare_state.get("closed") or current_gen != _compare_state.get("generation"):
                        return
                    _compare_state["in_flight"] = False
                    _render_compare(result)
                try:
                    if _wx.GetApp() is not None:
                        _wx.CallAfter(apply)
                except Exception:
                    pass
            except Exception as e:
                import wx as _wx
                def apply_err(err=e):
                    if _compare_state.get("closed") or current_gen != _compare_state.get("generation"):
                        return
                    _compare_state["in_flight"] = False
                    try:
                        _compare_result.SetValue(str(err))
                    except Exception:
                        pass
                try:
                    if _wx.GetApp() is not None:
                        _wx.CallAfter(apply_err)
                except Exception:
                    pass
        Thread(target=worker, daemon=True).start()
        evt.Skip()
    compare_btn.Bind(wx.EVT_BUTTON, _on_compare)
    files_page._compare_fetch_local = _fetch_local_entries
    files_page._compare_fetch_remote = _fetch_remote_entries
    files_page._compare_render = _render_compare
    # close handling
    def _files_close():
        _compare_state["closed"] = True
        _compare_state["generation"] += 1
    # store for shell close
    files_page._wx_files_close = _files_close
    if lifecycle is not None:
        lifecycle.register_cleanup(_files_close, worker_safe=True)

    return files_page
