from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from truba_gui.ssh.client import SSHClientWrapper, SSHConnInfo


class _Transport:
    def get_banner(self):
        return None

    def is_active(self):
        return False


class _SSHClient:
    def __init__(self):
        self.connect_kwargs = None
        self.applied_policy = None
        self.system_host_keys_loaded = False

    def load_system_host_keys(self):
        self.system_host_keys_loaded = True

    def set_missing_host_key_policy(self, policy):
        self.applied_policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs

    def get_transport(self):
        return _Transport()

    def open_sftp(self):
        return object()


class OptionalSSHCredentialsTests(unittest.TestCase):
    def test_empty_username_and_password_use_ssh_defaults(self):
        fake_client = _SSHClient()
        with patch(
            "truba_gui.ssh.client.paramiko.SSHClient",
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

    def test_key_path_forwards_loaded_key_object_without_secret(self):
        fake_client = _SSHClient()
        sentinel_key = object()
        key_path = "/home/bob/id_rsa"
        with patch(
            "truba_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ), patch(
            "truba_gui.ssh.client.paramiko.RSAKey.from_private_key_file",
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

    def test_strict_host_key_policy_loads_system_keys_and_applies_reject(self):
        fake_client = _SSHClient()
        with patch(
            "truba_gui.ssh.client.paramiko.SSHClient",
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

    def test_accept_new_host_key_policy_applies_auto_add(self):
        fake_client = _SSHClient()
        with patch(
            "truba_gui.ssh.client.paramiko.SSHClient",
            return_value=fake_client,
        ):
            wrapper = SSHClientWrapper(
                SSHConnInfo(
                    host="cluster.example",
                    port=22,
                    host_key_policy="accept-new",
                )
            )
            wrapper.connect()

        self.assertIsInstance(fake_client.applied_policy, paramiko.AutoAddPolicy)


if __name__ == "__main__":
    unittest.main()
