"""Login connection-profile UI flows (Wave M01).

Qt ownership of the login widget's profile surface: profile list,
profile form mapping, add/edit/duplicate dialogs and the save/connect
bridges. Service access goes through canonical modules with call-time
attribute lookup so tests can patch the canonical homes. The facade keeps
thin delegating methods for signal wiring and the tested API surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
)

from hpc_gui.config import storage as _storage
from hpc_gui.config.file_manager_profile import normalize_file_manager_settings
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.core.i18n import t
from hpc_gui.services.profile_duplicate import duplicate_profile
from hpc_gui.ssh.client import coerce_keepalive_interval
from hpc_gui.config.storage import (
    coerce_profile_ssh_timeout,
    coerce_profile_transfer_parallelism,
)
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime cycle
    from hpc_gui.ui.widgets.login_widget import LoginWidget


def refresh_profiles(widget: LoginWidget, select_name: str | None = None) -> None:
    widget.profiles_list.clear()
    widget.btn_connect.setEnabled(False)
    profiles = _storage.load_profiles()
    for p in profiles:
        name = p.get("name", "")
        if name:
            widget.profiles_list.addItem(name)
    if select_name:
        items = widget.profiles_list.findItems(select_name, Qt.MatchFlag.MatchExactly)
        if items:
            widget.profiles_list.setCurrentItem(items[0])


def on_profile_selected(widget: LoginWidget) -> None:
    item = widget.profiles_list.currentItem()
    if not item:
        widget.btn_connect.setEnabled(False)
        return
    name = item.text()
    profiles = _storage.load_profiles()
    prof = next((p for p in profiles if p.get("name") == name), None)
    if not prof:
        widget.btn_connect.setEnabled(False)
        return
    load_profile_into_fields(widget, prof)
    widget.btn_connect.setEnabled(True)


def load_profile_into_fields(widget: LoginWidget, prof: dict) -> None:
    widget.profile_name.setText(prof.get("name", ""))
    widget.host.setText(prof.get("host", ""))
    widget.port.setText(str(prof.get("port", 22)))
    widget.username.setText(prof.get("username", ""))
    widget.project.setText(prof.get("project", ""))
    widget.account.setText(prof.get("account", ""))
    widget.key_path.setText(prof.get("key_path", ""))
    widget.cb_x11.setChecked(bool(prof.get("x11_forwarding", False)))
    host_key_policy = str(prof.get("host_key_policy") or "accept-new").strip()
    if host_key_policy not in {"accept-new", "strict"}:
        host_key_policy = "accept-new"
    widget._profile_host_key_policy = host_key_policy
    widget.cb_strict_hostkey.setChecked(host_key_policy == "strict")
    # legacy field: prof.get("dry_run") ignored

    save_pw = bool(prof.get("save_password", False))
    widget.cb_save_password.setChecked(save_pw)
    widget._password_prompt_policy = (
        prof.get("password_prompt_policy") or "when-needed"
    )
    widget._profile_system_settings = normalize_system_settings(
        prof.get("system")
    )
    update_provider_requirement_labels(widget)
    raw_file_manager = prof.get("file_manager")
    widget._profile_file_manager_raw = (
        dict(raw_file_manager) if isinstance(raw_file_manager, dict) else {}
    )
    widget._profile_file_manager_settings = normalize_file_manager_settings(
        raw_file_manager
    )
    raw_jump_host = prof.get("jump_host")
    widget._profile_jump_host_raw = (
        dict(raw_jump_host) if isinstance(raw_jump_host, dict) else {}
    )
    widget._profile_jump_host_settings = normalize_jump_host_settings(raw_jump_host)
    widget._profile_cli_allowed = bool(prof.get("cli_allowed", False))
    widget._profile_keepalive = coerce_keepalive_interval(
        prof.get("keepalive_interval_seconds", 30)
    )
    widget._profile_transfer_parallelism = coerce_profile_transfer_parallelism(prof.get("transfer_parallelism", 1))
    widget._profile_ssh_timeout = coerce_profile_ssh_timeout(prof.get("ssh_timeout"))
    widget.sp_transfer_parallelism.setValue(widget._profile_transfer_parallelism)
    widget.sp_ssh_timeout.setValue(widget._profile_ssh_timeout or 0)
    # Never auto-fill decrypted password.
    # If legacy plain password exists, show it; if encrypted, keep empty.
    if save_pw and isinstance(prof.get("password"), str) and prof.get("password"):
        widget.password.setText(prof.get("password", ""))
    else:
        widget.password.setText("")


def load_profile_by_name(widget: LoginWidget, name: str) -> dict | None:
    profiles = _storage.load_profiles()
    return next((p for p in profiles if p.get("name") == name), None)


def update_provider_requirement_labels(widget: LoginWidget) -> None:
    provider = widget._profile_system_settings.get("provider_template") or {}
    requirements = provider.get("requirements", {}) if isinstance(provider, dict) else {}
    for key, label in (("project", widget.project_label), ("account", widget.account_label)):
        rule = requirements.get(key) if isinstance(requirements, dict) else None
        name = str((rule or {}).get("label") or t(f"connection.{key}")) if isinstance(rule, dict) else t(f"connection.{key}")
        label.setText(name + (" *" if isinstance(rule, dict) and rule.get("required") else ""))
        label.setToolTip(str((rule or {}).get("help") or ""))


def open_add_connection_dialog(widget: LoginWidget) -> None:
    dlg = ConnectionDialog(
        widget,
        initial_profile=None,
        on_save=widget._save_profile_from_dialog,
        on_connect=widget._save_and_connect_from_dialog,
    )
    dlg.exec()


def open_edit_connection_dialog(widget: LoginWidget, profile_name: str | None = None) -> None:
    name = (profile_name or selected_profile_name(widget)).strip()
    if not name:
        return
    initial = load_profile_by_name(widget, name)
    if not initial:
        return
    if initial.get("password_keychain_ref") or initial.get("password_dpapi"):
        expected = widget._decrypt_profile_password(initial, allow_prompt=False)
        if expected is None:
            return
        entered, ok = QInputDialog.getText(
            widget,
            t("connection.edit_auth_title"),
            t("connection.edit_auth_prompt"),
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return
        if entered != expected:
            QMessageBox.warning(
                widget,
                t("login.err_title"),
                t("connection.edit_auth_failed"),
            )
            return
    elif initial.get("password_enc") and initial.get("password_salt"):
        if widget._decrypt_profile_password(initial, allow_prompt=True) is None:
            return
    dlg = ConnectionDialog(
        widget,
        initial_profile=initial,
        on_save=widget._save_profile_from_dialog,
        on_connect=widget._save_and_connect_from_dialog,
    )
    dlg.setWindowTitle(t("connection.edit_dialog_title"))
    widget._editing_profile_original_name = name
    try:
        dlg.exec()
    finally:
        widget._editing_profile_original_name = ""


def selected_profile_name(widget: LoginWidget) -> str:
    item = widget.profiles_list.currentItem()
    return item.text().strip() if item else ""


def show_profile_context_menu(widget: LoginWidget, pos) -> None:
    item = widget.profiles_list.itemAt(pos)
    if not item:
        return
    widget.profiles_list.setCurrentItem(item)
    menu = QMenu(widget)
    act_connect = menu.addAction(t("login.connect"))
    act_edit = menu.addAction(t("connection.edit_action"))
    act_duplicate = menu.addAction(t("login.duplicate"))
    chosen = menu.exec(widget.profiles_list.mapToGlobal(pos))
    if chosen == act_connect:
        connect_selected_profile(widget)
        return
    if chosen == act_edit:
        open_edit_connection_dialog(widget, item.text())
    if chosen == act_duplicate:
        duplicate_selected_profile(widget, item.text())


def duplicate_selected_profile(widget: LoginWidget, profile_name: str | None = None) -> None:
    name = (profile_name or selected_profile_name(widget)).strip()
    original = load_profile_by_name(widget, name)
    if not original:
        return
    duplicate = duplicate_profile(original, [p.get("name", "") for p in _storage.load_profiles()])
    dialog = ConnectionDialog(
        widget,
        initial_profile=duplicate,
        on_save=widget._save_profile_from_dialog,
    )
    dialog.setWindowTitle(t("login.duplicate"))
    dialog.exec()


def on_profile_double_clicked(widget: LoginWidget, item) -> None:
    if item is None:
        return
    widget.profiles_list.setCurrentItem(item)
    connect_selected_profile(widget)


def save_profile_from_dialog(widget: LoginWidget, profile: dict) -> bool:
    widget._profile_system_settings = normalize_system_settings(
        profile.get("system")
    )
    widget._password_prompt_policy = (
        profile.get("password_prompt_policy") or "when-needed"
    )
    load_profile_into_fields(widget, profile)
    return widget.save_profile()


def save_and_connect_from_dialog(widget: LoginWidget, profile: dict) -> bool:
    # The typed password is a transient connection credential: it is used
    # for this connection attempt but only persisted when the dialog's
    # "save password" option is on.  It is passed explicitly instead of
    # being routed back through the password field, which may be cleared
    # while loading a profile.
    transient_password = (
        profile.get("password")
        if isinstance(profile.get("password"), str)
        else ""
    )
    if not save_profile_from_dialog(widget, profile):
        return False
    return widget.connect_clicked(transient_password=transient_password)


def connect_selected_profile(widget: LoginWidget) -> bool:
    name = selected_profile_name(widget)
    if not name:
        return False
    prof = load_profile_by_name(widget, name)
    if not prof:
        return False
    load_profile_into_fields(widget, prof)
    return widget.connect_clicked()


def pick_key_file(widget: LoginWidget) -> None:
    path, _ = QFileDialog.getOpenFileName(widget, t("login.ssh_key"))
    if path:
        widget.key_path.setText(path)


def profile_patch_base(widget: LoginWidget, port: int, name: str) -> dict[str, Any]:
    """Known-field patch for :func:`save_profile`; the store module merges
    it onto the stored profile so unrelated keys survive."""
    from hpc_gui.config.file_manager_profile import patch_file_manager_settings
    from hpc_gui.config.jump_host_profile import patch_jump_host_settings

    return {
        "name": name,
        "host": widget.host.text().strip(),
        "port": port,
        "username": widget.username.text().strip(),
        "project": widget.project.text().strip(),
        "account": widget.account.text().strip(),
        "key_path": widget.key_path.text().strip(),
        "host_key_policy": widget._profile_host_key_policy,
        "x11_forwarding": widget.cb_x11.isChecked(),
        "cli_allowed": getattr(widget, "_profile_cli_allowed", False),
        "keepalive_interval_seconds": widget._profile_keepalive,
        "transfer_parallelism": int(widget.sp_transfer_parallelism.value()),
        "ssh_timeout": float(widget.sp_ssh_timeout.value()) or None,
        # dry_run removed
        "save_password": widget.cb_save_password.isChecked(),
        "password_prompt_policy": widget._password_prompt_policy,
        "system": normalize_system_settings(widget._profile_system_settings),
        "file_manager": patch_file_manager_settings(
            getattr(widget, "_profile_file_manager_raw", None),
            {
                "local_start_dir": normalize_file_manager_settings(
                    getattr(widget, "_profile_file_manager_settings", None)
                )["local_start_dir"]
            },
        ),
        "jump_host": patch_jump_host_settings(
            getattr(widget, "_profile_jump_host_raw", None),
            normalize_jump_host_settings(
                getattr(widget, "_profile_jump_host_settings", None)
            ),
        ),
    }
