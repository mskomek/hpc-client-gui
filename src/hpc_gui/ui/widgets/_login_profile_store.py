"""Login profile persistence (Wave M01).

Qt ownership of the login widget's profile save flow: building the
known-field patch, secret-storage branching (keychain / OS store /
master-password) and remote-default updates. Reads stored profiles through
the canonical storage module with call-time attribute lookup so tests can
patch the canonical home. The facade keeps thin delegating methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from hpc_gui.config import storage as _storage
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.core import crypto_master as _crypto
from hpc_gui.core import secret_store as _secrets
from hpc_gui.core import history as _history
from hpc_gui.core.i18n import t
from hpc_gui.ui.widgets import _login_profiles as _profiles

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime cycle
    from hpc_gui.ui.widgets.login_widget import LoginWidget


def save_profile(widget: LoginWidget) -> bool:
    name = widget.profile_name.text().strip()
    if not name:
        username = widget.username.text().strip()
        host = widget.host.text().strip()
        name = f"{username}@{host}" if username else host
        widget.profile_name.setText(name)

    try:
        port = int(widget.port.text().strip() or "22")
    except ValueError:
        QMessageBox.warning(widget, t("login.err_title"), t("login.err_port_numeric"))
        return False

    # Resolve the stored profile so the save patches known fields onto
    # it instead of discarding unrelated keys (plugin provenance,
    # file_manager, jump_host, ...).
    original_name = getattr(widget, "_editing_profile_original_name", "").strip()
    existing_name = original_name or name
    existing = next(
        (p for p in _storage.load_profiles() if p.get("name") == existing_name),
        None,
    )

    patch = _profiles.profile_patch_base(widget, port, name)

    # Password storage (encrypted):
    # - Do not store plaintext in config.
    # - When saving with "save password", ask for a master password and encrypt.
    remove_keys: list[str] = []
    if widget.cb_save_password.isChecked():
        plain = widget.password.text() or ""
        current = existing or next(
            (p for p in _storage.load_profiles() if p.get("name") == name),
            None,
        )
        if _secrets.keychain_available():
            if not plain and current and current.get("password_keychain_ref"):
                plain = widget._decrypt_profile_password(current, allow_prompt=False)
                if plain is None:
                    return False
            try:
                if plain:
                    patch["password_keychain_ref"] = _secrets.protect_keychain_secret(
                        plain,
                        str(current.get("password_keychain_ref"))
                        if current and current.get("password_keychain_ref")
                        else None,
                    )
            except Exception as exc:
                QMessageBox.critical(
                    widget,
                    t("login.err_title"),
                    t("connection.password_store_failed").format(error=exc),
                )
                return False
        elif (
            widget._password_prompt_policy == "edit-only"
            and _secrets.is_available()
        ):
            # Existing profiles may have been encrypted with a master
            # password.  Convert them once to Windows credential
            # protection when the user chooses not to be prompted while
            # connecting, so future double-click connections stay prompt-free.
            if not plain and current and current.get("password_enc"):
                plain = widget._decrypt_profile_password(
                    current,
                    allow_prompt=True,
                )
                if plain is None:
                    return False
            try:
                if plain:
                    patch["password_dpapi"] = _secrets.protect_secret(plain)
            except Exception as exc:
                QMessageBox.critical(
                    widget,
                    t("login.err_title"),
                    t("connection.password_store_failed").format(
                        error=exc
                    ),
                )
                return False
        elif plain:
            master = widget._ask_master_password(confirm=True)
            if master is None:
                return False
            enc = _crypto.encrypt_with_master(master, plain)
            patch["password_enc"] = enc.token
            patch["password_salt"] = enc.salt
        else:
            # keep existing encrypted password if present (when editing profile)
            if current:
                for key in (
                    "password_keychain_ref",
                    "password_dpapi",
                    "password_enc",
                    "password_salt",
                ):
                    if current.get(key):
                        patch[key] = current.get(key)

        # Always clear legacy plaintext field
        patch["password"] = ""
    else:
        patch["password"] = ""
        if existing and existing.get("password_keychain_ref"):
            _secrets.delete_keychain_secret(str(existing["password_keychain_ref"]))
        remove_keys.extend(
            [
                "password_keychain_ref",
                "password_enc",
                "password_salt",
                "password_dpapi",
            ]
        )

    prof = _storage.merge_profile_patch(existing, patch, remove_keys=remove_keys)
    # Only one secret scheme may survive a save.
    if "password_keychain_ref" in prof:
        prof.pop("password_dpapi", None)
        prof.pop("password_enc", None)
        prof.pop("password_salt", None)
    elif "password_dpapi" in prof:
        prof.pop("password_enc", None)
        prof.pop("password_salt", None)
    elif "password_enc" in prof:
        prof.pop("password_dpapi", None)
    old_keychain_ref = str((existing or {}).get("password_keychain_ref") or "")
    new_keychain_ref = str(prof.get("password_keychain_ref") or "")
    if old_keychain_ref and old_keychain_ref != new_keychain_ref:
        _secrets.delete_keychain_secret(old_keychain_ref)
    _storage.upsert_profile(prof)
    if original_name and original_name != name:
        _storage.delete_profile(original_name)
    _profiles.refresh_profiles(widget, select_name=name)
    _history.append_event({"type": "profile_save", "name": name})
    widget.append_console(t("login.profile_saved").format(name=name))
    return True


def update_active_profile_remote_defaults(
    widget: LoginWidget,
    scratch_dir: str,
    home_dir: str,
) -> bool:
    name = str(
        (widget._session or {}).get("profile_name")
        or widget.profile_name.text()
        or ""
    ).strip()
    if not name:
        return False
    profile = widget._load_profile_by_name(name)
    if not profile:
        return False
    system = normalize_system_settings(profile.get("system"))
    if scratch_dir.strip():
        system["scratch_dir"] = scratch_dir.strip()
    if home_dir.strip():
        system["home_dir"] = home_dir.strip()
    profile = dict(profile)
    profile["system"] = system
    _storage.upsert_profile(profile)
    widget._profile_system_settings = dict(system)
    cfg = (widget._session or {}).get("cfg")
    if cfg is not None:
        cfg.system_settings = dict(system)
    _profiles.refresh_profiles(widget, select_name=name)
    widget.session_changed.emit(widget._session)
    return True
