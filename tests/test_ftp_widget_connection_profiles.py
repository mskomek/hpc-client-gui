from __future__ import annotations

from support.ftp_widget_test_support import (
    ASCII,
    AUTO,
    BINARY,
    ConnectionDialog,
    FtpWidgetTestCase,
    GENERIC_SLURM_DEFAULTS,
    LoginWidget,
    SettingsDialog,
    patch,
    pytest,
    save_user_system_template,
    t,
)

class FtpWidgetTests(FtpWidgetTestCase):
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
    def test_connection_dialog_applies_generic_slurm_template_from_menu(self) -> None:
        dialog = ConnectionDialog()
        try:
            dialog.scratch_dir.setText("/custom/scratch")
            dialog.home_dir.setText("/custom/home")

            root_menu = dialog.btn_system_templates.menu()
            self.assertIsNotNone(root_menu)
            generic_menu = root_menu.actions()[0].menu()
            self.assertIsNotNone(generic_menu)
            self.assertEqual(root_menu.actions()[0].text(), "Generic Slurm")
            generic_menu.actions()[0].trigger()

            self.assertEqual(dialog.system_name.text(), "Generic Slurm")
            self.assertEqual(dialog.scratch_dir.text(), GENERIC_SLURM_DEFAULTS["scratch_dir"])
            self.assertEqual(dialog.home_dir.text(), GENERIC_SLURM_DEFAULTS["home_dir"])
        finally:
            dialog.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_connection_dialog_advanced_settings_collapses_without_losing_values(self) -> None:
        dialog = ConnectionDialog()
        try:
            dialog.sp_transfer_parallelism.setValue(4)
            dialog.squeue_command.setText("squeue --custom")
            self.assertTrue(dialog.advanced_body.isHidden())

            dialog.advanced_button.click()
            self.assertFalse(dialog.advanced_body.isHidden())
            dialog.advanced_button.click()
            self.assertTrue(dialog.advanced_body.isHidden())

            profile = dialog._collect_profile()
            self.assertEqual(profile["transfer_parallelism"], 4)
            self.assertEqual(profile["system"]["squeue_command"], "squeue --custom")
        finally:
            dialog.deleteLater()
    @pytest.mark.contract
    @pytest.mark.regression
    def test_connection_dialog_round_trips_advanced_profile_values(self) -> None:
        profile = {
            "name": "example",
            "host": "hpc.example.org",
            "port": 2222,
            "username": "researcher",
            "key_path": "C:/keys/example",
            "host_key_policy": "strict",
            "x11_forwarding": True,
            "cli_allowed": True,
            "keepalive_interval_seconds": 90,
            "transfer_parallelism": 4,
            "ssh_timeout": 12.5,
            "system": {
                "name": "Example HPC",
                "scratch_dir": "/scratch/{user}",
                "home_dir": "/home/{user}",
                "squeue_command": "squeue --custom",
                "sbatch_command": "sbatch --custom",
                "scancel_command": "scancel --custom",
                "sacct_command": "sacct --custom",
                "scontrol_command": "scontrol --custom",
                "status_command": "status --custom",
                "active_job_ids_command": "jobs --custom",
                "job_state_command": "state --custom",
            },
        }
        dialog = ConnectionDialog(initial_profile=profile)
        try:
            self.assertTrue(dialog.advanced_body.isHidden())
            collected = dialog._collect_profile()
            self.assertEqual(collected["port"], 2222)
            self.assertEqual(collected["transfer_parallelism"], 4)
            self.assertEqual(collected["ssh_timeout"], 12.5)
            self.assertEqual(collected["keepalive_interval_seconds"], 90)
            self.assertEqual(collected["system"]["scratch_dir"], "/scratch/{user}")
            self.assertEqual(collected["system"]["home_dir"], "/home/{user}")
            self.assertEqual(collected["system"]["status_command"], "status --custom")

            dialog.advanced_button.click()
            dialog.sp_transfer_parallelism.setValue(5)
            changed = dialog._collect_profile()
            self.assertEqual(changed["transfer_parallelism"], 5)
            self.assertEqual(changed["system"]["squeue_command"], "squeue --custom")
        finally:
            dialog.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    def test_connection_dialog_has_room_for_advanced_commands(self) -> None:
        dialog = ConnectionDialog()
        try:
            self.assertGreaterEqual(dialog.minimumWidth(), 720)
        finally:
            dialog.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_connection_dialog_can_remember_password_without_connect_prompts(self) -> None:
        dialog = ConnectionDialog()
        try:
            self.assertFalse(dialog.cb_edit_only_password.isEnabled())
            dialog.cb_save_password.setChecked(True)
            dialog.cb_edit_only_password.setChecked(True)

            profile = dialog._collect_profile()

            self.assertIsNotNone(profile)
            self.assertEqual(profile["password_prompt_policy"], "edit-only")
            self.assertEqual(
                dialog.cb_edit_only_password.text(),
                t("connection.password_no_prompt"),
            )
        finally:
            dialog.deleteLater()
    @pytest.mark.contract
    @pytest.mark.regression
    def test_remembered_profile_is_migrated_to_prompt_free_windows_storage(self) -> None:
        legacy_profile = {
            "name": "truba",
            "host": "login.truba.gov.tr",
            "password_enc": "legacy-token",
            "password_salt": "legacy-salt",
        }
        login = LoginWidget()
        try:
            login.profile_name.setText("truba")
            login.host.setText("login.truba.gov.tr")
            login.cb_save_password.setChecked(True)
            login._password_prompt_policy = "edit-only"

            with (
                patch(
                    "hpc_gui.ui.widgets.login_widget.load_profiles",
                    return_value=[legacy_profile],
                ),
                patch(
                    "hpc_gui.ui.widgets.login_widget.os_secret_store_available",
                    return_value=True,
                ),
                patch.object(
                    login,
                    "_decrypt_profile_password",
                    return_value="ssh-password",
                ) as decrypt_password,
                patch(
                    "hpc_gui.ui.widgets.login_widget.protect_secret",
                    return_value="windows-protected-password",
                ),
                patch("hpc_gui.ui.widgets.login_widget.upsert_profile") as save_profile,
            ):
                self.assertTrue(login.save_profile())

            decrypt_password.assert_called_once_with(
                legacy_profile,
                allow_prompt=True,
            )
            saved = save_profile.call_args.args[0]
            self.assertEqual(saved["password_dpapi"], "windows-protected-password")
            self.assertNotIn("password_enc", saved)
            self.assertNotIn("password_salt", saved)
        finally:
            login.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_saved_master_password_is_reused_without_showing_a_prompt(self) -> None:
        login = LoginWidget()
        try:
            with (
                patch(
                    "hpc_gui.ui.widgets.login_widget.load_settings",
                    return_value={"master_password_dpapi": "protected-master"},
                ),
                patch(
                    "hpc_gui.ui.widgets.login_widget.unprotect_secret",
                    return_value="master-password",
                ) as decrypt_master,
                patch("hpc_gui.ui.widgets.login_widget.QDialog.exec") as show_dialog,
            ):
                self.assertEqual(
                    login._ask_master_password(confirm=False),
                    "master-password",
                )

            decrypt_master.assert_called_once_with("protected-master")
            show_dialog.assert_not_called()
        finally:
            login.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_connection_dialog_saves_current_system_as_user_template(self) -> None:
        dialog = ConnectionDialog()
        try:
            dialog.system_name.setText("My Cluster")
            dialog.scratch_dir.setText("/work/{user}")
            dialog.home_dir.setText("/home/{user}")
            with (
                patch(
                    "hpc_gui.ui.dialogs.connection_dialog.QInputDialog.getText",
                    return_value=("My Cluster", True),
                ),
                patch(
                    "hpc_gui.ui.dialogs._connection_dialog_templates.save_user_system_template",
                    return_value=dict(GENERIC_SLURM_DEFAULTS, name="My Cluster"),
                ) as save_template,
                patch(
                    "hpc_gui.ui.dialogs._connection_dialog_templates.load_user_system_templates",
                    return_value=[],
                ),
            ):
                dialog._save_current_system_template()

            save_template.assert_called_once()
            name, values = save_template.call_args.args
            self.assertEqual(name, "My Cluster")
            self.assertEqual(values["scratch_dir"], "/work/{user}")
            self.assertEqual(values["home_dir"], "/home/{user}")
        finally:
            dialog.deleteLater()
    @pytest.mark.contract
    @pytest.mark.regression
    def test_system_template_save_syncs_structured_provider_edits(self) -> None:
        dialog = ConnectionDialog()
        try:
            dialog._provider_template = {
                "storage": [{"id": "home", "path_template": "/old/{user}"}],
                "quota_sources": [{"id": "q1", "enabled": True, "command_template": "old"}],
            }
            dialog.storage_rows = [{"id": "home", "path_template": "/new/{user}"}]
            dialog.quota_command.setText("")
            with (
                patch(
                    "hpc_gui.ui.dialogs.connection_dialog.QInputDialog.getText",
                    return_value=("Structured", True),
                ),
                patch("hpc_gui.ui.dialogs._connection_dialog_templates.save_user_system_template") as save_template,
            ):
                dialog._save_current_system_template()
            saved = save_template.call_args.args[1]["provider_template"]
            self.assertEqual(saved["storage"][0]["path_template"], "/new/{user}")
            self.assertEqual(saved["quota_sources"][0]["command_template"], "")
        finally:
            dialog.deleteLater()
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_user_system_template_persists_by_name(self) -> None:
        saved_settings = {"system_templates": []}

        def fake_update(patch_data):
            saved_settings.update(patch_data)
            return saved_settings

        with (
            patch(
                "hpc_gui.config.system_profile.load_settings",
                side_effect=lambda: saved_settings,
            ),
            patch(
                "hpc_gui.config.system_profile.update_settings",
                side_effect=fake_update,
            ) as update,
        ):
            first = save_user_system_template(
                "My Cluster",
                {
                    "name": "ignored",
                    "scratch_dir": "/work/{user}",
                    "home_dir": "/home/{user}",
                },
            )
            second = save_user_system_template(
                "my cluster",
                {
                    "scratch_dir": "/new/work",
                    "home_dir": "/new/home",
                },
            )

        self.assertEqual(first["name"], "My Cluster")
        self.assertEqual(second["name"], "my cluster")
        self.assertEqual(len(saved_settings["system_templates"]), 1)
        self.assertEqual(saved_settings["system_templates"][0]["scratch_dir"], "/new/work")
        self.assertGreaterEqual(update.call_count, 2)
