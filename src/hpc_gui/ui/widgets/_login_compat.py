"""Legacy login-widget exports and patch routes for the extracted leaves."""

from __future__ import annotations

import sys
from importlib import import_module

from hpc_gui.core._legacy_patch_targets import enable_legacy_patch_targets


LEGACY_EXPORTS = {
    "QCoreApplication": ("PySide6.QtCore", "QCoreApplication"),
    "QObject": ("PySide6.QtCore", "QObject"),
    "QThread": ("PySide6.QtCore", "QThread"),
    "QEvent": ("PySide6.QtCore", "QEvent"),
    "QFontDatabase": ("PySide6.QtGui", "QFontDatabase"),
    "QTextCursor": ("PySide6.QtGui", "QTextCursor"),
    "QApplication": ("PySide6.QtWidgets", "QApplication"),
    "QFileDialog": ("PySide6.QtWidgets", "QFileDialog"),
    "QMenu": ("PySide6.QtWidgets", "QMenu"),
    "QDialogButtonBox": ("PySide6.QtWidgets", "QDialogButtonBox"),
    "QVBoxLayout": ("PySide6.QtWidgets", "QVBoxLayout"),
    "QFormLayout": ("PySide6.QtWidgets", "QFormLayout"),
    "QHBoxLayout": ("PySide6.QtWidgets", "QHBoxLayout"),
    "QLineEdit": ("PySide6.QtWidgets", "QLineEdit"),
    "QPushButton": ("PySide6.QtWidgets", "QPushButton"),
    "QCheckBox": ("PySide6.QtWidgets", "QCheckBox"),
    "QLabel": ("PySide6.QtWidgets", "QLabel"),
    "QSplitter": ("PySide6.QtWidgets", "QSplitter"),
    "QSpinBox": ("PySide6.QtWidgets", "QSpinBox"),
    "QDoubleSpinBox": ("PySide6.QtWidgets", "QDoubleSpinBox"),
    "t": ("hpc_gui.core.i18n", "t"),
    "describe_connection_error": ("hpc_gui.core.ui_errors", "describe_connection_error"),
    "show_exception": ("hpc_gui.core.ui_errors", "show_exception"),
    "merge_profile_patch": ("hpc_gui.config.storage", "merge_profile_patch"),
    "coerce_profile_transfer_parallelism": ("hpc_gui.config.storage", "coerce_profile_transfer_parallelism"),
    "coerce_profile_ssh_timeout": ("hpc_gui.config.storage", "coerce_profile_ssh_timeout"),
    "patch_file_manager_settings": ("hpc_gui.config.file_manager_profile", "patch_file_manager_settings"),
    "patch_jump_host_settings": ("hpc_gui.config.jump_host_profile", "patch_jump_host_settings"),
    "jump_info_from_settings": ("hpc_gui.ssh.jump", "jump_info_from_settings"),
    "normalize_auth_methods": ("hpc_gui.services.connection_profile_service", "normalize_auth_methods"),
    "password_prompt_recommended": ("hpc_gui.services.connection_profile_service", "password_prompt_recommended"),
    "append_log": ("hpc_gui.core.logging", "append_log"),
    "MockSlurmBackend": ("hpc_gui.services.slurm_mock", "MockSlurmBackend"),
    "duplicate_profile": ("hpc_gui.services.profile_duplicate", "duplicate_profile"),
    "MockFilesBackend": ("hpc_gui.services.files_mock", "MockFilesBackend"),
    "HostKeyChangedError": ("hpc_gui.ssh.client", "HostKeyChangedError"),
    "HostKeyInfo": ("hpc_gui.ssh.client", "HostKeyInfo"),
    "HostKeyRejectedError": ("hpc_gui.ssh.client", "HostKeyRejectedError"),
    "SSHClientWrapper": ("hpc_gui.ssh.client", "SSHClientWrapper"),
    "SSHConnInfo": ("hpc_gui.ssh.client", "SSHConnInfo"),
    "coerce_keepalive_interval": ("hpc_gui.ssh.client", "coerce_keepalive_interval"),
    "SSHFilesBackend": ("hpc_gui.services.files_ssh", "SSHFilesBackend"),
    "SSHSlurmBackend": ("hpc_gui.services.slurm_ssh", "SSHSlurmBackend"),
    "encrypt_with_master": ("hpc_gui.core.crypto_master", "encrypt_with_master"),
    "decrypt_with_master": ("hpc_gui.core.crypto_master", "decrypt_with_master"),
    "keychain_available": ("hpc_gui.core.secret_store", "keychain_available"),
    "protect_keychain_secret": ("hpc_gui.core.secret_store", "protect_keychain_secret"),
    "unprotect_keychain_secret": ("hpc_gui.core.secret_store", "unprotect_keychain_secret"),
    "delete_keychain_secret": ("hpc_gui.core.secret_store", "delete_keychain_secret"),
}

_PATCH_TARGETS = {
    "load_profiles": (("hpc_gui.config.storage", "load_profiles"),),
    "load_settings": (("hpc_gui.config.storage", "load_settings"),),
    "upsert_profile": (("hpc_gui.config.storage", "upsert_profile"),),
    "update_settings": (("hpc_gui.config.storage", "update_settings"),),
    "delete_profile": (("hpc_gui.config.storage", "delete_profile"),),
    "os_secret_store_available": (("hpc_gui.core.secret_store", "is_available"),),
    "keychain_available": (("hpc_gui.core.secret_store", "keychain_available"),),
    "protect_secret": (("hpc_gui.core.secret_store", "protect_secret"),),
    "unprotect_secret": (("hpc_gui.core.secret_store", "unprotect_secret"),),
    "protect_keychain_secret": (
        ("hpc_gui.core.secret_store", "protect_keychain_secret"),
    ),
    "unprotect_keychain_secret": (
        ("hpc_gui.core.secret_store", "unprotect_keychain_secret"),
    ),
    "delete_keychain_secret": (
        ("hpc_gui.core.secret_store", "delete_keychain_secret"),
    ),
    "append_event": (("hpc_gui.core.history", "append_event"),),
    "SSHClientWrapper": (
        ("hpc_gui.ssh.client", "SSHClientWrapper"),
    ),
    "QDialog": (("hpc_gui.ui.widgets._login_secrets", "QDialog"),),
    "QInputDialog": (
        ("hpc_gui.ui.widgets._login_profiles", "QInputDialog"),
        ("hpc_gui.ui.widgets._login_connect", "QInputDialog"),
    ),
    "QMessageBox": tuple(
        (f"hpc_gui.ui.widgets.{leaf}", "QMessageBox")
        for leaf in (
            "_login_profiles",
            "_login_profile_store",
            "_login_secrets",
            "_login_connect",
            "_login_connection_worker",
        )
    ),
}


def resolve_legacy_export(name: str):
    destination = LEGACY_EXPORTS.get(name)
    if destination is None:
        targets = _PATCH_TARGETS.get(name)
        if not targets:
            raise AttributeError(name) from None
        destination = targets[0]
    module_name, attribute = destination
    return getattr(import_module(module_name), attribute)


def install_legacy_login_exports(module_name: str) -> None:
    module = sys.modules[module_name]
    module.__getattr__ = resolve_legacy_export
    module.__dir__ = lambda: sorted(
        set(module.__dict__) | set(LEGACY_EXPORTS) | set(_PATCH_TARGETS)
    )
    enable_legacy_patch_targets(module_name, _PATCH_TARGETS)


__all__ = ["LEGACY_EXPORTS", "install_legacy_login_exports", "resolve_legacy_export"]
