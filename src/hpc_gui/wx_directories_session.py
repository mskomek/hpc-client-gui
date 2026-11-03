"""Live session rebinding for the embedded two-pane directories view."""

from __future__ import annotations

from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings
from hpc_gui.core.i18n import t


def _resolve_scratch_home(session_state) -> tuple[str, str]:
    """Resolve provider scratch and home paths from the current connection."""
    session = session_state.get("session") if isinstance(session_state, dict) else None
    if session is None and isinstance(session_state, dict) and session_state.get("profile"):
        session = session_state
    if not isinstance(session, dict):
        session = {}

    cfg = session.get("cfg")
    if cfg is None:
        cfg = session.get("profile")
    if isinstance(cfg, dict):
        user = str(cfg.get("username") or cfg.get("user") or "user")
        system_raw = cfg.get("system_settings")
        if system_raw is None:
            system_raw = cfg.get("system") or cfg.get("system_profile")
    elif cfg is not None:
        user = str(getattr(cfg, "username", None) or getattr(cfg, "user", None) or "user")
        system_raw = getattr(cfg, "system_settings", None)
        if system_raw is None:
            system_raw = getattr(cfg, "system", None)
    else:
        profile = session.get("profile") if isinstance(session.get("profile"), dict) else {}
        user = str(profile.get("username") or "user")
        system_raw = profile.get("system_settings") or profile.get("system")
    system = normalize_system_settings(system_raw)
    scratch = system.get("scratch_dir", "")
    home = system.get("home_dir", "")
    scratch_dir = format_remote_path(scratch, user) if isinstance(scratch, str) else ""
    home_dir = format_remote_path(home, user) if isinstance(home, str) else ""
    return scratch_dir or "/", home_dir or "/"


def _clear_pane_navigation(panel) -> None:
    """Discard stale per-pane back/forward paths after a profile switch."""
    tabs = getattr(panel, "_wx_remote_tabs", ()) or ()
    for tab in tabs:
        if not isinstance(tab, dict):
            continue
        for key in ("back_stack", "forward_stack"):
            values = tab.get(key)
            if isinstance(values, list):
                values.clear()


def rebind_directories_storage(host, session_state) -> dict:
    """Rebind both panes and immediately reload them for the new session."""
    scratch, home = _resolve_scratch_home(session_state)
    models = getattr(host, "_wx_dirs_models", None) or {}
    controls = getattr(host, "_wx_dirs_controls", None) or {}

    for key, target in (("scratch", scratch), ("home", home)):
        model = models.get(key)
        if model is not None:
            try:
                model.invalidate()
            except Exception:
                pass
        panel = controls.get(key)
        pane_controls = getattr(panel, "_wx_remote_controls", {}) if panel is not None else {}
        navigate = pane_controls.get("navigate") if isinstance(pane_controls, dict) else None
        load = pane_controls.get("load") if isinstance(pane_controls, dict) else None
        if callable(navigate):
            try:
                navigate(target)
            except Exception:
                continue
        elif model is not None:
            try:
                model.navigate(target)
            except Exception:
                continue
        _clear_pane_navigation(panel)
        history = getattr(model, "history", None)
        if isinstance(history, list):
            history.clear()
        path_control = pane_controls.get("path") if isinstance(pane_controls, dict) else None
        if path_control is not None:
            try:
                path_control.SetValue(target)
            except Exception:
                pass
        if callable(load):
            try:
                load()
            except Exception:
                pass

    for key, target in (("scratch", scratch), ("home", home)):
        label = controls.get(f"{key}_label")
        if label is not None:
            try:
                label.SetLabel(f"{key.title()} — {target}")
            except Exception:
                pass
    return {"scratch": scratch, "home": home}


def mark_directories_disconnected(host) -> None:
    """Invalidate remote listings and mark both panes disconnected."""
    controls = getattr(host, "_wx_dirs_controls", None) or {}
    models = getattr(host, "_wx_dirs_models", None) or {}
    for key in ("scratch", "home"):
        model = models.get(key)
        if model is not None:
            try:
                model.invalidate()
            except Exception:
                pass
        panel = controls.get(key)
        pane_controls = getattr(panel, "_wx_remote_controls", {}) if panel is not None else {}
        listing = pane_controls.get("listing") if isinstance(pane_controls, dict) else None
        if listing is not None:
            try:
                listing.DeleteAllItems()
            except Exception:
                pass
        label = controls.get(f"{key}_label")
        if label is not None:
            try:
                label.SetLabel(t("dirs.disconnected_label").format(name=key.title()))
            except Exception:
                pass
