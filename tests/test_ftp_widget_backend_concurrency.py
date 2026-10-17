from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    Path,
    QApplication,
    SSHFilesBackend,
    SimpleNamespace,
    TransferDialog,
    TransferItem,
    _PlannedOp,
    pytest,
    tempfile,
    threading,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
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
                        [
                            _PlannedOp(item.op, item.src, item.dst)
                            for item in items
                        ],
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
