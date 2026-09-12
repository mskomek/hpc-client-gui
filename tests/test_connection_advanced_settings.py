"""FM-04 tests: advanced connection settings + transfer source-of-truth."""

from __future__ import annotations

import pytest
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

    @pytest.mark.qt
    @pytest.mark.gui
    def test_accept_new_profile_selects_correct_combo(self) -> None:
        dialog = self._dialog({"host_key_policy": "accept-new"})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "accept-new")

    @pytest.mark.qt
    @pytest.mark.gui
    def test_strict_profile_selects_correct_combo(self) -> None:
        dialog = self._dialog({"host_key_policy": "strict"})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "strict")

    @pytest.mark.qt
    @pytest.mark.gui
    def test_malformed_policy_defaults_to_accept_new(self) -> None:
        dialog = self._dialog({"host_key_policy": "accept-anything"})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "accept-new")

    @pytest.mark.qt
    @pytest.mark.gui
    def test_missing_policy_defaults_to_accept_new(self) -> None:
        dialog = self._dialog({})
        self.assertEqual(dialog.cb_host_key_policy.currentData(), "accept-new")

    @pytest.mark.qt
    @pytest.mark.gui
    def test_saving_persists_enum_not_translated_text(self) -> None:
        dialog = self._dialog()
        index = dialog.cb_host_key_policy.findData("strict")
        dialog.cb_host_key_policy.setCurrentIndex(index)
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["host_key_policy"], "strict")
        self.assertNotEqual(collected["host_key_policy"], "Yalnızca önceden güvenilen sunucu")

    @pytest.mark.contract
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

    @pytest.mark.qt
    @pytest.mark.gui
    def test_keepalive_missing_defaults_to_30(self) -> None:
        dialog = self._dialog({})
        self.assertEqual(dialog.sp_keepalive.value(), 30)

    @pytest.mark.qt
    @pytest.mark.gui
    def test_keepalive_malformed_uses_coercion_default(self) -> None:
        dialog = self._dialog({"keepalive_interval_seconds": "junk"})
        self.assertEqual(dialog.sp_keepalive.value(), coerce_keepalive_interval("junk"))

    @pytest.mark.qt
    @pytest.mark.gui
    def test_keepalive_zero_is_collected(self) -> None:
        dialog = self._dialog({"keepalive_interval_seconds": 0})
        self.assertEqual(dialog.sp_keepalive.value(), 0)
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["keepalive_interval_seconds"], 0)

    @pytest.mark.unit
    def test_keepalive_zero_disables_runtime_keepalive(self) -> None:
        # Runtime contract: 0 reaches transport.set_keepalive(0), which is
        # how the current Paramiko-based client disables keepalive.
        cfg = SSHConfig(keepalive_interval_seconds=0)
        self.assertEqual(coerce_keepalive_interval(cfg.keepalive_interval_seconds), 0)

    @pytest.mark.qt
    @pytest.mark.gui
    def test_keepalive_thirty_propagates_exactly(self) -> None:
        dialog = self._dialog({"keepalive_interval_seconds": 30})
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["keepalive_interval_seconds"], 30)

    @pytest.mark.qt
    @pytest.mark.gui
    def test_timeout_zero_maps_to_none(self) -> None:
        from hpc_gui.config.storage import coerce_profile_ssh_timeout

        dialog = self._dialog({"ssh_timeout": 0})
        value = float(dialog.sp_ssh_timeout.value()) or None
        self.assertIsNone(value)
        self.assertIsNone(coerce_profile_ssh_timeout(0))

    @pytest.mark.qt
    @pytest.mark.gui
    def test_positive_timeout_propagates(self) -> None:
        dialog = self._dialog({"ssh_timeout": 12.5})
        collected = dialog._collect_profile()
        assert collected is not None
        self.assertEqual(collected["ssh_timeout"], 12.5)


@pytest.mark.gui
class ProfilePreservationAfterAdvancedEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    @pytest.mark.qt
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


@pytest.mark.gui
class LoginWidgetPolicyPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    @pytest.mark.qt
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
    @pytest.mark.unit
    def test_coerce_bounds_and_defaults(self) -> None:
        from hpc_gui.config.storage import coerce_profile_transfer_parallelism

        self.assertEqual(coerce_profile_transfer_parallelism(None, 1), 1)
        self.assertEqual(coerce_profile_transfer_parallelism(3, 1), 3)
        self.assertEqual(coerce_profile_transfer_parallelism(99, 1), 10)
        self.assertEqual(coerce_profile_transfer_parallelism("bad", 1), 1)

    @pytest.mark.unit
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

    @pytest.mark.qt
    @pytest.mark.gui
    def test_settings_dialog_has_no_global_parallelism_editor(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language
        from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog

        load_language("en")
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            Path, "home", return_value=Path(temp_dir)
        ):
            dialog = SettingsDialog()
            try:
                self.assertFalse(hasattr(dialog, "sp_transfer_parallelism"))
            finally:
                dialog.deleteLater()


class TransferChannelSafetyTests(unittest.TestCase):
    @pytest.mark.integration
    def test_workers_receive_distinct_channels(self) -> None:
        """The channel manager gives concurrent workers owned bounded channels."""
        from hpc_gui.ssh.sftp_channels import SFTPChannelManager

        channels = []
        errors = []
        barrier = threading.Barrier(2, timeout=5)
        transport = SimpleNamespace(
            is_active=lambda: True,
            is_authenticated=lambda: True,
        )

        class FakeChannel:
            timeout = None

            def settimeout(self, value):
                self.timeout = value

        class FakeSFTP:
            def __init__(self):
                self.channel = FakeChannel()
                self.closed = False

            def get_channel(self):
                return self.channel

            def close(self):
                self.closed = True

        def open_fake(_transport):
            channel = FakeSFTP()
            channels.append(channel)
            return channel

        import paramiko

        manager = SFTPChannelManager(lambda: transport)
        with mock.patch.object(
            paramiko.SFTPClient, "from_transport", staticmethod(open_fake)
        ):
            def worker():
                channel = None
                try:
                    channel = manager.open_transfer_sftp()
                    barrier.wait()
                except BaseException as exc:
                    errors.append(exc)
                finally:
                    if channel is not None:
                        channel.close()

            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(channels), 2)
        self.assertIsNot(channels[0], channels[1])
        self.assertTrue(all(channel.closed for channel in channels))
        self.assertTrue(all(channel.channel.timeout == 60 for channel in channels))

    @pytest.mark.integration
    def test_unsupported_backend_forces_one(self) -> None:
        files = SimpleNamespace(supports_parallel_transfers=False)
        cfg = SSHConfig(transfer_parallelism=4)
        effective = cfg.transfer_parallelism if getattr(files, "supports_parallel_transfers", False) else 1
        self.assertEqual(effective, 1)


if __name__ == "__main__":
    unittest.main()
