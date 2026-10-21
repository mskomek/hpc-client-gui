"""Login master-password and saved-secret flows (Wave M01).

Qt ownership of the login widget's credential-secret behavior: the master
password dialog, saved-password decryption and the connect-time prompt
policy. Service access goes through canonical modules with call-time
attribute lookup so tests can patch the canonical homes. The facade keeps
thin delegating methods for the public/private API surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from hpc_gui.config import storage as _storage
from hpc_gui.core import crypto_master as _crypto
from hpc_gui.core import secret_store as _secrets
from hpc_gui.core.i18n import t
from hpc_gui.services import connection_profile_service as _profiles_svc

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime cycle
    from hpc_gui.ui.widgets.login_widget import LoginWidget


def ask_master_password(widget: LoginWidget, *, confirm: bool) -> str | None:
    """Ask user for a master password. Returns None if canceled."""
    if widget._master_password_cache:
        return widget._master_password_cache

    saved_master = _storage.load_settings().get("master_password_dpapi")
    if saved_master:
        try:
            widget._master_password_cache = _secrets.unprotect_secret(str(saved_master))
            return widget._master_password_cache
        except Exception:
            _storage.update_settings({"master_password_dpapi": ""})

    if confirm:
        title_key = "login.master_create_title"
        prompt_key = "login.master_create_prompt"
        password_label_key = "login.master_password_label"
        confirm_label_key = "login.master_confirm_label"
        accept_key = "login.master_save"
    else:
        title_key = "login.master_unlock_title"
        prompt_key = "login.master_unlock_prompt"
        password_label_key = "login.master_password_label"
        confirm_label_key = None
        accept_key = "login.master_unlock"
    title = t(title_key)
    dialog = QDialog(widget)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    prompt = QLabel(t(prompt_key))
    prompt.setWordWrap(True)
    layout.addWidget(prompt)
    form = QFormLayout()
    password_input = QLineEdit()
    password_input.setEchoMode(QLineEdit.EchoMode.Password)
    form.addRow(t(password_label_key), password_input)
    confirm_input = None
    if confirm:
        confirm_input = QLineEdit()
        confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(t(confirm_label_key), confirm_input)
    layout.addLayout(form)
    remember_password = QCheckBox(t("connection.remember_master_password"))
    remember_password.setVisible(_secrets.is_available())
    remember_password.setChecked(False)
    layout.addWidget(remember_password)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t(accept_key))
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("common.cancel"))

    def accept_dialog() -> None:
        if not password_input.text().strip():
            QMessageBox.warning(widget, t("login.err_title"), t("login.err_master_empty"))
            return
        if confirm_input is not None and confirm_input.text() != password_input.text().strip():
            QMessageBox.warning(widget, t("login.err_title"), t("login.err_master_mismatch"))
            return
        dialog.accept()

    buttons.accepted.connect(accept_dialog)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    password_input.setFocus()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    pw = password_input.text().strip()
    widget._master_password_cache = pw
    if remember_password.isChecked():
        try:
            _storage.update_settings({"master_password_dpapi": _secrets.protect_secret(pw)})
        except Exception as exc:
            QMessageBox.warning(
                widget,
                t("login.err_title"),
                t("connection.master_password_store_failed").format(error=exc),
            )
    return pw


def decrypt_saved_password(widget: LoginWidget, prof: dict) -> str | None:
    """Decrypt a saved password and retry if the cached master password is wrong."""
    token = prof.get("password_enc")
    salt = prof.get("password_salt")
    if not token or not salt:
        return ""

    used_cached_master = bool(widget._master_password_cache)
    master = widget._ask_master_password(confirm=False)
    if master is None:
        return None

    try:
        return _crypto.decrypt_with_master(master, token, salt)
    except Exception:
        if used_cached_master:
            widget._master_password_cache = ""
            _storage.update_settings({"master_password_dpapi": ""})
            master = widget._ask_master_password(confirm=False)
            if master is None:
                return None
            try:
                return _crypto.decrypt_with_master(master, token, salt)
            except Exception:
                pass

    widget._master_password_cache = ""
    QMessageBox.critical(widget, t("login.err_title"), t("login.err_master_wrong"))
    return None


def decrypt_profile_password(
    widget: LoginWidget,
    prof: dict,
    *,
    allow_prompt: bool,
) -> str | None:
    keychain_ref = prof.get("password_keychain_ref")
    if keychain_ref:
        try:
            return _secrets.unprotect_keychain_secret(str(keychain_ref))
        except Exception:
            QMessageBox.critical(
                widget,
                t("login.err_title"),
                t("connection.saved_password_unavailable"),
            )
            return None
    token = prof.get("password_dpapi")
    if token:
        try:
            return _secrets.unprotect_secret(str(token))
        except Exception:
            QMessageBox.critical(
                widget,
                t("login.err_title"),
                t("connection.saved_password_unavailable"),
            )
            return None
    if prof.get("password_enc") and prof.get("password_salt"):
        if not allow_prompt:
            return None
        return decrypt_saved_password(widget, prof)
    return ""


def should_prompt_for_password(widget: LoginWidget, prof: dict | None) -> bool:
    """Whether Connect should ask for a transient password.

    Key/agent profiles and providers that declare their own key or
    keyboard-interactive source are never forced through a password
    prompt.  Profiles that explicitly opted out of connect-time prompts
    ("edit-only") are also left alone; the SSH layer then reports the
    missing credential truthfully.
    """
    if widget._password_prompt_policy == "edit-only":
        return False
    key_path = widget.key_path.text().strip()
    if not key_path and isinstance(prof, dict):
        key_path = str(prof.get("key_path") or "").strip()
    return _profiles_svc.password_prompt_recommended(
        widget._profile_system_settings,
        has_key_path=bool(key_path),
    )
