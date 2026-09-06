"""wx startup splash per spec §18-29 — 760×560, stages, progress, log, connection controls."""

from __future__ import annotations

from threading import Thread
from typing import Callable

from hpc_gui import __version__
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change


STAGES = ("preferences", "helpers", "updates", "session")
STAGE_LABELS = {
    "preferences": "Preferences",
    "helpers": "Helpers",
    "updates": "Updates",
    "session": "Session",
}

# Visual states for each stage — spec §22
STATE_PENDING = "pending"   # ○
STATE_ACTIVE = "active"     # ● / spinner
STATE_COMPLETE = "complete" # ✓
STATE_FAILED = "failed"     # !


def _stage_icon(state: str) -> str:
    return {"pending": "○", "active": "●", "complete": "✓", "failed": "!"} .get(state, "○")


def create_startup_splash(parent=None, *, profiles: list[dict] | None = None, lifecycle=None, on_connect=None, on_offline=None, on_reload=None):
    """Create and show the startup splash dialog (spec §18-29). Returns the dialog instance.

    The dialog is modeless and centered; caller controls stage progression via the
    returned object's public methods.
    """
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    profiles = list(profiles or [])
    # Spec §19: 760×560 recommended, min 700×500, centered, not maximized
    dlg = wx.Dialog(parent, title="HPC Client", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    dlg.SetMinSize(wx.Size(700, 500))
    dlg.SetSize(wx.Size(760, 560))
    try:
        dlg.CentreOnScreen()
    except Exception:
        try:
            dlg.Centre()
        except Exception:
            pass

    panel = wx.Panel(dlg)
    root = wx.BoxSizer(wx.VERTICAL)

    # --- Branding §21: top area HPC Client / Starting application..., logo max 64-80px (~20% height) ---
    brand_title = wx.StaticText(panel, label="HPC Client")
    try:
        fnt = brand_title.GetFont()
        fnt.SetPointSize(16)
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        brand_title.SetFont(fnt)
    except Exception:
        pass
    brand_sub = wx.StaticText(panel, label=t("splash.starting") if t("splash.starting") != "[splash.starting]" else "Starting application...")
    try:
        brand_sub.SetForegroundColour(wx.Colour(90, 90, 90))
    except Exception:
        pass
    root.Add(brand_title, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 16)
    root.Add(brand_sub, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 12)

    # --- Stage indicators §22: Preferences Helpers Updates Session with ○/●/✓/! ---
    stage_sizer = wx.BoxSizer(wx.HORIZONTAL)
    stage_controls: dict[str, wx.StaticText] = {}
    for sid in STAGES:
        # Use label keys if available, else fallback
        label_key = f"splash.stage_{sid}"
        lbl = t(label_key) if t(label_key) != f"[{label_key}]" else STAGE_LABELS[sid]
        st = wx.StaticText(panel, label=f"{_stage_icon(STATE_PENDING)}  {lbl}")
        try:
            st.SetMinSize(wx.Size(110, -1))
        except Exception:
            pass
        stage_controls[sid] = st
        # 8px standard spacing between related controls per §4
        stage_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    root.Add(stage_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 8)

    # --- Progress bar §23: single bar below stages ---
    gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
    gauge.SetMinSize(wx.Size(-1, 12))
    gauge.SetValue(0)
    root.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    # --- Current status §24: one line below progress ---
    status_text = wx.StaticText(panel, label=t("splash.loading_preferences") if t("splash.loading_preferences") != "[splash.loading_preferences]" else "Loading preferences...")
    root.Add(status_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    # --- Diagnostic log §25: 180-220px monospace, auto-scroll at bottom ---
    log_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_RICH2)
    log_ctrl.SetMinSize(wx.Size(-1, 200))
    try:
        fnt = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        log_ctrl.SetFont(fnt)
    except Exception:
        pass
    # Initial height 200 within 180-220
    root.Add(log_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    # --- Connection controls §26: Profile dropdown + Reload / Continue Offline / Connect ---
    conn_box = wx.StaticBox(panel, label=t("connection.profile") if t("connection.profile") != "[connection.profile]" else "Profile")
    conn_sizer = wx.StaticBoxSizer(conn_box, wx.VERTICAL)
    # Profile selector: min 320 preferred 400-500, not full-width on wide monitor
    try:
        choices = [str(p.get("name", "")) for p in profiles if p.get("name")]
    except Exception:
        choices = []
    if not choices:
        choices = [t("connection.no_profiles") if t("connection.no_profiles") != "[connection.no_profiles]" else "No profiles"]
    profile_choice = wx.Choice(conn_box, choices=choices)
    try:
        profile_choice.SetMinSize(wx.Size(320, -1))
        profile_choice.SetSelection(0 if choices else -1)
    except Exception:
        pass
    # Second row of buttons with hierarchy §26: Connect Primary, Reload Secondary, Continue Tertiary
    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    reload_btn = wx.Button(conn_box, label=t("connection.reload") if t("connection.reload") != "[connection.reload]" else "Reload Connections")
    try:
        reload_btn.SetMinSize(wx.Size(88, 30))
    except Exception:
        pass
    offline_btn = wx.Button(conn_box, label=t("connection.continue_offline") if t("connection.continue_offline") != "[connection.continue_offline]" else "Continue Offline")
    try:
        offline_btn.SetMinSize(wx.Size(88, 30))
    except Exception:
        pass
    connect_btn = wx.Button(conn_box, label=t("login.connect_selected") if t("login.connect_selected") != "[login.connect_selected]" else "Connect")
    try:
        connect_btn.SetMinSize(wx.Size(100, 32))
        # Primary styling: bold
        fnt = connect_btn.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        connect_btn.SetFont(fnt)
    except Exception:
        pass
    try:
        connect_btn.SetDefault()
    except Exception:
        pass
    # Spec places Profile dropdown centered, then row below with Reload on left, Continue/Connect right?
    # Layout per spec: Profile [dropdown] / [Reload]  [Continue Offline] [Connect] (last two right-aligned)
    conn_sizer.Add(profile_choice, 0, wx.EXPAND | wx.ALL, 8)
    btn_row.Add(reload_btn, 0, wx.RIGHT, 8)
    btn_row.AddStretchSpacer(1)
    btn_row.Add(offline_btn, 0, wx.RIGHT, 8)
    btn_row.Add(connect_btn, 0)
    conn_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
    root.Add(conn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    # --- Mandatory update banner §29 (hidden initially) ---
    mandatory_panel = wx.Panel(panel)
    mand_sizer = wx.BoxSizer(wx.VERTICAL)
    mand_text = wx.StaticText(mandatory_panel, label=t("updates.mandatory_message") if t("updates.mandatory_message") != "[updates.mandatory_message]" else "A required update is available.")
    mand_detail = wx.StaticText(mandatory_panel, label="")
    mand_btn_row = wx.BoxSizer(wx.HORIZONTAL)
    mand_view = wx.Button(mandatory_panel, label=t("common.details") if t("common.details") != "[common.details]" else "View Details")
    mand_update = wx.Button(mandatory_panel, label=t("updates.update_now") if t("updates.update_now") != "[updates.update_now]" else "Update Now")
    try:
        mand_update.SetMinSize(wx.Size(100, 32))
        fnt = mand_update.GetFont()
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        mand_update.SetFont(fnt)
    except Exception:
        pass
    mand_btn_row.AddStretchSpacer(1)
    mand_btn_row.Add(mand_view, 0, wx.RIGHT, 8)
    mand_btn_row.Add(mand_update, 0)
    mand_sizer.Add(mand_text, 0, wx.ALL, 8)
    mand_sizer.Add(mand_detail, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    mand_sizer.Add(mand_btn_row, 0, wx.EXPAND | wx.ALL, 8)
    mandatory_panel.SetSizer(mand_sizer)
    mandatory_panel.Hide()
    root.Add(mandatory_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    panel.SetSizer(root)
    # Dialog sizer
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)

    state = {"closed": False, "stage": "preferences", "stages": {sid: STATE_PENDING for sid in STAGES}, "mandatory": False}

    # Helpers
    def _refresh_stage_labels():
        for sid, ctrl in stage_controls.items():
            cur = state["stages"].get(sid, STATE_PENDING)
            base = t(f"splash.stage_{sid}") if t(f"splash.stage_{sid}") != f"[splash.stage_{sid}]" else STAGE_LABELS[sid]
            icon = _stage_icon(cur)
            try:
                ctrl.SetLabel(f"{icon}  {base}")
                # Bold for active
                fnt = ctrl.GetFont()
                if cur == STATE_ACTIVE:
                    fnt.SetWeight(wx.FONTWEIGHT_BOLD)
                else:
                    fnt.SetWeight(wx.FONTWEIGHT_NORMAL)
                ctrl.SetFont(fnt)
            except Exception:
                pass
        panel.Layout()

    def set_stage(stage_id: str, stage_state: str):
        if stage_id not in STAGES:
            return
        state["stages"][stage_id] = stage_state
        state["stage"] = stage_id
        try:
            import wx as _wx
            if _wx.GetApp() is not None:
                _wx.CallAfter(_refresh_stage_labels)
            else:
                _refresh_stage_labels()
        except Exception:
            pass

    def set_progress(value: int, message: str | None = None):
        try:
            v = max(0, min(100, int(value)))
            gauge.SetValue(v)
            if message is not None:
                status_text.SetLabel(str(message))
            panel.Layout()
        except Exception:
            pass

    def set_status(message: str):
        try:
            status_text.SetLabel(str(message))
            panel.Layout()
        except Exception:
            pass

    def append_log(line: str, status: str | None = None):
        # Spec example: "Loading preferences... OK"
        suffix = f" {status}" if status else ""
        entry = f"{line}{suffix}".rstrip()
        try:
            # Auto-scroll only if at bottom
            insertion = log_ctrl.GetInsertionPoint()
            # Check if user scrolled up: compare caret at end?
            # Simple: if previous position was at end, scroll after append
            at_bottom = insertion >= max(0, log_ctrl.GetLastPosition() - 2)
            if log_ctrl.GetValue():
                log_ctrl.AppendText("\n" + entry)
            else:
                log_ctrl.SetValue(entry)
            if at_bottom:
                log_ctrl.ShowPosition(log_ctrl.GetLastPosition())
        except Exception:
            try:
                log_ctrl.AppendText(entry + "\n")
            except Exception:
                pass

    def set_indeterminate(active: bool, message: str | None = None):
        try:
            if active:
                gauge.Pulse()
                if message is not None:
                    status_text.SetLabel(str(message))
            else:
                gauge.SetValue(gauge.GetValue())
        except Exception:
            pass

    def set_mandatory_update(version: str, details: str = ""):
        state["mandatory"] = True
        try:
            mand_detail.SetLabel(details or f"Version {version} must be installed before HPC Client can continue.")
            mandatory_panel.Show()
            # Disable connection controls per §29
            profile_choice.Disable()
            reload_btn.Disable()
            connect_btn.Disable()
            # Continue Offline disabled unless explicitly supported — hide/disable
            offline_btn.Disable()
            panel.Layout()
            dlg.Layout()
            dlg.FitInside()
        except Exception:
            pass

    def set_connecting(is_connecting: bool, profile_name: str = ""):
        try:
            if is_connecting:
                msg = t("connection.connecting_to").format(name=profile_name) if t("connection.connecting_to") != "[connection.connecting_to]" else f"Connecting to {profile_name}..."
                status_text.SetLabel(msg)
                connect_btn.SetLabel(t("common.connecting") if t("common.connecting") != "[common.connecting]" else "Connecting...")
                connect_btn.Disable()
                profile_choice.Disable()
                reload_btn.Disable()
                offline_btn.Disable()
            else:
                connect_btn.SetLabel(t("login.connect_selected") if t("login.connect_selected") != "[login.connect_selected]" else "Connect")
                connect_btn.Enable(True)
                profile_choice.Enable(True)
                reload_btn.Enable(True)
                offline_btn.Enable(True)
            panel.Layout()
        except Exception:
            pass

    def set_offline_mode():
        try:
            status_text.SetLabel(t("connection.offline_starting") if t("connection.offline_starting") != "[connection.offline_starting]" else "Starting in offline mode...")
            profile_choice.Disable()
            reload_btn.Disable()
            connect_btn.Disable()
            offline_btn.Disable()
            panel.Layout()
        except Exception:
            pass

    # Button handlers
    def _on_reload(_evt):
        if on_reload:
            try:
                on_reload()
            except Exception:
                pass
        else:
            # Default: refresh profiles list if possible
            try:
                from hpc_gui.config.storage import load_profiles
                new_profiles = load_profiles()
                choices_new = [str(p.get("name","")) for p in new_profiles if p.get("name")]
                if choices_new:
                    profile_choice.Clear()
                    for c in choices_new:
                        profile_choice.Append(c)
                    profile_choice.SetSelection(0)
                    append_log("Reloaded connection profiles", "OK")
                else:
                    append_log("No connection profiles found", "")
            except Exception as exc:
                append_log(f"Reload failed: {exc}", "")

    def _on_offline(_evt):
        set_offline_mode()
        if on_offline:
            try:
                on_offline()
            except Exception:
                pass
        else:
            # Default: close splash and continue
            try:
                dlg.EndModal(wx.ID_CANCEL)
            except Exception:
                try:
                    dlg.Close()
                except Exception:
                    pass

    def _on_connect(_evt):
        sel = ""
        try:
            sel = profile_choice.GetStringSelection()
        except Exception:
            pass
        set_connecting(True, sel)
        if on_connect:
            def worker():
                try:
                    on_connect(sel)
                except Exception as exc:
                    import wx as _wx
                    def on_err():
                        set_connecting(False, sel)
                        append_log(f"Connection failed: {exc}", "")
                        set_status(str(exc))
                    try:
                        _wx.CallAfter(on_err)
                    except Exception:
                        pass
            Thread(target=worker, daemon=True).start()
        else:
            # No handler: just reset after delay for demo
            def reset():
                import wx as _wx
                import time
                time.sleep(0.5)
                _wx.CallAfter(lambda: set_connecting(False, sel))
            Thread(target=reset, daemon=True).start()

    reload_btn.Bind(wx.EVT_BUTTON, _on_reload)
    offline_btn.Bind(wx.EVT_BUTTON, _on_offline)
    connect_btn.Bind(wx.EVT_BUTTON, _on_connect)

    # Language refresh
    def refresh_labels(_lang=None):
        if state["closed"]:
            return
        try:
            brand_sub.SetLabel(t("splash.starting") if t("splash.starting") != "[splash.starting]" else "Starting application...")
            # stage labels refreshed via _refresh_stage_labels
            _refresh_stage_labels()
            status_text.SetLabel(status_text.GetLabel())  # keep current
        except Exception:
            pass
        try:
            reload_btn.SetLabel(t("connection.reload") if t("connection.reload") != "[connection.reload]" else "Reload Connections")
            offline_btn.SetLabel(t("connection.continue_offline") if t("connection.continue_offline") != "[connection.continue_offline]" else "Continue Offline")
            connect_btn.SetLabel(t("login.connect_selected") if t("login.connect_selected") != "[login.connect_selected]" else "Connect")
        except Exception:
            pass
        try:
            mand_view.SetLabel(t("common.details") if t("common.details") != "[common.details]" else "View Details")
            mand_update.SetLabel(t("updates.update_now") if t("updates.update_now") != "[updates.update_now]" else "Update Now")
        except Exception:
            pass

    subscribe_language_change(refresh_labels)

    def on_close(evt):
        state["closed"] = True
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass
        evt.Skip()

    dlg.Bind(wx.EVT_CLOSE, on_close)

    # Expose API for external startup orchestration
    dlg._wx_splash_controls = {
        "brand_title": brand_title,
        "brand_sub": brand_sub,
        "stages": stage_controls,
        "gauge": gauge,
        "status": status_text,
        "log": log_ctrl,
        "profile_choice": profile_choice,
        "reload": reload_btn,
        "offline": offline_btn,
        "connect": connect_btn,
        "mandatory_panel": mandatory_panel,
        "mandatory_text": mand_text,
        "mandatory_detail": mand_detail,
        "mandatory_view": mand_view,
        "mandatory_update": mand_update,
    }
    dlg._wx_splash_set_stage = set_stage
    dlg._wx_splash_set_progress = set_progress
    dlg._wx_splash_set_status = set_status
    dlg._wx_splash_append_log = append_log
    dlg._wx_splash_set_indeterminate = set_indeterminate
    dlg._wx_splash_set_mandatory = set_mandatory_update
    dlg._wx_splash_set_connecting = set_connecting
    dlg._wx_splash_set_offline = set_offline_mode
    dlg._wx_splash_state = state

    return dlg


def show_startup_splash(parent=None, **kwargs):
    dlg = create_startup_splash(parent, **kwargs)
    dlg.ShowModal()
    return dlg


__all__ = ["create_startup_splash", "show_startup_splash", "STAGES", "STATE_PENDING", "STATE_ACTIVE", "STATE_COMPLETE", "STATE_FAILED"]
