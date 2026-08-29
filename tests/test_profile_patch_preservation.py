"""FM-01 regression tests: profile edits must patch, never rebuild destructively."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.config import storage  # noqa: E402
from hpc_gui.config.storage import merge_profile_patch  # noqa: E402
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog  # noqa: E402
from hpc_gui.ui.widgets.login_widget import LoginWidget  # noqa: E402


def _existing_profile() -> dict:
    return {
        "id": "stable-id",
        "name": "lab",
        "host": "login.example.org",
        "port": 22,
        "username": "user",
        "key_path": "",
        "host_key_policy": "accept-new",
        "x11_forwarding": False,
        "save_password": True,
        "password_enc": "token",
        "password_salt": "salt",
        "system_template_source": {
            "kind": "plugin",
            "plugin_id": "org.hpcclient.truba",
            "profile_id": "truba",
        },
        "file_manager": {"local_start_dir": "/tmp/work", "future_key": 1},
        "jump_host": {"enabled": False},
        "plugin_meta": {"custom": {"nested": True}},
    }


class MergeProfilePatchTests(unittest.TestCase):
    def test_unknown_top_level_key_survives_an_edit(self) -> None:
        merged = merge_profile_patch(
            _existing_profile(),
            {"name": "lab", "host": "new.example.org"},
        )
        self.assertEqual(merged["plugin_meta"], {"custom": {"nested": True}})
        self.assertEqual(merged["jump_host"], {"enabled": False})

    def test_stable_id_survives(self) -> None:
        merged = merge_profile_patch(_existing_profile(), {"name": "renamed"})
        self.assertEqual(merged["id"], "stable-id")

    def test_remove_keys_are_removed_explicitly(self) -> None:
        merged = merge_profile_patch(
            _existing_profile(),
            {},
            remove_keys=("password_enc", "password_salt"),
        )
        self.assertNotIn("password_enc", merged)
        self.assertNotIn("password_salt", merged)
        self.assertIn("file_manager", merged)

    def test_none_existing_starts_from_empty(self) -> None:
        merged = merge_profile_patch(None, {"name": "fresh"})
        self.assertEqual(merged, {"name": "fresh"})


class ProfileStoragePreservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        home = mock.patch.object(Path, "home")
        home.start().return_value = Path(self._dir.name)
        self.addCleanup(home.stop)

    def test_upsert_after_merge_keeps_unknown_keys_and_id(self) -> None:
        storage.upsert_profile(dict(_existing_profile()))
        stored = storage.load_profiles()[0]
        patched = merge_profile_patch(stored, {"host": "other.example.org"})
        storage.upsert_profile(patched)
        saved = storage.load_profiles()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["id"], "stable-id")
        self.assertEqual(saved[0]["host"], "other.example.org")
        self.assertEqual(saved[0]["system_template_source"]["kind"], "plugin")
        self.assertEqual(saved[0]["file_manager"]["future_key"], 1)

    def test_new_profile_gets_one_stable_id(self) -> None:
        fresh = {k: v for k, v in _existing_profile().items() if k != "id"}
        fresh["name"] = "brand-new"
        storage.upsert_profile(fresh)
        first_id = storage.load_profiles()[0]["id"]
        self.assertTrue(first_id)
        again = dict(storage.load_profiles()[0])
        storage.upsert_profile(again)
        self.assertEqual(storage.load_profiles()[0]["id"], first_id)


class ConnectionDialogPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _dialog_collect(self, initial: dict | None = None):
        dialog = ConnectionDialog(initial_profile=dict(initial or {}))
        try:
            return dialog._collect_profile()
        finally:
            dialog.deleteLater()

    def test_unrelated_edit_preserves_provenance_file_manager_and_future_keys(self) -> None:
        collected = self._dialog_collect(_existing_profile())
        assert collected is not None
        self.assertEqual(collected["system_template_source"]["kind"], "plugin")
        self.assertEqual(collected["file_manager"]["local_start_dir"], "/tmp/work")
        self.assertEqual(collected["file_manager"]["future_key"], 1)
        self.assertFalse(collected["jump_host"]["enabled"])
        self.assertEqual(collected["plugin_meta"], {"custom": {"nested": True}})
        # Secret material must not ride along through the dialog result.
        self.assertNotIn("password_dpapi", collected)
        self.assertNotIn("password_enc", collected)
        self.assertNotIn("password_salt", collected)

    def test_applying_builtin_template_clears_stale_plugin_provenance(self) -> None:
        dialog = ConnectionDialog(initial_profile=_existing_profile())
        try:
            dialog._apply_system_template({"name": "Generic Slurm"})
            collected = dialog._collect_profile()
        finally:
            dialog.deleteLater()
        assert collected is not None
        self.assertNotIn("system_template_source", collected)

    def test_no_template_action_preserves_provenance(self) -> None:
        dialog = ConnectionDialog(initial_profile=_existing_profile())
        try:
            dialog.home_dir.setText("/changed/home/{user}")
            collected = dialog._collect_profile()
        finally:
            dialog.deleteLater()
        assert collected is not None
        self.assertEqual(collected["system_template_source"]["plugin_id"], "org.hpcclient.truba")

    def test_saved_provider_edits_preserve_all_quota_sources(self) -> None:
        profile = _existing_profile()
        profile["provider_template"] = {
            "schema_version": 2,
            "storage": [{"id": "home", "label": "Home", "path_template": "/home/{user}"}],
            "quota_sources": [
                {"id": "home", "enabled": True, "consent": True, "backend_id": "", "command_template": "", "scope": "user"},
                {"id": "project", "enabled": False, "command_template": "keep", "scope": "project"},
            ],
        }
        dialog = ConnectionDialog(initial_profile=profile)
        try:
            dialog.storage_rows[0]["path_template"] = "/changed/{user}"
            collected = dialog._collect_profile()
        finally:
            dialog.deleteLater()
        assert collected is not None
        sources = collected["provider_template"]["quota_sources"]
        self.assertEqual([source["id"] for source in sources], ["home", "project"])
        self.assertEqual(sources[1]["command_template"], "keep")
        self.assertEqual(collected["provider_template"]["storage"][0]["path_template"], "/changed/{user}")

    def test_legacy_new_profile_has_blank_local_start(self) -> None:
        collected = self._dialog_collect({"name": "legacy", "host": "h"})
        assert collected is not None
        self.assertEqual(collected["file_manager"].get("local_start_dir", ""), "")


class LoginWidgetSaveProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_save_patches_existing_profile_without_dropping_fields(self) -> None:
        login = LoginWidget()
        try:
            for key in ("name", "host", "port", "username"):
                pass
            login._load_profile_into_fields(_existing_profile())
            login.host.setText("edited.example.org")
            with (
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.load_profiles",
                    return_value=[dict(_existing_profile())],
                ),
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.upsert_profile"
                ) as upsert,
                mock.patch.object(login, "_ask_master_password", return_value=None),
            ):
                self.assertTrue(login.save_profile())

            saved = upsert.call_args.args[0]
            self.assertEqual(saved["host"], "edited.example.org")
            self.assertEqual(saved["id"], "stable-id")
            self.assertEqual(saved["system_template_source"]["kind"], "plugin")
            self.assertEqual(saved["file_manager"]["local_start_dir"], "/tmp/work")
            self.assertEqual(saved["file_manager"]["future_key"], 1)
            self.assertFalse(saved["jump_host"]["enabled"])
            self.assertEqual(saved["plugin_meta"], {"custom": {"nested": True}})
            # Saved password kept without a typed replacement.
            self.assertEqual(saved["password_enc"], "token")
            self.assertEqual(saved["password_salt"], "salt")
        finally:
            login.deleteLater()

    def test_disable_saved_password_removes_secret_fields_only(self) -> None:
        login = LoginWidget()
        try:
            login._load_profile_into_fields(_existing_profile())
            login.cb_save_password.setChecked(False)
            with (
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.load_profiles",
                    return_value=[dict(_existing_profile())],
                ),
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.upsert_profile"
                ) as upsert,
            ):
                self.assertTrue(login.save_profile())

            saved = upsert.call_args.args[0]
            self.assertNotIn("password_enc", saved)
            self.assertNotIn("password_salt", saved)
            self.assertNotIn("password_dpapi", saved)
            self.assertEqual(saved.get("password"), "")
            self.assertEqual(saved["id"], "stable-id")
            self.assertEqual(saved["file_manager"]["local_start_dir"], "/tmp/work")
        finally:
            login.deleteLater()

    def test_rename_preserves_identity_and_removes_old_entry(self) -> None:
        login = LoginWidget()
        try:
            login._editing_profile_original_name = "lab"
            login._load_profile_into_fields(_existing_profile())
            login.profile_name.setText("lab-renamed")
            with (
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.load_profiles",
                    return_value=[dict(_existing_profile())],
                ),
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.upsert_profile"
                ) as upsert,
                mock.patch(
                    "hpc_gui.ui.widgets.login_widget.delete_profile"
                ) as delete_profile,
                mock.patch.object(login, "_ask_master_password", return_value=None),
            ):
                self.assertTrue(login.save_profile())

            saved = upsert.call_args.args[0]
            self.assertEqual(saved["name"], "lab-renamed")
            self.assertEqual(saved["id"], "stable-id")
            delete_profile.assert_called_once_with("lab")
        finally:
            login.deleteLater()

    def test_load_stores_normalized_file_manager_settings_for_runtime(self) -> None:
        login = LoginWidget()
        try:
            login._load_profile_into_fields(_existing_profile())
            settings = login._profile_file_manager_settings
            self.assertEqual(settings["local_start_dir"], "/tmp/work")
            cfg_settings = dict(settings)
            self.assertIsInstance(cfg_settings, dict)
        finally:
            login.deleteLater()


if __name__ == "__main__":
    unittest.main()
