"""Runtime language refresh for the login widget's owned controls."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def retranslate_ui(widget) -> None:
    """Refresh the labels owned by LoginWidget and its composed terminal."""
    try:
        widget.cb_x11.setText(t("login.x11_enable"))
        widget.cb_strict_hostkey.setText(t("login.strict_host_key"))
        widget.cb_save_password.setText(t("login.save_password"))
        widget.btn_browse_key.setText(t("login.browse"))
        widget.btn_save.setText(t("login.save"))
        labels = (
            (widget.profile_name, "login.profile_name_label"),
            (widget.host, "login.host"),
            (widget.port, "login.port"),
            (widget.username, "login.username"),
            (widget.password, "login.password"),
            (widget.key_row_widget, "login.ssh_key"),
        )
        for field, key in labels:
            label = widget.form.labelForField(field)
            if label is not None:
                label.setText(t(key))
        widget.console_title_label.setText(t("login.console_title"))
        widget.console.setPlaceholderText(t("login.console_placeholder"))
        widget.cmd_in.setPlaceholderText(t("login.command_placeholder"))
        widget.btn_run_cmd.setText(t("login.run_command"))
        widget.terminal_header.retranslate_ui()
        widget.btn_add_connection.setText(t("login.add_connection"))
        widget.btn_connect.setText(t("login.connect_selected"))
    except Exception:
        pass


__all__ = ["retranslate_ui"]
