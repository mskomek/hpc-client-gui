"""FM-05 tests: one-hop SSH jump host with fakes; no real network."""

from __future__ import annotations
from support.test_ssh_jump_host_shared import (
    Any,
    HostKeyInfo,
    Path,
    SSHClientWrapper,
    SSHConnInfo,
    SSHJumpInfo,
    _FakeChannel,
    _FakeClient,
    _FakeSFTP,
    _KnownHostsPolicy,
    jump_info_from_settings,
    make_connected_wrapper,
    mock,
    normalize_jump_host_settings,
    paramiko,
    pytest,
    sys,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

class JumpDisabledBaselineTests(unittest.TestCase):
    @pytest.mark.integration
    def test_jump_disabled_uses_direct_path(self) -> None:
        wrapper, target, jump, _seq = make_connected_wrapper(None)
        self.assertNotIn("sock", target.connect_kwargs)
        self.assertIsNone(wrapper._jump_connection)

    @pytest.mark.contract
    def test_legacy_profile_without_jump_host_is_direct(self) -> None:
        self.assertIsNone(jump_info_from_settings(None))
        self.assertIsNone(jump_info_from_settings({}))
        settings = normalize_jump_host_settings({"enabled": True, "host": ""})
        self.assertIsNone(jump_info_from_settings(settings))

    @pytest.mark.contract
    def test_socket_like_typing_accepts_fake_channel(self) -> None:
        channel = _FakeChannel()
        info = SSHConnInfo(host="h", port=22, preconnected_socket=channel)
        self.assertIs(info.preconnected_socket, channel)

class JumpSequenceTests(unittest.TestCase):
    pytestmark = pytest.mark.integration

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
    pytestmark = pytest.mark.contract

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
