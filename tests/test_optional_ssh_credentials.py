from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hpc_gui.ssh.client import (
    HostKeyChangedError,
    HostKeyRejectedError,
    SSHClientWrapper,
    SSHConnInfo,
    _KeyboardInteractiveSource,
    load_private_key_with_certificate,
)


class _HostKeys:
    def __init__(self):
        self.entries = []

    def add(self, hostname, key_type, key):
        self.entries.append((hostname, key_type, key))


class _Transport:
    def __init__(self):
        self.keepalive_calls: list[int] = []

    def get_banner(self):
        return None

    def is_active(self):
        return False

    def set_keepalive(self, seconds: int):
        self.keepalive_calls.append(seconds)


class _SSHClient:
    def __init__(self):
        self.connect_kwargs = None
        self.applied_policy = None
        self.system_host_keys_loaded = False
        self.loaded_host_keys = []
        self.saved_host_keys = []
        self.host_keys = _HostKeys()
        self.transport = _Transport()

    def load_system_host_keys(self):
        self.system_host_keys_loaded = True

    def load_host_keys(self, path):
        self.loaded_host_keys.append(path)

    def get_host_keys(self):
        return self.host_keys

    def save_host_keys(self, path):
        self.saved_host_keys.append(path)

    def set_missing_host_key_policy(self, policy):
        self.applied_policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs

    def get_transport(self):
        return self.transport

    def open_sftp(self):
        return object()


class OptionalSSHCredentialsTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        app_data = patch(
            "hpc_gui.ssh.client.app_data_dir",
            return_value=Path(self._temp.name),
        )
        app_data.start()
        self.addCleanup(app_data.stop)

    def test_empty_username_and_password_use_ssh_defaults(self):
        fake_client = _SSHClient()
        with patch(
            "hpc_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ):
            wrapper = SSHClientWrapper(
                SSHConnInfo(
                    host="cluster.example",
                    port=22,
                    username="",
                    password="",
                )
            )
            wrapper.connect()

        self.assertIsNone(fake_client.connect_kwargs["username"])
        self.assertIsNone(fake_client.connect_kwargs["password"])
        self.assertTrue(fake_client.connect_kwargs["allow_agent"])
        self.assertTrue(fake_client.connect_kwargs["look_for_keys"])
        self.assertEqual(fake_client.connect_kwargs["timeout"], 45)
        self.assertEqual(fake_client.connect_kwargs["banner_timeout"], 45)

    def test_keyboard_interactive_returns_ephemeral_challenge_responses(self):
        seen = {}

        def handler(title, instructions, prompts):
            seen.update(title=title, instructions=instructions, prompts=prompts)
            return ["otp-response"]

        class Transport:
            def auth_interactive(self, username, callback):
                self.username = username
                self.result = callback("MFA", "Choose a factor", [("Code: ", False)])
                return self.result

        transport = Transport()
        result = _KeyboardInteractiveSource("user", handler).authenticate(transport)

        self.assertEqual(result, ["otp-response"])
        self.assertEqual(seen["prompts"], [("Code: ", False)])
        self.assertEqual(transport.username, "user")
        self.assertNotIn("otp-response", repr(_KeyboardInteractiveSource("user", handler)))

    def test_private_key_loads_conventional_openssh_certificate(self):
        key_path = Path(self._temp.name) / "id_ed25519"
        cert_path = Path(f"{key_path}-cert.pub")
        key_path.write_text("private-key-placeholder")
        cert_path.write_text("ssh-ed25519-cert-v01@openssh.com placeholder")
        class Key:
            def load_certificate(self, path):
                self.certificate_path = path

        key = Key()
        with patch("hpc_gui.ssh.client.paramiko.PKey.from_path", return_value=key):
            loaded = load_private_key_with_certificate(str(key_path))
        self.assertIs(loaded, key)
        self.assertEqual(loaded.certificate_path, str(cert_path))

    def test_preconnected_socket_is_forwarded_to_paramiko(self):
        fake_client = _SSHClient()
        connected_socket = object()
        with patch(
            "hpc_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ):
            wrapper = SSHClientWrapper(
                SSHConnInfo(
                    host="cluster.example",
                    port=22,
                    preconnected_socket=connected_socket,
                )
            )
            wrapper.connect()

        self.assertIs(fake_client.connect_kwargs["sock"], connected_socket)
    def test_key_path_forwards_loaded_key_object_without_secret(self):
        fake_client = _SSHClient()
        sentinel_key = object()
        key_path = "/home/bob/id_rsa"
        with patch(
            "hpc_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ), patch(
            "hpc_gui.ssh.client.paramiko.PKey.from_path",
            return_value=sentinel_key,
        ) as loader:
            wrapper = SSHClientWrapper(
                SSHConnInfo(
                    host="cluster.example",
                    port=22,
                    username="user",
                    key_path=key_path,
                )
            )
            wrapper.connect()

        loader.assert_called_once_with(key_path)
        self.assertIs(fake_client.connect_kwargs["pkey"], sentinel_key)
        self.assertNotIn("password", fake_client.connect_kwargs)

    def test_key_path_loads_non_rsa_key_from_disk(self):
        from tempfile import TemporaryDirectory

        fake_client = _SSHClient()
        with TemporaryDirectory() as td:
            key_path = str(Path(td) / "id_ecdsa")
            paramiko.ECDSAKey.generate().write_private_key_file(key_path)
            with patch(
                "hpc_gui.ssh.client.paramiko.SSHClient",
                return_value=fake_client,
            ):
                wrapper = SSHClientWrapper(
                    SSHConnInfo(
                        host="cluster.example",
                        port=22,
                        username="user",
                        key_path=key_path,
                    )
                )
                wrapper.connect()

        self.assertIsInstance(fake_client.connect_kwargs["pkey"], paramiko.ECDSAKey)
        self.assertNotIn("password", fake_client.connect_kwargs)

    def test_keepalive_is_bounded_and_applied_to_transport(self):
        for value, expected in ((30, 30), (120, 120), (0, 0), (-10, 0), (999999, 3600), ("oops", 30)):
            with self.subTest(value=value):
                fake_client = _SSHClient()
                with patch(
                    "hpc_gui.ssh.client.paramiko.SSHClient",
                    return_value=fake_client,
                ):
                    SSHClientWrapper(
                        SSHConnInfo(
                            host="cluster.example",
                            port=22,
                            keepalive_interval_seconds=value,
                        )
                    ).connect()
                self.assertEqual(fake_client.transport.keepalive_calls, [expected])

    def test_strict_host_key_policy_loads_system_keys_and_applies_reject(self):
        fake_client = _SSHClient()
        with patch(
            "hpc_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ):
            wrapper = SSHClientWrapper(
                SSHConnInfo(
                    host="cluster.example",
                    port=22,
                    host_key_policy="strict",
                )
            )
            wrapper.connect()

        self.assertTrue(fake_client.system_host_keys_loaded)
        self.assertIsInstance(fake_client.applied_policy, paramiko.RejectPolicy)

    def test_unknown_host_key_can_save_once_or_cancel(self):
        fake_client = _SSHClient()
        key = paramiko.ECDSAKey.generate()
        with tempfile.TemporaryDirectory() as td:
            known_hosts = str(Path(td) / "known_hosts")
            for decision in ("once", "save", "cancel"):
                with self.subTest(decision=decision), patch(
                    "hpc_gui.ssh.client.paramiko.SSHClient",
                    return_value=fake_client,
                ):
                    SSHClientWrapper(
                        SSHConnInfo(
                            host="cluster.example",
                            port=22,
                            known_hosts_path=known_hosts,
                            host_key_decision=lambda _info, value=decision: value,
                        )
                    ).connect()
                    if decision == "cancel":
                        with self.assertRaises(HostKeyRejectedError):
                            fake_client.applied_policy.missing_host_key(
                                fake_client, "cluster.example", key
                            )
                    else:
                        fake_client.applied_policy.missing_host_key(
                            fake_client, "cluster.example", key
                        )

        self.assertEqual(fake_client.saved_host_keys, [known_hosts])
        self.assertEqual(len(fake_client.host_keys.entries), 1)

    def test_changed_host_key_is_rejected(self):
        fake_client = _SSHClient()
        expected = paramiko.ECDSAKey.generate()
        received = paramiko.ECDSAKey.generate()

        def reject_changed(**kwargs):
            raise paramiko.BadHostKeyException(
                kwargs["hostname"], received, expected
            )

        fake_client.connect = reject_changed
        with patch(
            "hpc_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ), self.assertRaises(HostKeyChangedError):
            SSHClientWrapper(
                SSHConnInfo(host="cluster.example", port=22)
            ).connect()


if __name__ == "__main__":
    unittest.main()
