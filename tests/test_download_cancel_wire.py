"""Cancelling a download, end to end over a real SSH/SFTP wire.

Everything between the transfer queue and paramiko was only covered by
fakes, so the behaviour that actually matters after a cancel - the partial
file surviving, the item staying retryable, the session staying usable, and
the next plan still listing the folder - was never exercised together.

Runs against the local disposable mock server; no real host or credential.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.services.transfer_controller import TransferController, TransferItem  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel  # noqa: E402

BIG_NAME = "big_result.cas.h5"
BIG_SIZE = 48 * 1024 * 1024
CANCEL_AFTER_BYTES = 6 * 1024 * 1024


class _PlanWorker:
    """Stand-in for _TransferPlanWorker: the planner only reads `cancelled`."""

    cancelled = False


class DownloadCancelWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls._temp = tempfile.TemporaryDirectory(prefix="truba_cancel_wire_")
        cls.root = Path(cls._temp.name)
        results = cls.root / "results" / "DP_41"
        results.mkdir(parents=True)
        with (results / BIG_NAME).open("wb") as stream:
            stream.write(os.urandom(1 << 20) * (BIG_SIZE >> 20))
        for index in range(4):
            (results / f"extra{index}.dat").write_bytes(b"x" * 128)

        cls.server = MockSSHServer(cls.root)
        cls.server.__enter__()
        cls.ssh = SSHClientWrapper()
        cls.ssh.connect(
            SSHConnInfo(
                host="127.0.0.1",
                port=cls.server.port,
                username=MOCK_USERNAME,
                password=MOCK_PASSWORD,
                host_key_policy="accept-new",
                known_hosts_path=str(cls.root / "known_hosts"),
            )
        )
        cls.files = SSHFilesBackend(cls.ssh)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.ssh.close()
        cls.server.__exit__()
        cls._temp.cleanup()

    def setUp(self) -> None:
        self.panel = RemoteDirPanel()
        self.panel.set_session({"connected": True, "files": self.files})
        self.addCleanup(self.panel.deleteLater)
        self.target = Path(tempfile.mkdtemp(dir=self.root, prefix="local_"))

        # paramiko's prefetch thread dies on the closed channel by design;
        # keep its traceback out of the test output.
        previous = threading.excepthook
        threading.excepthook = lambda args: None
        self.addCleanup(lambda: setattr(threading, "excepthook", previous))

    def _plan(self) -> list:
        result = self.panel._build_remote_download_plan_background(
            _PlanWorker(), self.files, ["/results/DP_41"], str(self.target)
        )
        return list(result["plan"])

    def _open_channels(self) -> int:
        transport = self.ssh.client.get_transport()
        return len([c for c in transport._channels.values() if not c.closed])

    def _run_until_cancelled(self, plan) -> TransferController:
        seen = {"bytes": 0}
        controller = TransferController(
            [TransferItem(op.op, op.src, op.dst, op.recursive) for op in plan],
            lambda item, progress: self.panel._execute_transfer_item(item, progress_cb=progress),
            parallel_limit=1,
        )
        controller._on_progress = lambda _item, done, _total: seen.update(bytes=done)

        def cancel_when_underway() -> None:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if seen["bytes"] > CANCEL_AFTER_BYTES:
                    controller.cancel_all()
                    return
                time.sleep(0.01)

        watcher = threading.Thread(target=cancel_when_underway, daemon=True)
        watcher.start()
        controller.start()
        self.assertTrue(controller.wait(120), "queue never finished")
        watcher.join(5)
        self.assertGreater(seen["bytes"], CANCEL_AFTER_BYTES, "cancel never triggered")
        return controller

    def test_cancel_keeps_the_partial_and_leaves_the_session_usable(self) -> None:
        plan = self._plan()
        downloads = [op for op in plan if op.op == "download"]
        self.assertEqual(len(downloads), 5)
        # Warm the persistent listing channel first: it is opened once and
        # kept, so counting before it exists would read as a leak afterwards.
        list(self.files.iterdir_entries("/results/DP_41"))
        channels_before = self._open_channels()

        controller = self._run_until_cancelled(plan)

        # The cancelled item is reported, and reported as cancelled.
        self.assertEqual(
            [(Path(item.dst).name, error) for item, error in controller.failed],
            [(BIG_NAME, "cancelled")],
        )

        # The partial download never takes the real filename, and its resume
        # metadata survives for the next attempt.
        folder = self.target / "DP_41"
        names = sorted(p.name for p in folder.iterdir())
        self.assertIn(f"{BIG_NAME}.part", names)
        self.assertIn(f"{BIG_NAME}.part.meta", names)
        self.assertNotIn(BIG_NAME, names)

        # Browsing still works and no channel was leaked by the abort.
        self.assertEqual(len(list(self.files.listdir_entries("/results/DP_41"))), 5)
        self.assertEqual(len(list(self.files.iterdir_entries("/results/DP_41"))), 5)
        self.assertEqual(self._open_channels(), channels_before)

        # And the next plan still contains every file, so a retry can restart.
        again = [op for op in self._plan() if op.op == "download"]
        self.assertEqual(len(again), 5)

    def test_retrying_after_a_cancel_completes_the_file(self) -> None:
        self._run_until_cancelled(self._plan())

        for op in self._plan():
            self.panel._execute_transfer_item(
                TransferItem(op.op, op.src, op.dst, op.recursive)
            )

        finished = self.target / "DP_41" / BIG_NAME
        self.assertTrue(finished.exists())
        self.assertEqual(finished.stat().st_size, BIG_SIZE)
        self.assertFalse((self.target / "DP_41" / f"{BIG_NAME}.part").exists())


if __name__ == "__main__":
    unittest.main()
