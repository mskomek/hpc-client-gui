"""Regression tests for the extracted SFTP channel manager.

Pure in-memory fakes; no sockets, no real SSH. The wrapper facade keeps its
behaviour, these tests pin the new owner of the channel lifecycle.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.ssh.sftp_channels import SFTPChannelManager  # noqa: E402


def _transport(active=True, authenticated=True):
    return SimpleNamespace(is_active=lambda: active, is_authenticated=lambda: authenticated)


class _FakeChannel:
    def __init__(self) -> None:
        self.timeout = None

    def settimeout(self, value) -> None:
        self.timeout = value


class _FakeSftp:
    created = 0

    def __init__(self) -> None:
        _FakeSftp.created += 1
        self.serial = _FakeSftp.created
        self.channel = _FakeChannel()
        self.closed = False

    def get_channel(self):
        return self.channel

    def close(self) -> None:
        self.closed = True


class SFTPChannelManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeSftp.created = 0
        self.opened: list[_FakeSftp] = []

    def _manager(self, transport=None) -> tuple[SFTPChannelManager, list]:
        calls: list = []

        def provider():
            calls.append(1)
            return transport

        original_from_transport = None
        import paramiko

        original_from_transport = paramiko.SFTPClient.from_transport

        def fake_from_transport(_transport):
            handle = _FakeSftp()
            self.opened.append(handle)
            return handle

        paramiko.SFTPClient.from_transport = staticmethod(fake_from_transport)
        self.addCleanup(setattr, paramiko.SFTPClient, "from_transport", original_from_transport)
        return SFTPChannelManager(provider), calls

    def test_unauthenticated_transport_is_rejected(self) -> None:
        manager, _ = self._manager(_transport(active=True, authenticated=False))
        with self.assertRaises(RuntimeError):
            manager.open_transfer_sftp()

    def test_inactive_or_missing_transport_is_rejected(self) -> None:
        for bad in (None, _transport(active=False)):
            manager, _ = self._manager(bad)
            with self.assertRaises(RuntimeError):
                manager.open_transfer_sftp()

    def test_transfer_channel_gets_timeout_applied(self) -> None:
        manager, _ = self._manager(_transport())
        sftp = manager.open_transfer_sftp()
        self.assertEqual(sftp.channel.timeout, 60)

    def test_listing_channel_is_reused_when_clean(self) -> None:
        manager, _ = self._manager(_transport())
        with manager.listing_sftp() as first:
            pass
        with manager.listing_sftp() as second:
            pass
        self.assertIs(first, second)
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(first.channel.timeout, 15)

    def test_abandoned_listing_context_drops_channel(self) -> None:
        manager, _ = self._manager(_transport())
        try:
            with manager.listing_sftp() as first:
                raise RuntimeError("abandoned iteration")
        except RuntimeError:
            pass
        self.assertTrue(first.closed)
        with manager.listing_sftp() as second:
            self.assertIsNot(second, first)
        self.assertEqual(len(self.opened), 2)

    def test_clean_listing_retains_channel(self) -> None:
        manager, _ = self._manager(_transport())
        with manager.listing_sftp() as handle:
            pass
        self.assertFalse(handle.closed)
        self.assertIs(manager.listing_channel, handle)

    def test_close_is_idempotent(self) -> None:
        manager, _ = self._manager(_transport())
        with manager.listing_sftp():
            pass
        manager.close()
        manager.close()
        self.assertIsNone(manager.listing_channel)
        self.assertTrue(self.opened[0].closed)

    def test_capability_probe_closes_its_temporary_channel(self) -> None:
        manager, _ = self._manager(_transport())
        self.assertTrue(manager.supports_transfer_sftp_channels())
        self.assertTrue(self.opened[0].closed)

    def test_broken_transport_reports_no_capability(self) -> None:
        manager, _ = self._manager(None)
        self.assertFalse(manager.supports_transfer_sftp_channels())


if __name__ == "__main__":
    unittest.main()
