"""Regression tests for the paramiko prefetch shutdown race.

Cancelling a download closes the SFTP channel while paramiko's prefetch
thread is still queueing reads, which raised ``OSError: Socket is closed``
in that thread. It was logged as an uncaught crash and raised the crash
flag, so the next launch reported a crash that never happened.
"""

from __future__ import annotations

import unittest

from hpc_gui.core.logging_setup import _is_paramiko_prefetch_shutdown


class PrefetchShutdownFilterTests(unittest.TestCase):
    def test_matches_the_prefetch_socket_close(self) -> None:
        self.assertTrue(
            _is_paramiko_prefetch_shutdown(
                "Thread-6 (_prefetch_thread)", OSError, OSError("Socket is closed")
            )
        )

    def test_matches_a_closed_channel(self) -> None:
        self.assertTrue(
            _is_paramiko_prefetch_shutdown(
                "Thread-79 (_prefetch_thread)", OSError, OSError("Channel closed.")
            )
        )

    def test_leaves_other_failures_in_the_same_thread_alone(self) -> None:
        self.assertFalse(
            _is_paramiko_prefetch_shutdown(
                "Thread-6 (_prefetch_thread)",
                MemoryError,
                MemoryError("out of memory"),
            )
        )
        self.assertFalse(
            _is_paramiko_prefetch_shutdown(
                "Thread-6 (_prefetch_thread)",
                OSError,
                OSError("No space left on device"),
            )
        )

    def test_leaves_other_threads_alone(self) -> None:
        self.assertFalse(
            _is_paramiko_prefetch_shutdown(
                "TransferWorker", OSError, OSError("Socket is closed")
            )
        )
        self.assertFalse(
            _is_paramiko_prefetch_shutdown("", OSError, OSError("Socket is closed"))
        )


if __name__ == "__main__":
    unittest.main()
