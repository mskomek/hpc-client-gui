"""FM-05 tests: one-hop SSH jump host with fakes; no real network."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import paramiko  # noqa: E402

from hpc_gui.config.jump_host_profile import (  # noqa: E402
    normalize_jump_host_settings,
)
from hpc_gui.ssh.client import (  # noqa: E402
    HostKeyInfo,
    SSHClientWrapper,
    SSHConnInfo,
    _KnownHostsPolicy,
)
from hpc_gui.ssh.jump import (  # noqa: E402
    JumpAuthenticationError,
    JumpConnection,
    JumpForwardingDeniedError,
    SSHJumpInfo,
    jump_info_from_settings,
)


class _FakeTransport:
    def __init__(self, *, fail_channel: bool = False):
        self.keepalive_calls: list[int] = []
        self.open_channel_calls: list[tuple] = []
        self.fail_channel = fail_channel

    def is_active(self) -> bool:
        return True

    def is_authenticated(self) -> bool:
        return True

    def set_keepalive(self, interval: int) -> None:
        self.keepalive_calls.append(interval)

    def get_banner(self):
        return b""

    def open_channel(self, kind, dest_addr=None, src_addr=None):
        self.open_channel_calls.append((kind, dest_addr, src_addr))
        if self.fail_channel:
            raise paramiko.ChannelException(1, "administratively prohibited")
        return _FakeChannel()


class _FakeChannel:
    def send(self, data: bytes) -> int:
        return len(data)

    def recv(self, size: int) -> bytes:
        return b""

    def settimeout(self, timeout) -> None:
        return None

    def close(self) -> None:
        return None


class _FakeHostKeys:
    def add(self, *args, **kwargs) -> None:
        return None


class _FakeClient:
    """Fake paramiko.SSHClient for either role."""

    def __init__(self, sequence: Optional[list] = None, role: str = "") -> None:
        self.transport = _FakeTransport()
        self.connect_kwargs: dict[str, Any] = {}
        self.policies: list[Any] = []
        self.closed = False
        self.connect_count = 0
        self.sequence = sequence
        self.role = role
        self._host_keys = _FakeHostKeys()
        self.connect_error: Optional[BaseException] = None
        self.sftp_error: Optional[BaseException] = None

    # host-key plumbing
    def load_system_host_keys(self) -> None:
        pass

    def load_host_keys(self, path) -> None:
        pass

    def get_host_keys(self):
        return self._host_keys

    def save_host_keys(self, path) -> None:
        pass

    def set_missing_host_key_policy(self, policy) -> None:
        self.policies.append(policy)

    def open_sftp(self):
        if self.sftp_error is not None:
            raise self.sftp_error
        return _FakeSFTP()

    def connect(self, **kwargs) -> None:
        if self.sequence is not None:
            self.sequence.append(f"{self.role}-connect")
        self.connect_count += 1
        self.connect_kwargs.update(kwargs)
        if self.connect_error is not None:
            raise self.connect_error

    def get_transport(self):
        return None if self.closed else self.transport

    def close(self) -> None:
        self.closed = True


class _FakeSFTP:
    def get_channel(self):
        return _FakeChannel()

    def close(self):
        pass


def make_connected_wrapper(jump_info: Optional[SSHJumpInfo] = None, **info_kwargs):
    """Build a wrapper whose paramiko clients are fakes; returns (w, target, jump).

    ``client.py`` and ``jump.py`` share one ``paramiko`` module object, so a
    single ordered factory hands out the target client first and the jump
    client second.
    """
    sequence: list[str] = []
    target_client = _FakeClient(sequence=sequence, role="target")
    jump_client = _FakeClient(sequence=sequence, role="jump") if jump_info else None
    info = SSHConnInfo(
        host="cluster.example.org",
        port=22,
        username="user",
        keepalive_interval_seconds=30,
        jump=jump_info,
        **info_kwargs,
    )
    wrapper = SSHClientWrapper(info)
    pending = [target_client] + ([jump_client] if jump_client else [])

    def factory(*args, **kwargs):
        return pending.pop(0) if len(pending) > 1 else pending[0]

    with mock.patch(
        "hpc_gui.ssh.client.paramiko.SSHClient", side_effect=factory
    ), mock.patch.object(
        SSHClientWrapper, "_start_shell_session", lambda self: None
    ):
        wrapper.connect()
    return wrapper, target_client, jump_client, sequence


class JumpDisabledBaselineTests(unittest.TestCase):
    def test_jump_disabled_uses_direct_path(self) -> None:
        wrapper, target, jump, _seq = make_connected_wrapper(None)
        self.assertNotIn("sock", target.connect_kwargs)
        self.assertIsNone(wrapper._jump_connection)

    def test_legacy_profile_without_jump_host_is_direct(self) -> None:
        self.assertIsNone(jump_info_from_settings(None))
        self.assertIsNone(jump_info_from_settings({}))
        settings = normalize_jump_host_settings({"enabled": True, "host": ""})
        self.assertIsNone(jump_info_from_settings(settings))

    def test_socket_like_typing_accepts_fake_channel(self) -> None:
        channel = _FakeChannel()
        info = SSHConnInfo(host="h", port=22, preconnected_socket=channel)
        self.assertIs(info.preconnected_socket, channel)


class JumpSequenceTests(unittest.TestCase):
    def test_jump_connects_before_target(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw.example.org", username="gate")
        wrapper, target, jump, sequence = make_connected_wrapper(jump_info)
        self.assertIn("jump-connect", sequence)
        self.assertIn("target-connect", sequence)
        self.assertLess(
            sequence.index("jump-connect"), sequence.index("target-connect")
        )
        self.assertEqual(jump.connect_count, 1)

    def test_direct_tcpip_targets_exact_host_port(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw", port=2222)
        info = SSHConnInfo(host="cluster.example.org", port=2222, jump=jump_info)
        wrapper = SSHClientWrapper(info)
        jump_client = _FakeClient(role="jump")
        with mock.patch(
            "hpc_gui.ssh.client.paramiko.SSHClient"
        ), mock.patch(
            "hpc_gui.ssh.jump.paramiko.SSHClient", return_value=jump_client
        ), mock.patch.object(
            SSHClientWrapper, "_start_shell_session", lambda self: None
        ):
            wrapper.connect()
        kind, dest, src = jump_client.transport.open_channel_calls[-1]
        self.assertEqual(kind, "direct-tcpip")
        self.assertEqual(dest, ("cluster.example.org", 2222))

    def test_target_receives_channel_as_sock(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        sock = target.connect_kwargs.get("sock")
        self.assertIsNotNone(sock)
        self.assertIs(sock, wrapper._jump_connection.channel)

    def test_jump_transport_receives_keepalive(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw", keepalive_interval_seconds=30)
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        self.assertEqual(jump.transport.keepalive_calls, [30])

    def test_target_transport_remains_active_transport(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        self.assertIs(wrapper._active_transport(), target.transport)

    def test_parallel_transfers_do_not_multiply_jump_clients(self) -> None:
        jump_info = SSHJumpInfo(enabled=True, host="gw")
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        from hpc_gui.ssh import sftp_channels as sftp_module

        used_transports: list[Any] = []

        def fake_from_transport(transport):
            used_transports.append(transport)
            return _FakeSFTP()

        with mock.patch.object(
            sftp_module.paramiko.SFTPClient,
            "from_transport",
            staticmethod(fake_from_transport),
        ):
            wrapper.open_transfer_sftp()
            wrapper.open_transfer_sftp()
        self.assertEqual(len(used_transports), 2)
        self.assertTrue(all(t is target.transport for t in used_transports))
        self.assertEqual(jump.connect_count, 1)


class PolicyAndPromptRoleTests(unittest.TestCase):
    def test_hostkeyinfo_role_defaults_to_target(self) -> None:
        info = HostKeyInfo("h", "ssh-ed25519", "aa:bb")
        self.assertEqual(info.role, "target")

    def test_policy_emits_jump_role(self) -> None:
        captured: list[HostKeyInfo] = []

        def decide(info: HostKeyInfo) -> str:
            captured.append(info)
            return "once"

        policy = _KnownHostsPolicy(Path("unused"), decide, role="jump")

        class FakeKey:
            def get_name(self):
                return "ssh-ed25519"

            def get_fingerprint(self):
                return b"\x01\x02"

            fingerprint = b"\x01\x02"

        policy.missing_host_key(_FakeClient(), "gw", FakeKey())
        self.assertEqual(captured[0].role, "jump")
        self.assertEqual(captured[0].hostname, "gw")

    def test_policy_default_role_is_target(self) -> None:
        captured: list[HostKeyInfo] = []

        def decide(info: HostKeyInfo) -> str:
            captured.append(info)
            return "once"

        policy = _KnownHostsPolicy(Path("unused"), decide)

        class FakeKey:
            def get_name(self):
                return "ssh-rsa"

            fingerprint = b"\x03"

            def get_fingerprint(self):
                return b"\x03"

        policy.missing_host_key(_FakeClient(), "cluster", FakeKey())
        self.assertEqual(captured[0].role, "target")

    def test_policies_independent(self) -> None:
        jump_info = SSHJumpInfo(
            enabled=True, host="gw", host_key_policy="strict"
        )
        wrapper, target, jump, _seq = make_connected_wrapper(jump_info)
        self.assertTrue(
            any(isinstance(p, paramiko.RejectPolicy) for p in jump.policies)
        )
        self.assertTrue(
            any(isinstance(p, _KnownHostsPolicy) for p in target.policies)
        )


class FailureCleanupTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
