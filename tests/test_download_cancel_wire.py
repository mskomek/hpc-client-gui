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
import unittest
from pathlib import Path
from unittest import mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.services import private_profile_data as private_data  # noqa: E402
from hpc_gui.services import transfer_resume_store as resume_data  # noqa: E402
from hpc_gui.services.transfer_resume_store import (  # noqa: E402
    transfer_record_key,
    transfer_resume_store_for_backend,
)
from hpc_gui.services.transfer_controller import TransferController, TransferItem  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel  # noqa: E402

BIG_NAME = "big_result.cas.h5"
BIG_SIZE = 48 * 1024 * 1024
CANCEL_AFTER_BYTES = 6 * 1024 * 1024


class _FakeSecretStore:
    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def protect_secret(plaintext: str) -> str:
        return plaintext.encode("utf-8").hex()

    @staticmethod
    def unprotect_secret(token: str) -> str:
        return bytes.fromhex(token).decode("utf-8")


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.semantic,
    pytest.mark.concurrency,
    pytest.mark.slow,
]


class _PlanWorker:
    """Stand-in for _TransferPlanWorker's GUI bridge, with a canned answer."""

    cancelled = False

    def __init__(self, action: str = "resume") -> None:
        self.action = action
        self.conflicts: list[tuple[str, bool]] = []

    def request_conflict_decision(
        self, _source, target, *, partial: bool = False, direction: str = "download"
    ) -> str:
        assert direction == "download"
        self.conflicts.append((target.path, partial))
        return self.action

    def request_rename(self, _dst_dir: str, _current_name: str):
        raise AssertionError("rename was not expected")


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
        self.profile_id = "download-cancel-wire"
        self.files.profile_id = self.profile_id
        app_data = mock.patch.object(
            private_data, "app_data_dir", return_value=self.root / "app_data"
        )
        secret_store = mock.patch.object(private_data, "secret_store", _FakeSecretStore)
        app_data.start()
        secret_store.start()
        resume_data._STORES.clear()
        self.addCleanup(resume_data._STORES.clear)
        self.addCleanup(secret_store.stop)
        self.addCleanup(app_data.stop)

        self.panel = RemoteDirPanel()
        self.panel.set_session({"connected": True, "files": self.files})
        self.addCleanup(self.panel.deleteLater)
        self.target = Path(tempfile.mkdtemp(dir=self.root, prefix="local_"))

        # paramiko's prefetch thread dies on the closed channel by design;
        # keep its traceback out of the test output.
        previous = threading.excepthook
        threading.excepthook = lambda args: None
        self.addCleanup(lambda: setattr(threading, "excepthook", previous))

    def _plan(self, action: str = "resume") -> tuple[list, _PlanWorker]:
        worker = _PlanWorker(action)
        result = self.panel._build_remote_download_plan_background(
            worker, self.files, ["/results/DP_41"], str(self.target)
        )
        return list(result["plan"]), worker

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

        def cancel_when_underway(_item, done: int, _total: int) -> None:
            seen["bytes"] = done
            if done > CANCEL_AFTER_BYTES:
                controller.cancel_all()

        controller._on_progress = cancel_when_underway
        controller.start()
        self.assertTrue(controller.wait(120), "queue never finished")
        self.assertGreater(seen["bytes"], CANCEL_AFTER_BYTES, "cancel never triggered")
        self.assertEqual(
            [(Path(item.dst).name, error) for item, error in controller.failed],
            [(BIG_NAME, "cancelled")],
        )
        return controller

    @pytest.mark.resource
    def test_cancel_keeps_the_partial_and_leaves_the_session_usable(self) -> None:
        plan, planner = self._plan()
        downloads = [op for op in plan if op.op == "download"]
        self.assertEqual(len(downloads), 5)
        self.assertEqual(planner.conflicts, [], "nothing exists yet, nothing to ask")
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

        # The partial remains separate from the final file. Resume identity
        # is encrypted in profile data instead of a readable sidecar.
        folder = self.target / "DP_41"
        names = sorted(p.name for p in folder.iterdir())
        self.assertIn(f"{BIG_NAME}.part", names)
        self.assertNotIn(f"{BIG_NAME}.part.meta", names)
        self.assertNotIn(BIG_NAME, names)
        partial = folder / f"{BIG_NAME}.part"
        registry = transfer_resume_store_for_backend(self.files)
        self.assertIsNotNone(registry)
        record = registry.get(transfer_record_key("download", str(folder / BIG_NAME)))
        self.assertIsNotNone(record)
        self.assertEqual(record["partial_bytes"], partial.stat().st_size)
        raw_resume_state = private_data._path(
            self.profile_id, "transfer-resume"
        ).read_bytes()
        self.assertTrue(raw_resume_state.startswith(private_data._MAGIC))
        self.assertNotIn(BIG_NAME.encode("utf-8"), raw_resume_state)
        self.assertNotIn(str(partial).encode("utf-8"), raw_resume_state)

        # Browsing still works and no channel was leaked by the abort.
        self.assertEqual(len(list(self.files.listdir_entries("/results/DP_41"))), 5)
        self.assertEqual(len(list(self.files.iterdir_entries("/results/DP_41"))), 5)
        self.assertEqual(self._open_channels(), channels_before)

        # And the next plan still contains every file, so a retry can restart -
        # after asking what to do with the leftover chunk.
        again, planner = self._plan()
        self.assertEqual(len([op for op in again if op.op == "download"]), 5)
        self.assertEqual(
            planner.conflicts, [(str(folder / f"{BIG_NAME}.part"), True)]
        )

    def _run_plan_to_completion(self, plan) -> None:
        for op in plan:
            self.panel._execute_transfer_item(
                TransferItem(op.op, op.src, op.dst, op.recursive)
            )

    def _assert_big_file_complete(self) -> None:
        finished = self.target / "DP_41" / BIG_NAME
        self.assertTrue(finished.exists())
        self.assertEqual(finished.stat().st_size, BIG_SIZE)
        self.assertFalse((self.target / "DP_41" / f"{BIG_NAME}.part").exists())

    def test_resuming_after_a_cancel_completes_the_file(self) -> None:
        plan, _ = self._plan()
        self._run_until_cancelled(plan)

        retry, planner = self._plan("resume")
        self.assertEqual([partial for _path, partial in planner.conflicts], [True])
        self.assertNotIn("delete_local", [op.op for op in retry])
        self._run_plan_to_completion(retry)
        self._assert_big_file_complete()

    def test_overwriting_a_partial_discards_it_before_downloading(self) -> None:
        plan, _ = self._plan()
        self._run_until_cancelled(plan)
        part = self.target / "DP_41" / f"{BIG_NAME}.part"
        self.assertTrue(part.exists())

        retry, planner = self._plan("overwrite")
        self.assertEqual([partial for _path, partial in planner.conflicts], [True])
        # The leftover chunk is dropped first, so the transfer starts over
        # instead of quietly resuming from it.
        deletes = [op.dst for op in retry if op.op == "delete_local"]
        self.assertEqual(deletes, [str(part)])
        self._run_plan_to_completion(retry)
        self._assert_big_file_complete()

    def test_skipping_a_partial_leaves_it_alone(self) -> None:
        plan, _ = self._plan()
        self._run_until_cancelled(plan)

        retry, planner = self._plan("skip")
        self.assertEqual([partial for _path, partial in planner.conflicts], [True])
        self.assertNotIn(
            str(self.target / "DP_41" / BIG_NAME),
            [op.dst for op in retry if op.op == "download"],
        )
        self.assertTrue((self.target / "DP_41" / f"{BIG_NAME}.part").exists())


if __name__ == "__main__":
    unittest.main()
