"""Profile persistence and connection-dialog behavior for SSH jump hosts."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hpc_gui.config.jump_host_profile import normalize_jump_host_settings  # noqa: E402


class ProfilePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home_patch = mock.patch.object(Path, "home")
        home_patch.start().return_value = Path(self._tmp.name)
        self.addCleanup(home_patch.stop)

    @pytest.mark.contract
    def test_normalization_rules(self) -> None:
        settings = normalize_jump_host_settings(
            {
                "enabled": "yes",
                "host": " gw ",
                "port": "70000",
                "username": " gate ",
                "key_path": " /keys/gw ",
                "host_key_policy": "accept-anything",
            }
        )
        self.assertFalse(settings["enabled"])
        self.assertEqual(settings["host"], "gw")
        self.assertEqual(settings["port"], 22)
        self.assertEqual(settings["username"], "gate")
        self.assertEqual(settings["key_path"], "/keys/gw")
        self.assertEqual(settings["host_key_policy"], "accept-new")
        ok = normalize_jump_host_settings(
            {"port": 2222, "host_key_policy": "strict"}
        )
        self.assertEqual(ok["port"], 2222)
        self.assertEqual(ok["host_key_policy"], "strict")

    @pytest.mark.integration
    @pytest.mark.regression
    def test_round_trip_persists_without_password_key(self) -> None:
        from hpc_gui.config.storage import load_profiles, upsert_profile

        upsert_profile(
            {
                "name": "lab",
                "host": "c",
                "jump_host": normalize_jump_host_settings(
                    {"enabled": True, "host": "gw", "username": "gate"}
                ),
            }
        )
        stored = load_profiles()[0]["jump_host"]
        self.assertTrue(stored["enabled"])
        self.assertEqual(stored["host"], "gw")
        self.assertNotIn("password", stored)
        self.assertNotIn("password_enc", stored)

    @pytest.mark.integration
    @pytest.mark.regression
    def test_unrelated_edit_preserves_file_manager_and_jump_state(self) -> None:
        from hpc_gui.config.storage import (
            load_profiles,
            merge_profile_patch,
            upsert_profile,
        )

        original = {
            "name": "lab",
            "file_manager": {"local_start_dir": "/w", "future": 1},
            "jump_host": {
                **normalize_jump_host_settings({"enabled": True, "host": "gw"}),
                "unknown_future": {"a": 1},
            },
        }
        upsert_profile(dict(original))
        stored = load_profiles()[0]
        merged = merge_profile_patch(stored, {"host": "new"})
        upsert_profile(merged)
        saved = load_profiles()[0]
        self.assertEqual(saved["host"], "new")
        self.assertEqual(saved["file_manager"]["future"], 1)
        self.assertEqual(saved["jump_host"]["unknown_future"], {"a": 1})
        self.assertTrue(saved["jump_host"]["enabled"])

    @pytest.mark.integration
    def test_dialog_collect_patches_jump_settings(self) -> None:
        from PySide6.QtWidgets import QApplication
        from hpc_gui.core.i18n import load_language
        from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        QApplication.instance() or QApplication([])
        load_language("en")
        initial = {
            "name": "lab",
            "file_manager": {"local_start_dir": "/keep"},
            "jump_host": {"enabled": True, "host": "old-gw"},
        }
        dialog = ConnectionDialog(initial_profile=dict(initial))
        try:
            collected = dialog._collect_profile()
        finally:
            dialog.deleteLater()
        assert collected is not None
        self.assertEqual(collected["jump_host"]["host"], "old-gw")
        self.assertTrue(collected["jump_host"]["enabled"])
        self.assertEqual(collected["file_manager"]["local_start_dir"], "/keep")
