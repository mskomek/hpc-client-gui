"""FM-05 tests: one-hop SSH jump host with fakes; no real network."""

from __future__ import annotations
from support.test_ssh_jump_host_shared import (
    JumpAuthenticationError,
    JumpConnection,
    JumpForwardingDeniedError,
    Path,
    SSHClientWrapper,
    SSHConnInfo,
    SSHJumpInfo,
    _FakeChannel,
    _FakeClient,
    make_connected_wrapper,
    mock,
    normalize_jump_host_settings,
    os,
    paramiko,
    pytest,
    sys,
    tempfile,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

class FailureCleanupTests(unittest.TestCase):
    pytestmark = [pytest.mark.integration, pytest.mark.resource]

    @staticmethod
    def _connect(info, target_client, jump_client, *, shell=True):
        """Run wrapper.connect with ordered fake clients; returns the error."""
        pending = [target_client] + ([jump_client] if jump_client else [])

        def factory(*args, **kwargs):
            return pending.pop(0) if len(pending) > 1 else pending[0]

        error = None
        with mock.patch(
            "hpc_gui.ssh.client.paramiko.SSHClient", side_effect=factory
        ), mock.patch.object(
            SSHClientWrapper, "_start_shell_session", lambda self: None
        ):
            try:
                SSHClientWrapper(info).connect()
            except Exception as exc:  # noqa: BLE001 - tests assert on type
                error = exc
        return error

    def test_jump_auth_failure_never_attempts_target(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        sequence: list[str] = []
        target_client = _FakeClient(sequence=sequence, role="target")
        jump_client = _FakeClient(sequence=sequence, role="jump")
        jump_client.connect_error = paramiko.AuthenticationException()
        info = SSHConnInfo(host="c", port=22, jump=jump_info)
        error = self._connect(info, target_client, jump_client)
        self.assertIsInstance(error, JumpAuthenticationError)
        self.assertEqual(target_client.connect_count, 0)
        self.assertTrue(jump_client.closed)

    def test_forwarding_denied_is_distinct_error_with_cleanup(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        sequence: list[str] = []
        target_client = _FakeClient(sequence=sequence, role="target")
        jump_client = _FakeClient(sequence=sequence, role="jump")
        jump_client.transport.fail_channel = True
        info = SSHConnInfo(host="c", port=22, jump=jump_info)
        error = self._connect(info, target_client, jump_client)
        self.assertIsInstance(error, JumpForwardingDeniedError)
        self.assertEqual(target_client.connect_count, 0)
        self.assertTrue(jump_client.closed)

    def test_target_auth_failure_cleans_jump(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        sequence: list[str] = []
        target_client = _FakeClient(sequence=sequence, role="target")
        target_client.connect_error = paramiko.AuthenticationException()
        jump_client = _FakeClient(sequence=sequence, role="jump")
        info = SSHConnInfo(host="c", port=22, jump=jump_info)
        self._connect(info, target_client, jump_client)
        self.assertTrue(jump_client.closed)

    def test_target_hostkey_change_cleans_jump(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        sequence: list[str] = []
        target_client = _FakeClient(sequence=sequence, role="target")
        target_client.connect_error = paramiko.BadHostKeyException("c", None, None)
        jump_client = _FakeClient(sequence=sequence, role="jump")
        info = SSHConnInfo(host="c", port=22, jump=jump_info)
        self._connect(info, target_client, jump_client)
        self.assertTrue(jump_client.closed)

    def test_sftp_init_failure_full_cleanup(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        sequence: list[str] = []
        target_client = _FakeClient(sequence=sequence, role="target")
        target_client.sftp_error = RuntimeError("sftp init failed")
        jump_client = _FakeClient(sequence=sequence, role="jump")
        info = SSHConnInfo(host="c", port=22, jump=jump_info)
        self._connect(info, target_client, jump_client)
        self.assertTrue(target_client.closed)
        self.assertTrue(jump_client.closed)

    def test_close_twice_is_safe(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        wrapper.close()
        wrapper.close()
        self.assertTrue(jump.closed)
        self.assertIsNone(wrapper._jump_connection)

    def test_worker_cancel_style_close_during_partial_stage(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        # Simulate a cancel while only the jump stage has resources.
        partial = JumpConnection(
            jump_info,
            target_host="c",
            target_port=22,
        )
        fake_client = _FakeClient()
        partial.client = fake_client
        partial.channel = _FakeChannel()
        wrapper._jump_connection = partial
        wrapper.close()
        self.assertTrue(fake_client.closed)
        self.assertIsNone(wrapper._jump_connection)

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
