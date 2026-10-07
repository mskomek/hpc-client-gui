"""wx shell events workflows."""
from __future__ import annotations



def _logs_callbacks(session_state, parent, lifecycle):
    # Logs view uses WxLogsModel internally; no session needed
    return {}


def _directories_callbacks(session_state, parent, lifecycle):
    # Share single implementation between embedded tab and dispatch
    # Pass session_state so view can derive scratch/home via system_profile helpers
    # Also provide run_shell delegation matching _remote_files_callbacks pattern
    return {"session_state": session_state}


def _select_embedded_page(session_state, parent, key: str) -> bool:
    """Select the existing embedded notebook page for ``key`` (SHELL-NAV-002).

    Returns True when an embedded page was selected, False when the caller
    must fall back to the detached window path (headless/service use and
    legacy callers without a shell frame). The detached ``show_*`` owner
    stays intact in every dispatch branch for those fallbacks.
    """
    try:
        state = session_state or {}
        notebook = state.get("_embedded_main_notebook")
        if notebook is None:
            return False
        frame = parent
        for _ in range(8):
            if frame is None:
                break
            controls = getattr(frame, "_wx_shell_controls", None)
            if isinstance(controls, dict) and isinstance(controls.get("pages"), dict):
                break
            try:
                frame = frame.GetParent()
            except Exception:
                frame = None
        else:
            frame = None
        if frame is None:
            controls = None
        else:
            controls = getattr(frame, "_wx_shell_controls", None)
        if not isinstance(controls, dict):
            return False
        pages = controls.get("pages") or {}
        entry = pages.get(key) or {}
        page = entry.get("page")
        if page is None:
            return False
        try:
            index = notebook.FindPage(page)
        except Exception:
            return False
        try:
            notebook.SetSelection(index)
        except Exception:
            return False
        try:
            page.SetFocus()
        except Exception:
            pass
        return True
    except Exception:
        return False
