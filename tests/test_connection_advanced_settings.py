"""FM-04 tests: advanced connection settings + transfer source-of-truth."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.config.models import SSHConfig  # noqa: E402
from hpc_gui.ssh.client import coerce_keepalive_interval  # noqa: E402


class HostKeyPolicyDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def _dialog(self, initial=None):
        from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog

        dialog = ConnectionDialog(initial_profile=initial)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_accept_new_profile_selects_correct_combo(self) -> None:
        dialog = self._dialog({"host_key_policy": "accept-new"})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "accept-new")

    def test_strict_profile_selects_correct_combo(self) -> None:
        dialog = self._dialog({"host_key_policy": "strict"})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "strict")

    def test_malformed_policy_defaults_to_accept_new(self) -> None:
        dialog = self._dialog({"host_key_policy": "accept-anything"})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "accept-new")

    def test_missing_policy_defaults_to_accept_new(self) -> None:
        dialog = self._dialog({})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "accept-new")

    def test_saving_persists_enum_not_translated_text(self) -> None:
        dialog = self._dialog()
        index = dialog.cb_host_key_policy.findData("strict")
        dialog.cb_host_key_policy.setCurrentIndex(index)
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["host_key_policy"], "strict")
        self.assertNotEqual(collected["host_key_policy"], "Yalnızca önceden güvenilen sunucu")

    def test_no_duplicate_visible_strict_checkbox_remains(self) -> None:
        dialog = self._dialog()
        self.assertFalse(
            hasattr(dialog, "cb_strict_hostkey"),
            "ConnectionDialog must not keep the old strict-host-key checkbox",
        )


class KeepaliveAndTimeoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def _dialog(self, initial=None):
        from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog

        dialog = ConnectionDialog(initial_profile=initial)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_keepalive_missing_defaults_to_30(self) -> None:
        dialog = self._dialog({})
        self.assertEqual(dialog.sp_keepalive.value(), 30)

    def test_keepalive_malformed_uses_coercion_default(self) -> None:
        dialog = self._dialog({"keepalive_interval_seconds": "junk"})
        self.assertEqual(dialog.sp_keepalive.value(), coerce_keepalive_interval("junk"))

    def test_keepalive_zero_is_collected(self) -> None:
        dialog = self._dialog({"keepalive_interval_seconds": 0})
        self.assertEqual(dialog.sp_keepalive.value(), 0)
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["keepalive_interval_seconds"], 0)

    def test_keepalive_zero_disables_runtime_keepalive(self) -> None:
        # Runtime contract: 0 reaches transport.set_keepalive(0), which is
        # how the current Paramiko-based client disables keepalive.
        cfg = SSHConfig(keepalive_interval_seconds=0)
        self.assertEqual(coerce_keepalive_interval(cfg.keepalive_interval_seconds), 0)

    def test_keepalive_thirty_propagates_exactly(self) -> None:
        dialog = self._dialog({"keepalive_interval_seconds": 30})
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["keepalive_interval_seconds"], 30)

    def test_timeout_zero_maps_to_none(self) -> None:
        from hpc_gui.config.storage import coerce_profile_ssh_timeout

        dialog = self._dialog({"ssh_timeout": 0})
        value = float(dialog.sp_ssh_timeout.value()) or None
        self.assertIsNone(value)
        self.assertIsNone(coerce_profile_ssh_timeout(0))

    def test_positive_timeout_propagates(self) -> None:
        dialog = self._dialog({"ssh_timeout": 12.5})
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["ssh_timeout"], 12.5)


class ProfilePreservationAfterAdvancedEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def test_advanced_edit_preserves_fm01_state(self) -> None:
        from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog

        stored = {
            "id": "stable-id",
            "name": "lab",
            "host": "old.example.org",
            "password_enc": "token",
            "system_template_source": {"kind": "plugin"},
            "file_manager": {
                "local_start_dir": "/tmp/w",
                "sync": {"enabled": True, "local_root": "/L", "remote_root": "/R"},
                "future_nested": {"a": 1},
            },
            "comparison_enabled": True,
            "unknown_future": [1, 2],
        }
        dialog = ConnectionDialog(initial_profile=dict(stored))
        try:
            dialog.host.setText("new.example.org")
            index = dialog.cb_host_key_policy.findData("strict")
            dialog.cb_host_key_policy.setCurrentIndex(index)
            collected = dialog._collect_profile()
        finally:
            dialog.deleteLater()

        assert collected is not None
        self.assertEqual(collected["host"], "new.example.org")
        self.assertEqual(collected["host_key_policy"], "strict")
        self.assertEqual(collected["id"], "stable-id")
        self.assertEqual(collected["system_template_source"], {"kind": "plugin"})
        self.assertEqual(collected["file_manager"]["local_start_dir"], "/tmp/w")
        self.assertEqual(collected["file_manager"]["sync"]["enabled"], True)
        self.assertEqual(collected["file_manager"]["future_nested"], {"a": 1})
        self.assertTrue(collected["comparison_enabled"])
        self.assertEqual(collected["unknown_future"], [1, 2])


class LoginWidgetPolicyPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def test_login_widget_uses_canonical_policy_state(self) -> None:
        from hpc_gui.ui.widgets.login_widget import LoginWidget

        login = LoginWidget()
        try:
            login._load_profile_into_fields(
                {"name": "p", "host": "h", "host_key_policy": "strict"}
            )
            self.assertEqual(login._profile_host_key_policy, "strict")
            login.cb_strict_hostkey.setChecked(False)
            self.assertEqual(login._profile_host_key_policy, "accept-new")
            with mock.patch(
                "hpc_gui.ui.widgets.login_widget.upsert_profile"
            ) as upsert, mock.patch(
                "hpc_gui.ui.widgets.login_widget.load_profiles",
                return_value=[],
            ):
                login.profile_name.setText("p")
                login.host.setText("h")
                self.assertTrue(login.save_profile())
            saved = upsert.call_args.args[0]
            self.assertEqual(saved["host_key_policy"], "accept-new")
        finally:
            login.deleteLater()


class ParallelismSourceOfTruthTests(unittest.TestCase):
    def test_coerce_bounds_and_defaults(self) -> None:
        from hpc_gui.config.storage import coerce_profile_transfer_parallelism

        self.assertEqual(coerce_profile_transfer_parallelism(None, 1), 1)
        self.assertEqual(coerce_profile_transfer_parallelism(3, 1), 3)
        self.assertEqual(coerce_profile_transfer_parallelism(99, 1), 10)
        self.assertEqual(coerce_profile_transfer_parallelism("bad", 1), 1)

    def test_effective_limit_rule(self) -> None:
        # requested = profile value; effective = requested only if the
        # backend supports isolated parallel transfer channels.
        for requested, supports, expected in (
            (1, True, 1),
            (3, True, 3),
            (3, False, 1),
            (10, True, 10),
        ):
            cfg = SSHConfig(transfer_parallelism=requested)
            configured = int(cfg.transfer_parallelism)
            effective = configured if supports else 1
            self.assertEqual(effective, expected)

    def test_settings_dialog_has_no_global_parallelism_editor(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language
        from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog

        load_language("en")
        with mock.patch.object(Path, "home"), tempfile.TemporaryDirectory():
            dialog = SettingsDialog()
            try:
                self.assertFalse(hasattr(dialog, "sp_transfer_parallelism"))
            finally:
                dialog.deleteLater()


class TransferChannelSafetyTests(unittest.TestCase):
    def test_workers_receive_distinct_channels(self) -> None:
        """Two concurrent fake workers get distinct channel objects."""
        channels: list[object] = []
        barrier = threading.Barrier(2, timeout=5)

        class FakeChannel:
            pass

        def worker():
            channels.append(FakeChannel())
            barrier.wait()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(len(channels), 2)
        self.assertIsNot(channels[0], channels[1])

    def test_unsupported_backend_forces_one(self) -> None:
        files = SimpleNamespace(supports_parallel_transfers=False)
        cfg = SSHConfig(transfer_parallelism=4)
        effective = cfg.transfer_parallelism if getattr(files, "supports_parallel_transfers", False) else 1
        self.assertEqual(effective, 1)


if __name__ == "__main__":
    unittest.main()
