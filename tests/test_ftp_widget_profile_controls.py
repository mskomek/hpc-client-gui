"""Focused FTP widget tests for profile controls behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from unittest.mock import patch
import pytest
from PySide6.QtWidgets import QApplication
from hpc_gui.services.transfer_mode import ASCII, AUTO, BINARY
from hpc_gui.config.system_profile import GENERIC_SLURM_DEFAULTS
from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog
from hpc_gui.ui.widgets.login_widget import LoginWidget
from ftp_widget_test_support import FtpWidgetTestCase, _Files


class FtpWidgetProfileControlsTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_session_uses_configured_scratch_and_home_roots(self) -> None:
        files = _Files()
        cfg = SimpleNamespace(
            username="alice",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
        )
        self.widget.set_session({"connected": True, "files": files, "cfg": cfg})
        self.assertEqual(self.widget.panel_scratch.current_dir, "/arf/scratch/alice")
        self.assertEqual(self.widget.panel_home.current_dir, "/arf/home/alice")

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_context_menu_can_set_current_scratch_as_profile_default(self) -> None:
        cfg = SimpleNamespace(
            username="alice",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
        )
        self.widget.set_session(
            {
                "connected": True,
                "files": _Files(),
                "cfg": cfg,
                "profile_name": "alice@truba",
            }
        )
        self.widget.panel_scratch.current_dir = "/arf/scratch/alice/project"
        emitted = []
        self.widget.defaultPathsRequested.connect(
            lambda scratch, home: emitted.append((scratch, home))
        )

        self.widget.panel_scratch.set_default_requested.emit()

        self.assertEqual(
            emitted,
            [("/arf/scratch/alice/project", "/arf/home/alice")],
        )

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_settings_edit_and_reset_profile_remote_defaults(self) -> None:
        cfg = SimpleNamespace(
            username="alice",
            system_settings={
                "scratch_dir": "/custom/scratch/{user}",
                "home_dir": "/custom/home/{user}",
            },
        )
        updates = []
        dialog = SettingsDialog(
            session={
                "connected": True,
                "profile_name": "alice@truba",
                "cfg": cfg,
            },
            update_remote_defaults=lambda scratch, home: updates.append((scratch, home)),
        )
        try:
            self.assertTrue(dialog.ftp_scratch_dir.isEnabled())
            self.assertEqual(
                dialog.ftp_scratch_dir.text(),
                "/custom/scratch/{user}",
            )
            dialog._reset_ftp_defaults()
            self.assertEqual(updates, [])
            self.assertEqual(
                dialog.ftp_home_dir.text(),
                GENERIC_SLURM_DEFAULTS["home_dir"],
            )
            with patch("hpc_gui.ui.dialogs.settings_dialog.update_settings"):
                dialog.btn_apply.click()
            self.assertEqual(
                updates,
                [
                    (
                        GENERIC_SLURM_DEFAULTS["scratch_dir"],
                        GENERIC_SLURM_DEFAULTS["home_dir"],
                    )
                ],
            )
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_settings_apply_persists_without_closing_and_close_rejects(self) -> None:
        dialog = SettingsDialog()
        try:
            dialog.show()
            QApplication.processEvents()
            # FM-04: the global transfer-parallelism editor was removed;
            # per-profile value is the single user-facing source of truth.
            dialog.cb_upload_preflight_confirmation.setChecked(False)
            with patch("hpc_gui.ui.dialogs.settings_dialog.update_settings") as update:
                dialog.btn_apply.click()

            update.assert_called_once()
            self.assertNotIn(
                "transfer_parallelism",
                update.call_args.args[0],
                "Settings dialog must not write a global transfer_parallelism value",
            )
            self.assertEqual(
                update.call_args.args[0]["upload_preflight_confirmation_enabled"],
                False,
            )
            self.assertTrue(dialog.isVisible())
            self.assertEqual(dialog.btn_apply.text(), "Apply")
            self.assertEqual(dialog.btn_close.text(), "Close")

            dialog.btn_close.click()
            self.assertFalse(dialog.isVisible())
            self.assertEqual(dialog.result(), SettingsDialog.DialogCode.Rejected)
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_profile_remote_controls_disabled_without_active_profile(self) -> None:
        dialog = SettingsDialog()
        try:
            self.assertFalse(dialog.ftp_scratch_dir.isEnabled())
            self.assertFalse(dialog.ftp_home_dir.isEnabled())
            self.assertFalse(dialog.btn_ftp_reset_defaults.isEnabled())
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_profile_update_preserves_other_fields_and_refreshes_session(self) -> None:
        login = LoginWidget()
        cfg = SimpleNamespace(
            system_settings={
                "scratch_dir": "/old/scratch",
                "home_dir": "/old/home",
            }
        )
        login._session = {
            "connected": True,
            "profile_name": "alice@truba",
            "cfg": cfg,
        }
        original = {
            "name": "alice@truba",
            "host": "arf.truba.gov.tr",
            "password_dpapi": "protected-secret",
            "system": {
                "scratch_dir": "/old/scratch",
                "home_dir": "/old/home",
                "status_command": "lssrv-custom",
            },
        }
        emitted = []
        login.session_changed.connect(lambda session: emitted.append(session))
        try:
            with (
                patch.object(
                    login,
                    "_load_profile_by_name",
                    return_value=original,
                ),
                patch.object(login, "refresh_profiles"),
                patch("hpc_gui.ui.widgets.login_widget.upsert_profile") as save_profile,
            ):
                self.assertTrue(
                    login.update_active_profile_remote_defaults(
                        "/new/scratch",
                        "/new/home",
                    )
                )
            saved = save_profile.call_args.args[0]
            self.assertEqual(saved["password_dpapi"], "protected-secret")
            self.assertEqual(saved["system"]["status_command"], "lssrv-custom")
            self.assertEqual(saved["system"]["scratch_dir"], "/new/scratch")
            self.assertEqual(cfg.system_settings["home_dir"], "/new/home")
            self.assertEqual(emitted[-1], login._session)
        finally:
            login.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_settings_offer_exact_transfer_modes_and_default_auto(self) -> None:
        with patch(
            "hpc_gui.ui.dialogs.settings_dialog.get_ftp_transfer_type",
            return_value=AUTO,
        ):
            dialog = SettingsDialog()
            try:
                self.assertEqual(
                    [
                        dialog.cb_ftp_transfer_type.itemData(index)
                        for index in range(dialog.cb_ftp_transfer_type.count())
                    ],
                    [AUTO, BINARY, ASCII],
                )
                self.assertEqual(dialog.cb_ftp_transfer_type.currentData(), AUTO)
            finally:
                dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_settings_lists_and_clears_file_associations(self) -> None:
        with patch(
            "hpc_gui.ui.dialogs.settings_dialog.get_file_associations",
            return_value={".slurm": r"C:\Tools\editor.exe"},
        ):
            dialog = SettingsDialog()
        try:
            self.assertEqual(dialog.file_associations_list.count(), 1)
            self.assertIn(".slurm", dialog.file_associations_list.item(0).text())
            dialog.file_associations_list.setCurrentRow(0)
            with patch(
                "hpc_gui.ui.dialogs.settings_dialog.clear_file_association",
                return_value={},
            ) as clear_assoc:
                dialog._clear_selected_file_association()
            clear_assoc.assert_called_once_with(".slurm")
            self.assertEqual(dialog.file_associations_list.count(), 0)
        finally:
            dialog.deleteLater()
