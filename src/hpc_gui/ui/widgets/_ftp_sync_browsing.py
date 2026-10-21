"""FTP synchronized-browsing leaf for the file-manager FTP widget.

Owns ``FtpSyncMixin``: sync roots, navigation guard, toggles, local/remote
directory-change mirroring, pair confirmation, and persistence. Comparison
state refresh triggered from session changes lives in ``_ftp_comparison``;
everything else is reached via ``self``.

Imports Qt plus lower-level config/services/i18n only — never panels, FTP
internals of other leaves, controllers, or other branches.
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import QMessageBox

from hpc_gui.config.file_manager_profile import (
    normalize_file_manager_settings,
    update_profile_file_manager_settings,
)
from hpc_gui.core.i18n import t
from hpc_gui.services.synchronized_browsing import (
    SyncRoots,
    local_to_remote,
    remote_to_local,
)


class FtpSyncMixin:
    """Synchronized-browsing ownership (mixed into ``FtpWidget``)."""

    session: object

    def _session_sync_settings(self) -> dict:
        cfg = (self.session or {}).get("cfg")
        return normalize_file_manager_settings(
            getattr(cfg, "file_manager_settings", None)
        ).get("sync") or {}

    def _set_sync_status(self, reason: str) -> None:
        self._sync_status_reason = reason
        self.btn_sync_browsing.setToolTip(reason or t("ftp.sync_browsing"))

    def _set_sync_checked(self, checked: bool) -> None:
        if self.btn_sync_browsing.isChecked() == checked:
            return
        self.btn_sync_browsing.blockSignals(True)
        try:
            self.btn_sync_browsing.setChecked(checked)
        finally:
            self.btn_sync_browsing.blockSignals(False)

    def _apply_synchronized_state(self) -> None:
        """Reload the sync/compare button state for the current session/profile."""
        self._sync_navigation_guard = False
        self._sync_status_reason = ""
        connected = bool(self.session and self.session.get("connected"))
        self.btn_sync_browsing.setEnabled(connected)
        file_manager = self._session_file_manager()
        sync = file_manager.get("sync") or {}
        self._sync_roots = SyncRoots(
            str(sync.get("local_root", "")),
            str(sync.get("remote_root", "")),
        )
        if not connected:
            self._set_sync_checked(False)
            self._set_sync_status("")
        else:
            enabled = bool(sync.get("enabled"))
            local_root_ok = (
                bool(self._sync_roots.local_root)
                and os.path.isdir(self._sync_roots.local_root)
                and bool(self._sync_roots.remote_root)
            )
            if enabled and local_root_ok:
                self._set_sync_checked(True)
                self._set_sync_status("")
            else:
                self._set_sync_checked(False)
                if enabled and not local_root_ok:
                    self._set_sync_status(t("ftp.sync_local_root_unavailable"))
                else:
                    self._set_sync_status("")
        self._apply_comparison_state(file_manager)

    def _persist_sync_patch(self, patch: dict) -> bool:
        profile_name = str((self.session or {}).get("profile_name") or "").strip()
        if not profile_name:
            return False
        update_profile_file_manager_settings(
            profile_name,
            {"sync": patch},
        )
        return True

    def _confirm_sync_pair(self, local_dir: str, remote_dir: str) -> bool:
        message = "\n".join(
            [
                t("ftp.sync_confirm_question"),
                f"{t('ftp.sync_local_root')}: {local_dir}",
                f"{t('ftp.sync_remote_root')}: {remote_dir}",
            ]
        )
        return QMessageBox.question(
            self,
            t("ftp.sync_browsing"),
            message,
        ) == QMessageBox.StandardButton.Yes

    def _on_sync_browsing_toggled(self, checked: bool) -> None:
        if checked:
            self._enable_synchronized_browsing()
        else:
            self._disable_synchronized_browsing()

    def _enable_synchronized_browsing(self) -> None:
        if not (self.session and self.session.get("connected")):
            self._set_sync_checked(False)
            return
        roots = self._sync_roots
        if roots.local_root and roots.remote_root:
            # Saved pair exists; never navigate as a side effect of toggling.
            if os.path.isdir(roots.local_root):
                self._set_sync_status("")
                if not bool(self._session_sync_settings().get("enabled")):
                    try:
                        self._persist_sync_patch({"enabled": True})
                    except Exception as exc:
                        self._set_sync_checked(False)
                        QMessageBox.warning(self, t("common.error"), str(exc))
                        return
            else:
                # Case C: keep the stored pair, explain, do not enable.
                self._set_sync_status(t("ftp.sync_local_root_unavailable"))
                self._set_sync_checked(False)
            return
        local_dir = str(self.local_panel.current_dir or "")
        remote_dir = str(self.active_remote_panel().current_dir or "").strip()
        if (
            not local_dir
            or not os.path.isdir(local_dir)
            or not remote_dir
        ):
            self._set_sync_checked(False)
            return
        if not self._confirm_sync_pair(local_dir, remote_dir):
            self._set_sync_checked(False)
            return
        try:
            self._persist_sync_patch(
                {
                    "enabled": True,
                    "local_root": local_dir,
                    "remote_root": remote_dir,
                }
            )
        except Exception as exc:
            self._set_sync_checked(False)
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        self._sync_roots = SyncRoots(local_dir, remote_dir)
        self._set_sync_status("")

    def _disable_synchronized_browsing(self) -> None:
        self._sync_navigation_guard = False
        self._set_sync_status("")
        if self.session and self.session.get("connected"):
            saved = self._session_sync_settings()
            if saved.get("enabled"):
                try:
                    self._persist_sync_patch({"enabled": False})
                except Exception as exc:
                    QMessageBox.warning(self, t("common.error"), str(exc))

    def _reset_synchronized_roots(self) -> None:
        if not (self.session and self.session.get("connected")):
            return
        local_dir = str(self.local_panel.current_dir or "")
        remote_dir = str(self.active_remote_panel().current_dir or "").strip()
        if (
            not local_dir
            or not os.path.isdir(local_dir)
            or not remote_dir
        ):
            return
        if not self._confirm_sync_pair(local_dir, remote_dir):
            return
        keep_enabled = bool(self._session_sync_settings().get("enabled"))
        try:
            self._persist_sync_patch(
                {
                    "local_root": local_dir,
                    "remote_root": remote_dir,
                    **({"enabled": True} if keep_enabled else {}),
                }
            )
        except Exception as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        self._sync_roots = SyncRoots(local_dir, remote_dir)

    def _on_synchronized_local_dir_changed(self, path: str) -> None:
        if not self.btn_sync_browsing.isChecked():
            return
        if self._sync_navigation_guard:
            return
        target = local_to_remote(path, self._sync_roots)
        if target is None:
            self._set_sync_status(t("ftp.sync_outside_root"))
            return
        panel = self.active_remote_panel()
        if (panel.current_dir or "").rstrip("/") == target.rstrip("/"):
            return
        self._sync_navigation_guard = True
        try:
            panel.set_dir(target)
        finally:
            self._sync_navigation_guard = False

    def _on_synchronized_remote_dir_changed(self, path: str, panel) -> None:
        if panel is not self.active_remote_panel():
            return
        if not self.btn_sync_browsing.isChecked():
            return
        if self._sync_navigation_guard:
            return
        target = remote_to_local(path, self._sync_roots)
        if target is None:
            self._set_sync_status(t("ftp.sync_remote_outside_root"))
            return
        if not os.path.isdir(target):
            self._set_sync_status(t("ftp.sync_local_root_unavailable"))
            return
        if str(self.local_panel.current_dir or "") == target:
            return
        self._sync_navigation_guard = True
        try:
            self.local_panel.set_dir(target)
        finally:
            self._sync_navigation_guard = False


__all__ = [
    "FtpSyncMixin",
]
