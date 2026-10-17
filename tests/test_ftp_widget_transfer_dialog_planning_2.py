from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    Path,
    TransferDialog,
    TransferItem,
    _Files,
    _PlannedOp,
    patch,
    pytest,
    tempfile,
    threading,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
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
    def test_transfer_dialog_coalesces_burst_progress_and_delivers_final(self) -> None:
        item = TransferItem("upload", "burst.bin", "/remote/burst.bin")
        dialog = TransferDialog(title="Upload", items=[item], run_item=lambda _item, _progress=None: None)
        try:
            published: list[tuple[int, int]] = []
            dialog.transferProgressChanged.connect(
                lambda _item, done, total: published.append((int(done), int(total)))
            )
            with patch(
                "hpc_gui.ui.dialogs.transfer_dialog.time.monotonic",
                side_effect=[10.0, 10.001, 10.002, 10.100, 10.251, 10.252],
            ):
                dialog._on_transfer_progress(item, 100, 1000)
                dialog._on_transfer_progress(item, 200, 1000)
                dialog._on_transfer_progress(item, 300, 1000)
                dialog._on_transfer_progress(item, 400, 1000)
                self.assertEqual(published, [(100, 1000)])
                dialog._on_transfer_progress(item, 500, 1000)
                dialog._on_transfer_progress(item, 1000, 1000)
            self.assertEqual(published, [(100, 1000), (500, 1000), (1000, 1000)])
            self.assertEqual(dialog._last_progress_by_item[id(item)], (1000, 10.252))
        finally:
            dialog.deleteLater()
    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.performance
    def test_download_planning_uses_worker_and_returns_before_slow_probe(self) -> None:
        class SlowFiles:
            supports_parallel_transfers = False

            def __init__(self) -> None:
                self.started = threading.Event()
                self.release = threading.Event()
                self.thread_id = None

            def is_dir(self, _path: str) -> bool:
                self.thread_id = threading.get_ident()
                self.started.set()
                self.release.wait(3)
                return False

        files = SlowFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            panel,
            "_run_plan_with_progress",
            return_value=True,
        ) as run_plan:
            started_at = time.monotonic()
            self.assertTrue(
                panel._apply_remote_download_incremental(
                    ["/remote/output.bin"],
                    tmp,
                )
            )
            elapsed = time.monotonic() - started_at

            self.assertLess(elapsed, 0.2)
            self.assertTrue(files.started.wait(1))
            self.assertNotEqual(files.thread_id, threading.get_ident())
            run_plan.assert_not_called()

            files.release.set()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not run_plan.called:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertTrue(run_plan.called)
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_active_download_plan_is_not_queued_twice(self) -> None:
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": _Files()}
        source = "/remote/existing.txt"
        target = str(Path(tempfile.gettempdir(), "existing.txt"))
        panel._active_transfer_keys.add(("download", source, target))
        events = []
        panel.set_transfer_activity_callback(
            lambda event, items, title: events.append((event, items, title))
        )

        self.assertTrue(
            panel._run_plan_with_progress(
                [_PlannedOp("download", source, target)],
                "İndiriliyor...",
            )
        )

        self.assertEqual(events, [])
