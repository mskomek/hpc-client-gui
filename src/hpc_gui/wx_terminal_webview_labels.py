"""Language-aware labels and transient write feedback for the wx terminal."""

from hpc_gui.core.i18n import t


class TerminalLabelsMixin:
    """Own translated toolbar labels and the temporary input error status."""

    def _refresh_labels(self, _language=None):
        self._update_accessibility_label()
        try:
            self._find_ctrl.SetHint(t("login.terminal_find"))
            self._find_btn.SetLabel(t("login.terminal_find"))
            self._clear_btn.SetLabel(t("login.terminal_clear"))
            self._clear_btn.SetToolTip(t("login.terminal_clear"))
            self._font_down_btn.SetLabel(t("login.terminal_font_decrease_short"))
            self._font_down_btn.SetToolTip(t("login.terminal_font_decrease"))
            self._font_up_btn.SetLabel(t("login.terminal_font_increase_short"))
            self._font_up_btn.SetToolTip(t("login.terminal_font_increase"))
            self._find_btn.SetToolTip(t("login.terminal_find"))
        except Exception:
            pass

    def _write_failure_text(self) -> str:
        return t("login.terminal_write_failed")

    def _show_write_failure(self):
        """Show rejected input without changing the SSH connection state."""
        self._write_failure_shown = True
        try:
            self._status_label.SetLabel(self._write_failure_text())
        except Exception:
            pass

    def _clear_write_failure(self):
        if not self._write_failure_shown:
            return
        self._write_failure_shown = False
        try:
            self._status_label.SetLabel(self._status_text)
        except Exception:
            pass
