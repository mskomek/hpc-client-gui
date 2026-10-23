"""Focused FTP widget tests for transfer engine behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from PySide6.QtWidgets import QApplication
from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog, TransferItem
from hpc_gui.ui.widgets.remote_dir_panel import _PlannedOp
from hpc_gui.services.files_ssh import SSHFilesBackend
from ftp_widget_test_support import FtpWidgetTestCase


class FtpWidgetTransferEngineTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_overwrite_delete_is_followed_by_its_transfer_before_later_items(self) -> None:
        deletion_done = threading.Event()
        first_transfer_done = threading.Event()
        started: list[str] = []
        items = [
            TransferItem("delete", "", "/remote/a.bin"),
            TransferItem("upload", "a.bin", "/remote/a.bin"),
            TransferItem("upload", "b.bin", "/remote/b.bin"),
        ]

        def run_item(item, _progress=None):
            if item.op == "delete":
                deletion_done.set()
                return
            if item.src == "a.bin":
                self.assertTrue(deletion_done.is_set())
                time.sleep(0.05)
                first_transfer_done.set()
            else:
                self.assertTrue(first_transfer_done.is_set())
            started.append(item.src)

        dialog = TransferDialog(
            title="Upload",
            items=items,
            run_item=run_item,
            parallel_limit=2,
        )
        try:
            dialog.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not dialog.finished_cleanly():
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertTrue(dialog.finished_cleanly())
            self.assertEqual(started, ["a.bin", "b.bin"])
        finally:
            dialog.cancel_all()
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_recursive_plan_prepares_all_mkdirs_before_parallel_upload_phase(self) -> None:
        prepared: list[str] = []
        started: list[str] = []
        release = threading.Event()
        lock = threading.Lock()
        items = [
            TransferItem("mkdir_remote", "", "/remote/root"),
            TransferItem("mkdir_remote", "", "/remote/root/one"),
            TransferItem("upload", "one.bin", "/remote/root/one/one.bin"),
            TransferItem("mkdir_remote", "", "/remote/root/two"),
            TransferItem("upload", "two.bin", "/remote/root/two/two.bin"),
            TransferItem("upload", "root.bin", "/remote/root/root.bin"),
        ]

        def run_item(item, _progress=None):
            if item.op == "mkdir_remote":
                prepared.append(item.dst)
                return
            self.assertEqual(len(prepared), 3)
            with lock:
                started.append(item.src)
            release.wait(3)

        dialog = TransferDialog(
            title="Upload",
            items=items,
            run_item=run_item,
            parallel_limit=3,
        )
        try:
            dialog.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                with lock:
                    if len(started) >= 2:
                        break
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertEqual(prepared, ["/remote/root", "/remote/root/one", "/remote/root/two"])
            with lock:
                self.assertGreaterEqual(len(started), 2)
            release.set()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not dialog.finished_cleanly():
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertTrue(dialog.finished_cleanly())
        finally:
            release.set()
            dialog.cancel_all()
            dialog.deleteLater()

    @pytest.mark.unit
    def test_mixed_mutation_plan_keeps_original_order(self) -> None:
        items = [
            TransferItem("mkdir_remote", "", "/remote/root"),
            TransferItem("upload", "one.bin", "/remote/root/one.bin"),
            TransferItem("delete", "", "/remote/old.bin"),
            TransferItem("upload", "two.bin", "/remote/root/two.bin"),
        ]
        worker = __import__(
            "hpc_gui.ui.dialogs.transfer_dialog",
            fromlist=["_WorkerThread"],
        )._WorkerThread(items, lambda _item, _progress=None: None, parallel_limit=3)
        self.assertEqual(worker._items, items)

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_resumed_transfer_speed_uses_only_session_bytes(self) -> None:
        transfer_item = TransferItem("upload", "big.bin", "/remote/big.bin")
        dialog = TransferDialog(
            title="Upload",
            items=[transfer_item],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._on_item_started(0, transfer_item)
            with patch(
                "hpc_gui.ui.dialogs.transfer_dialog.time.monotonic",
                side_effect=[100.0, 102.0],
            ):
                dialog._on_transfer_progress(transfer_item, 8_000_000, 10_000_000)
                self.assertIn("0 B/s", dialog.lbl_transfer_stats.text())
                dialog._on_transfer_progress(transfer_item, 9_000_000, 10_000_000)

            detail = dialog.lbl_transfer_stats.text()
            self.assertIn("488.3 KB/s", detail)
            self.assertIn("remaining 0:02", detail)
            self.assertEqual(
                dialog._item_progress_baselines[id(transfer_item)],
                (8_000_000.0, 100.0),
            )

            dialog._on_item_finished(transfer_item, False, "")
            self.assertNotIn(id(transfer_item), dialog._item_progress_baselines)
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_parallel_capable_backend_uses_configured_parallelism_for_new_plan(self) -> None:
        class ParallelFiles:
            supports_parallel_transfers = True

            def __init__(self) -> None:
                self.active = 0
                self.max_active = 0
                self.lock = threading.Lock()

            def download(self, _remote_path: str, local_path: str, progress_cb=None) -> None:
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                time.sleep(0.03)
                Path(local_path).write_bytes(b"content")
                if progress_cb is not None:
                    progress_cb(7, 7)
                with self.lock:
                    self.active -= 1

        panel = self.widget.panel_scratch
        files = ParallelFiles()
        panel.session = {
            "connected": True,
            "files": files,
            "cfg": SimpleNamespace(transfer_parallelism=3),
        }
        controllers: list[TransferDialog] = []
        completed = threading.Event()

        def activity(event, items, _title):
            if event == "controller":
                controllers.extend(items)
            elif event == "completed":
                completed.set()

        panel.set_transfer_activity_callback(activity)
        with tempfile.TemporaryDirectory() as tmp:
            plan = [
                _PlannedOp(
                    "download",
                    f"/remote/{index}.txt",
                    str(Path(tmp) / f"local-{index}.txt"),
                )
                for index in range(4)
            ]

            self.assertTrue(panel._run_plan_with_progress(plan, "Download"))

            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not completed.is_set():
                QApplication.processEvents()
                time.sleep(0.01)

        self.assertEqual(len(controllers), 1)
        self.assertEqual(controllers[0]._parallel_limit, 3)
        self.assertEqual(controllers[0]._max_parallel_limit, 3)
        self.assertTrue(completed.is_set())
        self.assertGreaterEqual(files.max_active, 2)

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.resource
    def test_ssh_backend_parallel_uploads_use_isolated_closed_channels(self) -> None:
        class FakeWriter:
            def __init__(self, channel) -> None:
                self.channel = channel

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def write(self, _data: bytes) -> None:
                with self.channel.owner.lock:
                    self.channel.did_write = True
                    self.channel.owner.active += 1
                    self.channel.owner.max_active = max(
                        self.channel.owner.max_active,
                        self.channel.owner.active,
                    )
                    self.channel.owner.started.set()
                self.channel.owner.release.wait(3)
                with self.channel.owner.lock:
                    self.channel.owner.active -= 1

        class FakeTransferChannel:
            def __init__(self, owner) -> None:
                self.owner = owner
                self.closed = False
                self.did_write = False

            def stat(self, _path: str):
                return SimpleNamespace(st_size=0)

            def open(self, _path: str, mode: str):
                self.owner.assert_modes.append(mode)
                return FakeWriter(self)

            def close(self) -> None:
                self.closed = True

        class FakeSSH:
            sftp = SimpleNamespace(rename=lambda _old, _new: None)

            def __init__(self) -> None:
                self.channels: list[FakeTransferChannel] = []
                self.lock = threading.Lock()
                self.started = threading.Event()
                self.release = threading.Event()
                self.active = 0
                self.max_active = 0
                self.assert_modes: list[str] = []

            def open_transfer_sftp(self):
                channel = FakeTransferChannel(self)
                self.channels.append(channel)
                return channel

            def supports_transfer_sftp_channels(self) -> bool:
                probe = self.open_transfer_sftp()
                probe.close()
                return True

        ssh = FakeSSH()
        backend = SSHFilesBackend(ssh)
        self.assertTrue(backend.supports_parallel_transfers)
        items: list[TransferItem] = []
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(3):
                source = Path(tmp) / f"source-{index}.bin"
                source.write_bytes(b"payload")
                items.append(TransferItem("upload", str(source), f"/remote/{index}.bin"))
            panel = self.widget.panel_scratch
            panel.session = {
                "connected": True,
                "files": backend,
                "cfg": SimpleNamespace(transfer_parallelism=3),
            }
            try:
                self.assertTrue(
                    panel._run_plan_with_progress(
                        [_PlannedOp(item.op, item.src, item.dst) for item in items],
                        "Upload",
                    )
                )
                dialog = panel._transfer_dialogs[-1]
                self.assertEqual(dialog._parallel_limit, 3)
                self.assertEqual(dialog._max_parallel_limit, 3)
                self.assertTrue(ssh.started.wait(2))
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    with ssh.lock:
                        if ssh.max_active >= 2:
                            break
                    time.sleep(0.01)
                with ssh.lock:
                    self.assertGreaterEqual(ssh.max_active, 2)
                ssh.release.set()
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline and not dialog.finished_cleanly():
                    QApplication.processEvents()
                    time.sleep(0.01)
                self.assertTrue(dialog.finished_cleanly())
            finally:
                ssh.release.set()
                dialog.cancel_all()
                dialog.deleteLater()

        transfer_channels = [channel for channel in ssh.channels if channel.did_write]
        self.assertEqual(len(transfer_channels), 3)
        self.assertEqual(len({id(channel) for channel in transfer_channels}), 3)
        self.assertTrue(all(channel.closed for channel in transfer_channels))
        self.assertEqual(ssh.assert_modes, ["wb", "wb", "wb"])

    @pytest.mark.integration
    def test_ssh_backend_without_transfer_channel_capability_clamps_parallelism(self) -> None:
        class UnavailableSSH:
            sftp = object()

            def supports_transfer_sftp_channels(self) -> bool:
                return False

            def open_transfer_sftp(self):
                raise AssertionError("unavailable capability must not open a transfer channel")

        backend = SSHFilesBackend(UnavailableSSH())
        self.assertFalse(backend.supports_parallel_transfers)
        dialog = TransferDialog(
            title="Upload",
            items=[],
            run_item=lambda _item, _progress=None: None,
            parallel_limit=3,
            max_parallel_limit=(3 if backend.supports_parallel_transfers else 1),
        )
        try:
            self.assertEqual(dialog._parallel_limit, 1)
            self.assertEqual(dialog._max_parallel_limit, 1)
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_ssh_resumed_upload_reports_existing_offset_before_copy(self) -> None:
        class RemoteWriter:
            def __init__(self) -> None:
                self.data = bytearray(b"abc")

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def write(self, data: bytes) -> None:
                self.data.extend(data)

        class TransferChannel:
            def __init__(self) -> None:
                self.writer = RemoteWriter()
                self.closed = False

            def stat(self, _path: str):
                return SimpleNamespace(st_size=3)

            def open(self, _path: str, mode: str):
                self.assert_mode = mode
                return self.writer

            def close(self) -> None:
                self.closed = True

        channel = TransferChannel()
        ssh = SimpleNamespace(sftp=object(), open_transfer_sftp=lambda: channel)
        backend = SSHFilesBackend(ssh)
        progress: list[tuple[int, int]] = []
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "resume.bin"
            source.write_bytes(b"abcdefgh")
            backend.resume_upload(
                str(source),
                "/remote/resume.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(progress, [(3, 8), (8, 8)])
        self.assertEqual(channel.assert_mode, "ab")
        self.assertEqual(bytes(channel.writer.data), b"abcdefgh")
        self.assertTrue(channel.closed)
