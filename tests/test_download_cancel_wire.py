"""Cancelling a download, end to end over a real SSH/SFTP wire.

Everything between the transfer queue and paramiko was only covered by
fakes, so the behaviour that actually matters after a cancel - the partial
file surviving, the item staying retryable, the session staying usable, and
the next plan still listing the folder - was never exercised together.

Runs against the local disposable mock server; no real host or credential.
"""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import pytest

from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.services import private_profile_data as private_data  # noqa: E402
from hpc_gui.services import transfer_resume_store as resume_data  # noqa: E402
from hpc_gui.services.transfer_resume_store import (  # noqa: E402
    transfer_record_key,
    transfer_resume_store_for_backend,
)
from hpc_gui.services.transfer_controller import TransferController
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402
from hpc_gui.services.download_plan import build_download_plan
from hpc_gui.wx_shell_file_transfer import _start_file_transfers

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


class DownloadCancelWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
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

        self.target = Path(tempfile.mkdtemp(dir=self.root, prefix="local_"))

        # paramiko's prefetch thread dies on the closed channel by design;
        # keep its traceback out of the test output.
        previous = threading.excepthook
        threading.excepthook = lambda args: None
        self.addCleanup(lambda: setattr(threading, "excepthook", previous))

    def _plan(self):
        return build_download_plan(self.files, ["/results/DP_41"], str(self.target))

    def _open_channels(self) -> int:
        transport = self.ssh.client.get_transport()
        return len([c for c in transport._channels.values() if not c.closed])

    def _run(self, plan, action="resume", cancel=False):
        state = {"session": {"files": self.files}, "ftp_transfer_type": "binary"}
        seen = {"bytes": 0}
        controller = None

        def progress(_item, done, _total):
            seen["bytes"] = done
            if cancel and done > CANCEL_AFTER_BYTES:
                controller.engine.cancel_all()

        controller = _start_file_transfers(
            state, None, plan, on_progress=progress,
            conflict_resolver=lambda _item: action,
        )
        self.assertTrue(controller.engine.wait(120), "queue never finished")
        return controller, seen

    def _run_until_cancelled(self, plan) -> TransferController:
        controller, seen = self._run(plan, cancel=True)
        self.assertGreater(seen["bytes"], CANCEL_AFTER_BYTES, "cancel never triggered")
        self.assertEqual(
            [(Path(item.dst).name, error) for item, error in controller.engine.failed],
            [(BIG_NAME, "cancelled")],
        )
        return controller

    @pytest.mark.resource
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
            [(Path(item.dst).name, error) for item, error in controller.engine.failed],
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
        again = self._plan()
        self.assertEqual(len([op for op in again if op.op == "download"]), 5)

    def _run_plan_to_completion(self, plan) -> None:
        controller, _ = self._run(plan)
        self.assertFalse(controller.engine.failed, controller.engine.failed)

    def _assert_big_file_complete(self) -> None:
        finished = self.target / "DP_41" / BIG_NAME
        self.assertTrue(finished.exists())
        self.assertEqual(finished.stat().st_size, BIG_SIZE)
        self.assertFalse((self.target / "DP_41" / f"{BIG_NAME}.part").exists())

    def test_resuming_after_a_cancel_completes_the_file(self) -> None:
        plan = self._plan()
        self._run_until_cancelled(plan)

        retry = self._plan()
        self.assertNotIn("delete_local", [op.op for op in retry])
        self._run_plan_to_completion(retry)
        self._assert_big_file_complete()

    def test_overwriting_a_partial_discards_it_before_downloading(self) -> None:
        plan = self._plan()
        self._run_until_cancelled(plan)
        part = self.target / "DP_41" / f"{BIG_NAME}.part"
        self.assertTrue(part.exists())

        retry = self._plan()
        # Overwrite replaces the partial with a fresh staged transfer.
        controller, _ = self._run(retry, action="overwrite")
        self.assertFalse(controller.engine.failed, controller.engine.failed)
        self._assert_big_file_complete()

    def test_skipping_a_partial_leaves_it_alone(self) -> None:
        plan = self._plan()
        self._run_until_cancelled(plan)

        retry = self._plan()
        controller, _ = self._run(retry, action="skip")
        self.assertFalse(controller.engine.failed, controller.engine.failed)
        self.assertTrue((self.target / "DP_41" / f"{BIG_NAME}.part").exists())


if __name__ == "__main__":
    unittest.main()
