"""Directory streaming over a real paramiko SSH/SFTP wire.

The other listing tests use fakes, so nothing there proves that
``listdir_iter`` and the shared listing channel behave against an actual
SFTP subsystem. This runs the real client code against the local disposable
mock server (``tests/support/mock_ssh_server.py``) - no real host, account,
or credential is involved.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402


class SSHDirectoryListingWireTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="truba_listing_wire_")
        self.root = Path(self._temp.name)
        self.addCleanup(self._temp.cleanup)
        self.work = self.root / "work"
        self.work.mkdir()
        for index in range(250):
            (self.work / f"file{index:04d}.txt").write_text("x" * index, encoding="utf-8")
        for index in range(5):
            (self.work / f"dir{index}").mkdir()

        self.server = MockSSHServer(self.root)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)

        self.ssh = SSHClientWrapper()
        self.ssh.connect(
            SSHConnInfo(
                host="127.0.0.1",
                port=self.server.port,
                username=MOCK_USERNAME,
                password=MOCK_PASSWORD,
                host_key_policy="accept-new",
                known_hosts_path=str(self.root / "known_hosts"),
            )
        )
        self.addCleanup(self.ssh.close)
        self.backend = SSHFilesBackend(self.ssh)

    def test_streams_every_entry_with_correct_metadata(self) -> None:
        entries = list(self.backend.iterdir_entries("/work"))

        self.assertEqual(len(entries), 255)
        by_name = {entry.name: entry for entry in entries}
        self.assertTrue(by_name["dir3"].is_dir)
        self.assertEqual(by_name["dir3"].path, "/work/dir3")
        self.assertFalse(by_name["file0100.txt"].is_dir)
        self.assertEqual(by_name["file0100.txt"].size, 100)
        self.assertGreater(by_name["file0100.txt"].mtime, 0)

    def test_repeated_navigation_reuses_one_listing_channel(self) -> None:
        for _ in range(4):
            self.assertEqual(len(list(self.backend.iterdir_entries("/work"))), 255)
        first = self.ssh._listing_sftp
        self.assertIsNotNone(first)
        list(self.backend.iterdir_entries("/work"))
        self.assertIs(self.ssh._listing_sftp, first)

    def test_abandoned_listing_recovers_on_the_next_navigation(self) -> None:
        stream = self.backend.iterdir_entries("/work")
        next(stream)
        abandoned = self.ssh._listing_sftp
        stream.close()

        # The poisoned channel is dropped, and browsing still works.
        self.assertIsNot(self.ssh._listing_sftp, abandoned)
        self.assertEqual(len(list(self.backend.iterdir_entries("/work"))), 255)

    def test_missing_directory_reports_the_path(self) -> None:
        with self.assertRaises(FileNotFoundError) as caught:
            list(self.backend.iterdir_entries("/work/nope"))
        self.assertEqual(caught.exception.filename, "/work/nope")
        # A failed listing must not wedge browsing either.
        self.assertEqual(len(list(self.backend.iterdir_entries("/work"))), 255)


if __name__ == "__main__":
    unittest.main()
