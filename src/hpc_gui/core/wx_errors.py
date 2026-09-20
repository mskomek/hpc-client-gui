"""wx user-visible error reporting with stable diagnostic codes.

W02 error governance (``HPC-W01-TODO-ERROR-GOV-001`` /
``HPC-W01-TODO-ERROR-GOV-002``, ``HPC-W01-TODO-018``, ``HPC-W01-TODO-020``):

every mandatory wx action failure must produce a visible user error carrying
a stable diagnostic code plus a structured log entry.  Silent
``except Exception: pass`` on a user-visible dispatch path is forbidden.

The Qt surface already has :func:`hpc_gui.core.ui_errors.show_exception`;
this module is its wx counterpart.  ``wx`` is imported lazily so importing
this helper never makes ``wx`` mandatory for non-GUI processes.
"""

from __future__ import annotations

from typing import Optional

from hpc_gui.core.debug_support import ErrorId, log_exception_with_id, new_error_id
from hpc_gui.core.i18n import t


def report_wx_action_error(
    parent,
    *,
    area: str,
    message_key: str,
    exc: Optional[BaseException] = None,
    technical_detail: str = "",
) -> ErrorId:
    """Log ``exc`` with a stable error id and show it to the user.

    Returns the :class:`ErrorId` so tests and logs can correlate the visible
    dialog with the structured log entry (``Error-ID=<id>``).

    When ``exc`` is given it is logged with traceback; otherwise a fresh id
    is minted (e.g. a failed ``webbrowser.open`` returning ``False`` raises
    no exception but still needs a diagnosable code).  The dialog is
    best-effort: if ``wx`` cannot be imported or the dialog itself fails, the
    error id is still returned and the structured log entry still exists, so
    the failure never becomes silent.
    """
    if exc is not None:
        err_id = log_exception_with_id(area, exc, logger_name="hpc_gui.wx_shell")
    else:
        err_id = new_error_id(area)

    message = t(message_key)
    label = t("common.error_code")
    hint = t("common.error_code_hint")
    text = f"{message}\n\n{label}: {err_id}\n{hint}"
    detail = (technical_detail or "").strip()
    if detail and detail not in text:
        text += f"\n\n{t('common.technical_detail')}: {detail}"

    try:
        import wx

        title = t("common.error")
        try:
            wx.MessageBox(text, title, wx.OK | wx.ICON_ERROR, parent)
        except Exception:
            # Parent-bound dialog failed (e.g. parent already destroyed);
            # retry parentless so the user still sees the failure.
            try:
                wx.MessageBox(text, title, wx.OK | wx.ICON_ERROR)
            except Exception:
                pass
    except Exception:
        pass
    return err_id
