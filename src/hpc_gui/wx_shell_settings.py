"""wx shell settings workflows."""
from __future__ import annotations



def run_wx_update_check(parent) -> None:
    """Authoritative wx update-check controller (W41 UPDATER-ROUTE-001/002).

    Single shared implementation for the visible ``Check for Updates`` menu
    action (``APP-UPDATE-CHECK`` dispatch), the shell ``_on_update`` handler,
    and any other manual update-menu path. Opens the checking dialog and
    always starts the real update-check worker so the dialog transitions
    from ``CHECKING`` to ``UP_TO_DATE``, ``UPDATE_AVAILABLE`` (or manual
    install fallback), or ``FAILED``. Opening a checking dialog without
    starting the worker is forbidden.
    """
    import threading

    import wx

    from hpc_gui.core.i18n import t as _t

    try:
        from hpc_gui.wx_updater_view import (
            STATE_CHECKING,
            WxUpdateDialog,
        )
    except Exception:
        raise
    dlg = WxUpdateDialog(parent, None)
    dlg._build_for_state(STATE_CHECKING)
    dlg.dlg.Show()

    def _alive(frame) -> bool:
        try:
            if frame is None:
                return False
            import wx as _wx

            if not _wx.Window.FindWindowById(frame.GetId()):
                return False
        except Exception:
            return False
        return True

    def worker():
        try:
            from hpc_gui.services.app_updater import (
                AUTOMATIC_INSTALL_STRATEGIES,
                get_latest_release,
                is_newer_version,
            )
            from hpc_gui.core.platform import current_os
            from hpc_gui import __version__ as cur_ver2

            release = get_latest_release(timeout=10)

            def on_done():
                if not _alive(parent):
                    try:
                        dlg.Destroy()
                    except Exception:
                        pass
                    return
                try:
                    from hpc_gui.wx_updater_view import (
                        STATE_FAILED as _FAILED,
                        STATE_UPDATE_AVAILABLE as _AVAIL,
                        STATE_UP_TO_DATE as _UPTODATE,
                    )

                    if not is_newer_version(release.version, cur_ver2):
                        dlg._build_for_state(_UPTODATE)
                        return
                    try:
                        from hpc_gui.services import app_updater as _au

                        macos_ok = not (
                            release.install_strategy == "macos-bundle"
                            and release.security_status != _au.SECURITY_SIGNED
                        )
                    except Exception:
                        macos_ok = True
                    if (
                        release.install_strategy not in AUTOMATIC_INSTALL_STRATEGIES
                        or not macos_ok
                    ):
                        import webbrowser

                        msg = (
                            _t("updates.manual_install").format(version=release.version)
                            if _t("updates.manual_install") != "[updates.manual_install]"
                            else f"Update {release.version} requires manual install."
                        )
                        if current_os() == "macos":
                            try:
                                sec_key = {
                                    _au.SECURITY_UNSIGNED: "updates.security_unsigned_mac",
                                    _au.SECURITY_SIGNED: "updates.security_signed_mac",
                                    _au.SECURITY_UNKNOWN: "updates.security_unknown_mac",
                                }.get(release.security_status, "updates.security_unknown_mac")
                                msg += "\n\n" + _t(sec_key)
                            except Exception:
                                pass
                        wx.MessageBox(msg, _t("updates.title"), wx.OK | wx.ICON_INFORMATION, parent)
                        try:
                            webbrowser.open(release.zip_url or release.html_url)
                        except Exception:
                            pass
                        try:
                            dlg.Destroy()
                        except Exception:
                            pass
                        return
                    dlg.release = release
                    dlg._total = getattr(release, "size", None)
                    try:
                        from hpc_gui.wx_updater_view import _parse_whats_new

                        dlg._whats_new = _parse_whats_new(getattr(release, "body", ""))
                    except Exception:
                        pass
                    dlg._build_for_state(_AVAIL)
                except Exception as exc2:
                    dlg._error_message = str(exc2)
                    dlg._error_details = f"{type(exc2).__name__}: {exc2}"
                    dlg._build_for_state(_FAILED)

            wx.CallAfter(on_done)
        except Exception as exc:
            def on_err(exc=exc):
                if not _alive(parent):
                    try:
                        dlg.Destroy()
                    except Exception:
                        pass
                    return
                from hpc_gui.wx_updater_view import STATE_FAILED as _FAILED2

                dlg._error_message = str(exc)
                dlg._error_details = f"{type(exc).__name__}: {exc}"
                dlg._build_for_state(_FAILED2)

            wx.CallAfter(on_err)

    threading.Thread(target=worker, daemon=True).start()
