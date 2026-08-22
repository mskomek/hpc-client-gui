"""Isolated SFTP channel lifecycle for one authenticated SSH connection.

Owns the two channel kinds the file surfaces need: per-transfer isolated
channels and the long-lived persistent listing channel. The owner of the
authenticated connection supplies an active-transport provider callback; this
module intentionally knows nothing about UI or Qt.
"""

from __future__ import annotations

import contextlib
import threading
from typing import Callable, Optional

import paramiko

# Generous relative to the interactive-shell timeout: a transfer channel
# only needs to detect a truly dead connection, not bound normal chunk
# pacing on a slow HPC link.
_SFTP_TRANSFER_TIMEOUT_SECONDS = 60
# Directory browsing is interactive: waiting a full transfer timeout on a dead
# link before the panel reports anything is far too long for a click.
_SFTP_LISTING_TIMEOUT_SECONDS = 15


class SFTPChannelManager:
    """Open, reuse, and discard SFTP channels with bounded timeouts."""

    def __init__(
        self,
        transport_provider: Callable[[], Optional[paramiko.Transport]],
        log: Optional[Callable[[str], None]] = None,
        opener: Optional[Callable[[], paramiko.SFTPClient]] = None,
    ) -> None:
        self._transport_provider = transport_provider
        self._log = log or (lambda msg: None)
        # Late-bound so facade-level overrides of ``open_transfer_sftp``
        # (tests/monkeypatches) stay effective for internal reuse.
        self._opener = opener or self.open_transfer_sftp
        self._listing_sftp = None
        self._listing_lock = threading.RLock()

    @property
    def listing_channel(self):
        """Current persistent listing SFTP client, if one is open."""
        return self._listing_sftp

    def open_transfer_sftp(self):
        """Open an isolated SFTP channel for one upload or download.

        The browsing channel is deliberately shared by the UI. Paramiko SFTP
        clients are not safe to use from several transfer worker threads, so
        file transfers must obtain their own channel from the already
        authenticated transport instead.
        """
        transport = self._transport_provider()
        if transport is None:
            raise RuntimeError("SSH client not connected")
        if not transport.is_active():
            raise RuntimeError("SSH transport is not active")
        is_authenticated = getattr(transport, "is_authenticated", None)
        if callable(is_authenticated) and not is_authenticated():
            raise RuntimeError("SSH transport is not authenticated")
        sftp = paramiko.SFTPClient.from_transport(transport)
        # Without a channel timeout, a silently dead connection (dropped VPN,
        # NAT/firewall idle-kill, etc.) leaves stat()/read()/write() blocked
        # forever with no way for the worker thread, its QThread, or the app
        # to ever unstick — the transfer row freezes at 100% and, if the app
        # is closed while blocked, can crash on shutdown. Bound every SFTP
        # channel so a dead connection surfaces as a normal socket.timeout
        # (caught and reported as a failed transfer) instead of hanging.
        channel = sftp.get_channel()
        if channel is not None:
            channel.settimeout(_SFTP_TRANSFER_TIMEOUT_SECONDS)
        return sftp

    def drop_listing_sftp(self) -> None:
        sftp, self._listing_sftp = self._listing_sftp, None
        if sftp is not None:
            try:
                sftp.close()
            except Exception:
                pass

    @contextlib.contextmanager
    def listing_sftp(self):
        """Lend the long-lived SFTP channel used for directory browsing.

        Opening a channel per navigation costs a full round trip on a high-RTT
        link, so one channel is opened lazily and reused. Access is
        serialized: an abandoned ``listdir_iter`` leaves unread read-ahead
        replies queued, so any non-clean exit discards the channel and the
        next caller opens a fresh one.
        """
        with self._listing_lock:
            if self._listing_sftp is None:
                self._listing_sftp = self._opener()
                get_channel = getattr(self._listing_sftp, "get_channel", None)
                channel = get_channel() if callable(get_channel) else None
                if channel is not None:
                    channel.settimeout(_SFTP_LISTING_TIMEOUT_SECONDS)
            clean = False
            try:
                yield self._listing_sftp
                clean = True
            finally:
                if not clean:
                    self.drop_listing_sftp()

    def supports_transfer_sftp_channels(self) -> bool:
        """Probe whether the active connection can create isolated channels."""
        channel = None
        try:
            channel = self._opener()
            return True
        except Exception:
            return False
        finally:
            if channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass

    def close(self) -> None:
        """Drop persistent channel state; safe to call more than once."""
        self.drop_listing_sftp()
