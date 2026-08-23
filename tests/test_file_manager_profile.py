"""FM-01 tests: profile-scoped file-manager settings and local start dir."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.config.file_manager_profile import (  # noqa: E402
    normalize_file_manager_settings,
    patch_file_manager_settings,
)
from hpc_gui.config.models import SSHConfig  # noqa: E402


class NormalizeFileManagerSettingsTests(unittest.TestCase):
    def _expected_defaults(self) -> dict:
        return normalize_file_manager_settings(None)

    def test_missing_file_manager_gives_defaults(self) -> None:
        self.assertEqual(
            normalize_file_manager_settings(None),
            self._expected_defaults(),
        )

    def test_malformed_input_gives_safe_defaults(self) -> None:
        self.assertEqual(
            normalize_file_manager_settings("not-a-dict"),
            self._expected_defaults(),
        )
        self.assertEqual(
            normalize_file_manager_settings({"local_start_dir": 123})["local_start_dir"],
            "",
        )

    def test_local_start_dir_is_stripped(self) -> None:
        self.assertEqual(
            normalize_file_manager_settings({"local_start_dir": "  /tmp/x  "})["local_start_dir"],
            "/tmp/x",
        )

    def test_unknown_nested_keys_are_retained_by_patch(self) -> None:
        patched = patch_file_manager_settings(
            {"local_start_dir": "/old", "sync_root": "/remote"},
            {"local_start_dir": "/new"},
        )
        self.assertEqual(patched["local_start_dir"], "/new")
        self.assertEqual(patched["sync_root"], "/remote")


class SSHConfigRuntimeTests(unittest.TestCase):
    def test_default_runtime_config_has_empty_file_manager_settings(self) -> None:
        cfg = SSHConfig()
        self.assertEqual(cfg.file_manager_settings, {})

    def test_mock_session_carries_file_manager_settings(self) -> None:
        # The mock connection path builds the same SSHConfig dataclass.
        cfg = SSHConfig(
            host="mock",
            file_manager_settings={"local_start_dir": "/tmp/work"},
        )
        self.assertEqual(cfg.file_manager_settings["local_start_dir"], "/tmp/work")


class FtpWidgetLocalStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _widget_with_session(self, cfg):
        from hpc_gui.core.i18n import load_language
        from hpc_gui.services.files_mock import MockFilesBackend
        from hpc_gui.services.transfer_mode import AUTO
        from hpc_gui.ui.widgets.ftp_widget import FtpWidget

        load_language("en")
        state_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
            return_value={
                "local_dir": os.getcwd(),
                "active_remote": "scratch",
                "splitter_sizes": [500, 500],
            },
        )
        type_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_transfer_type",
            return_value=AUTO,
        )
        update_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.update_ftp_state",
            return_value={},
        )
        state_patch.start()
        type_patch.start()
        update_patch.start()
        self.addCleanup(state_patch.stop)
        self.addCleanup(type_patch.stop)
        self.addCleanup(update_patch.stop)
        widget = FtpWidget()
        self.addCleanup(widget.shutdown)
        self.addCleanup(widget.deleteLater)
        session = {
            "connected": True,
            "files": MockFilesBackend(),
            "cfg": cfg,
            "profile_name": "lab",
        }
        widget.set_session(session)
        return widget

    def test_valid_profile_local_folder_navigates_at_session_set(self) -> None:
        with tempfile.TemporaryDirectory() as start:
            cfg = SimpleNamespace(
                username="user",
                system_settings={
                    "scratch_dir": "/arf/scratch/{user}",
                    "home_dir": "/arf/home/{user}",
                },
                file_manager_settings={"local_start_dir": start},
            )
            widget = self._widget_with_session(cfg)
            self.assertEqual(Path(widget.local_panel.current_dir), Path(start))

    def test_missing_local_folder_keeps_global_behavior_without_modal(self) -> None:
        cfg = SimpleNamespace(
            username="user",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
            file_manager_settings={"local_start_dir": str(Path("Z:/definitely-missing"))},
        )
        global_dir = os.getcwd()
        widget = self._widget_with_session(cfg)
        self.assertEqual(widget.local_panel.current_dir, global_dir)

    def test_missing_file_manager_key_is_legacy_behavior(self) -> None:
        cfg = SimpleNamespace(
            username="user",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
            file_manager_settings={},
        )
        widget = self._widget_with_session(cfg)
        self.assertEqual(widget.local_panel.current_dir, os.getcwd())

    def test_profiles_carry_different_local_start_folders(self) -> None:
        with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
            base = {
                "username": "user",
                "system_settings": {
                    "scratch_dir": "/arf/scratch/{user}",
                    "home_dir": "/arf/home/{user}",
                },
            }
            cfg_a = SimpleNamespace(**base, file_manager_settings={"local_start_dir": dir_a})
            cfg_b = SimpleNamespace(**base, file_manager_settings={"local_start_dir": dir_b})
            widget_a = self._widget_with_session(cfg_a)
            self.assertEqual(Path(widget_a.local_panel.current_dir), Path(dir_a))
            widget_b = self._widget_with_session(cfg_b)
            self.assertEqual(Path(widget_b.local_panel.current_dir), Path(dir_b))
            # Profile A's folder must not leak into profile B's session.
            self.assertEqual(Path(widget_b.local_panel.current_dir), Path(dir_b))


if __name__ == "__main__":
    unittest.main()
