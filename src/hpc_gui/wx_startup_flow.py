"""Non-blocking startup stage orchestration for the wx application."""

from __future__ import annotations

import logging
import time
from threading import Thread

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.startup_update_state import StartupUpdateState
from hpc_gui.wx_splash_stages import STATE_ACTIVE, STATE_COMPLETE, STATE_FAILED


class StartupFlow:
    """Advance startup stages from wx timers while the main event loop runs."""

    def __init__(self, app, splash, on_complete, *, update_timeout: float = 10.0):
        import wx

        self.wx = wx
        self.app = app
        self.splash = splash
        self.on_complete = on_complete
        self.update_timeout = update_timeout
        self.update_check = StartupUpdateState()
        self.started_at = 0.0
        self.timer = None
        self._helper_check = StartupUpdateState()
        self._helper_started_at = 0.0
        self._cancelled = False
        self.splash.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._start_update_check()

    def _on_destroy(self, event) -> None:
        try:
            if event.GetWindow() is self.splash:
                self.cancel()
        finally:
            event.Skip()

    def cancel(self) -> None:
        self._cancelled = True
        self.update_check.skip()
        self._helper_check.skip()
        if self.timer is not None:
            self.timer.Stop()
            self.timer = None

    def _schedule(self, delay_ms: int, callback) -> None:
        def guarded():
            if self._cancelled or self.splash._wx_splash_state.get("closed"):
                return
            callback()

        if not self._cancelled:
            self.timer = self.wx.CallLater(delay_ms, guarded)

    def _start_update_check(self) -> None:
        self.splash._wx_splash_set_stage("updates", STATE_ACTIVE)
        self.splash._wx_splash_set_progress(20, t("splash.checking_updates"))
        self.splash._wx_splash_append_log("Checking for updates...", "")
        button = self.splash._wx_splash_controls["update_skip"]
        button.Bind(self.wx.EVT_BUTTON, self._skip_update_check)
        self.splash._wx_splash_set_update_skip_visible(True)
        self.started_at = time.monotonic()

        def worker():
            release = None
            error = None
            try:
                from hpc_gui.services.app_updater import get_latest_release

                release = get_latest_release(timeout=self.update_timeout)
            except Exception as exc:
                error = exc
            self.update_check.complete(release, error)

        Thread(target=worker, daemon=True).start()
        self._schedule(80, self._poll_update_check)

    def _skip_update_check(self, _event) -> None:
        if not self.update_check.skip():
            return
        logging.getLogger("hpc_gui").info("UPDATE_CHECK_SKIPPED_BY_USER")
        self.splash._wx_splash_append_log("UPDATE_CHECK_SKIPPED_BY_USER", "")
        self.splash._wx_splash_set_update_skip_visible(False)

    def _poll_update_check(self) -> None:
        if self.update_check.status == StartupUpdateState.CHECKING:
            elapsed = time.monotonic() - self.started_at
            if elapsed >= self.update_timeout:
                self.update_check.timeout()
            else:
                progress = min(35, 20 + int(elapsed * 1.2))
                self.splash._wx_splash_set_progress(progress, t("splash.checking_updates"))
                self._schedule(80, self._poll_update_check)
                return
        self._finish_update_check()

    def _finish_update_check(self) -> None:
        status = self.update_check.status
        release = None
        if status == StartupUpdateState.TIMED_OUT:
            self.splash._wx_splash_append_log("Update check timed out", "")
        elif status == StartupUpdateState.SKIPPED:
            pass
        else:
            release, error = self.update_check.result()
            if error is not None:
                logging.getLogger("hpc_gui").debug(
                    "update check failed: %s", error, exc_info=error
                )
                self.splash._wx_splash_append_log("Update check failed", "")
            else:
                self._record_release(release)

        self.splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        if release is not None and self.splash._wx_splash_state.get("found_update") is release:
            self._offer_release(release)
        self._schedule(200, self._start_preferences)

    def _record_release(self, release) -> None:
        try:
            from hpc_gui.services.app_updater import is_newer_version

            if release and is_newer_version(release.version, __version__):
                self.splash._wx_splash_append_log(f"Update available: {release.version}", "")
                self.splash._wx_splash_state["found_update"] = release
            else:
                self.splash._wx_splash_append_log("No updates available", "OK")
        except Exception as exc:
            logging.getLogger("hpc_gui").debug("update post-check error: %s", exc, exc_info=exc)
            self.splash._wx_splash_append_log("No updates available", "OK")

    def _offer_release(self, release) -> None:
        try:
            from hpc_gui.wx_updater_view import show_update_available

            downloaded = show_update_available(
                self.splash,
                __version__,
                release.version,
                getattr(release, "body", ""),
                release=release,
            )
            message = "Update download requested (on splash)" if downloaded else "Update postponed on splash"
            self.splash._wx_splash_append_log(message, "")
        except Exception as exc:
            logging.getLogger("hpc_gui").debug("splash update popup failed: %s", exc, exc_info=exc)

    def _start_preferences(self) -> None:
        self.splash._wx_splash_set_stage("preferences", STATE_ACTIVE)
        self.splash._wx_splash_set_progress(55, t("splash.loading_preferences"))
        try:
            from hpc_gui.config.storage import load_settings

            load_settings()
        except Exception:
            logging.getLogger("hpc_gui.startup").exception("Preferences check failed")
            self.splash._wx_splash_append_log("Preferences check failed", "")
            self.splash._wx_splash_set_stage("preferences", STATE_FAILED)
            self._schedule(200, self._start_helpers)
            return
        self.splash._wx_splash_append_log("Preferences loaded", "OK")
        self._schedule(500, self._finish_preferences)

    def _finish_preferences(self) -> None:
        self.splash._wx_splash_set_stage("preferences", STATE_COMPLETE)
        self._schedule(200, self._start_helpers)

    def _start_helpers(self) -> None:
        self.splash._wx_splash_set_stage("helpers", STATE_ACTIVE)
        self.splash._wx_splash_set_progress(85, t("splash.checking_helpers"))
        self.splash._wx_splash_append_log("Checking local SSH and SFTP support...", "")
        self._helper_started_at = time.monotonic()

        def worker():
            from hpc_gui.startup_checks import check_startup_helpers

            try:
                result = check_startup_helpers()
            except Exception as exc:
                self._helper_check.complete(error=exc)
            else:
                self._helper_check.complete(result)

        Thread(target=worker, daemon=True).start()
        self._schedule(80, self._poll_helpers)

    def _poll_helpers(self) -> None:
        if self._helper_check.status == StartupUpdateState.CHECKING:
            if time.monotonic() - self._helper_started_at < 5.0:
                self._schedule(80, self._poll_helpers)
                return
            self._helper_check.timeout()
        checks, error = self._helper_check.result()
        if checks is None or error is not None:
            self.splash._wx_splash_append_log("Local helper check unavailable", "")
            ok = False
        else:
            ok = True
            for name, available in checks.items():
                self.splash._wx_splash_append_log(
                    f"{name}: {'available' if available else 'unavailable'}",
                    "OK" if available else "",
                )
                ok = ok and available
        self.splash._wx_splash_set_stage("helpers", STATE_COMPLETE if ok else STATE_FAILED)
        self._schedule(200, self._show_ready)

    def _show_ready(self) -> None:
        self.splash._wx_splash_set_progress(100, t("common.ready"))
        self.splash._wx_splash_append_log("Ready — starting offline...", "")
        self._schedule(1800, self.on_complete)


def start_startup_flow(app, splash, on_complete) -> StartupFlow:
    """Start startup progression without blocking the wx event loop."""
    return StartupFlow(app, splash, on_complete)
