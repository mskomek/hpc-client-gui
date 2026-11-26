from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    Path,
    RemoteDirPanel,
    TransferDialog,
    TransferItem,
    _PlannedOp,
    patch,
    pytest,
    tempfile,
    time,
)


class FtpWidgetTests(FtpWidgetTestCase):


    @pytest.mark.gui
    @pytest.mark.qt
    def test_progress_updates_use_direct_item_id_row_lookup(self) -> None:
        item = TransferItem("download", "/remote/a.bin", "a.bin")
        dialog = TransferDialog(
            title="Download",
            items=[item],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._active_item = item
            dialog._pending = []
            panel = self.widget.transfer_activity
            panel.record("controller", [dialog], "Download")

            self.assertIn(id(item), panel._row_by_item_id)
            self.assertIn(id(item), panel._progress_bar_by_item_id)
            registered_bar = panel._progress_bar_by_item_id[id(item)]
            self.assertIsNotNone(registered_bar)

            dialog.transferProgressChanged.emit(item, 30, 100)

            row = panel._row_by_item_id[id(item)]
            bar = panel._progress_bar_by_item_id[id(item)]
            self.assertEqual(bar.value(), 30)
            self.assertEqual(
                panel.queue_list.itemWidget(row, panel._PROGRESS_COLUMN),
                bar,
            )

            dialog.transferListsChanged.emit([], [], [])
            self.assertIn(id(item), panel._row_by_item_id)
            self.assertEqual(panel._progress_bar_by_item_id[id(item)].value(), 30)
        finally:
            dialog.deleteLater()


    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.performance
    def test_transfer_dialog_bounds_and_coalesces_large_queue_publication(self) -> None:
        items = [
            TransferItem("download", f"/remote/{index}.bin", f"{index}.bin")
            for index in range(5)
        ]
        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=lambda _item, _progress=None: None,
        )
        try:
            published = []
            dialog.transferListsChanged.connect(
                lambda pending, _errors, _completed: published.append(pending)
            )
            with patch.object(dialog, "_MAX_VISIBLE_LIST_ITEMS", 3):
                dialog._refresh()
                self.assertEqual(dialog.queue_list.count(), 4)
                self.assertEqual(dialog.queue_list.item(3).text(), "Remaining: 2")
                self.assertEqual(len(published[-1]), 5)

                dialog._refresh_scheduled = False
                with patch.object(dialog._refresh_timer, "start") as start_timer:
                    dialog._schedule_refresh()
                    dialog._schedule_refresh()
                start_timer.assert_called_once_with()
        finally:
            dialog.deleteLater()


    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_dialog_is_modeless_and_reports_progress(self) -> None:
        transfer_item = TransferItem("download", "/remote/big.bin", "big.bin")
        dialog = TransferDialog(
            title="Download",
            items=[transfer_item, TransferItem("download", "/remote/next.bin", "next.bin")],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            self.assertFalse(dialog.isModal())
            self.assertEqual(dialog.queue_list.count(), 0)
            dialog._refresh()
            self.assertEqual(dialog.queue_list.count(), 2)

            dialog.clear_pending()
            self.assertEqual(dialog.queue_list.count(), 0)

            dialog._started_at = 1.0
            with patch("hpc_gui.ui.dialogs.transfer_dialog.time.monotonic", return_value=3.0):
                dialog._on_transfer_progress(transfer_item, 2048, 4096)
            detail = dialog.lbl_transfer_stats.text()
            self.assertIn("2.0 KB/4.0 KB", detail)
            self.assertIn("/s", detail)

            dialog._on_transfer_progress(transfer_item, 5 * 1024 ** 3, 8 * 1024 ** 3)
            self.assertIn("5.0 GB/8.0 GB", dialog.lbl_transfer_stats.text())
        finally:
            dialog.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    def test_transfer_dialog_never_exceeds_backend_safe_cap(self) -> None:
        dialog = TransferDialog(
            title="Upload",
            items=[],
            run_item=lambda _item, _progress=None: None,
            parallel_limit=5,
            max_parallel_limit=1,
        )
        try:
            self.assertEqual(dialog._parallel_limit, 1)
            self.assertEqual(dialog.set_parallel_limit(5), 1)
            self.assertEqual(dialog._parallel_limit, 1)
            self.assertIn("1", dialog.lbl_parallel_hint.text())
        finally:
            dialog.deleteLater()

    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_transfer_dialog_process_queue_starts_only_when_no_worker_is_active(self) -> None:
        dialog = TransferDialog(
            title="Download",
            items=[TransferItem("download", "/remote/a.txt", "a.txt")],
            run_item=lambda _item, _progress=None: None,
        )
        try:
            dialog._running = True
            with patch.object(dialog, "start") as start:
                self.assertFalse(dialog.process_queue())
            start.assert_not_called()

            dialog._running = False
            dialog._active_items = []
            dialog._active_item = None
            dialog._stopped = True
            dialog._cancelled = True
            with patch.object(dialog, "start") as start:
                self.assertTrue(dialog.process_queue())
            start.assert_called_once()
            self.assertFalse(dialog._stopped)
            self.assertFalse(dialog._cancelled)
        finally:
            dialog.deleteLater()


    @pytest.mark.unit
    def test_transfer_item_size_falls_back_to_stat_when_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.bin"
            source.write_bytes(b"x" * 333)
            item = TransferItem("upload", str(source), "/remote/data.bin")
            self.assertEqual(self.widget.transfer_activity._item_size(item), 333)

    @pytest.mark.unit
    def test_transfer_item_size_prefers_cached_size_without_repeat_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.bin"
            source.write_bytes(b"x" * 512)
            item = TransferItem(
                "upload",
                str(source),
                "/remote/data.bin",
                cached_size=128,
            )
            with patch(
                "pathlib.Path.stat",
                side_effect=AssertionError("cached size must avoid a stat"),
            ):
                self.assertEqual(
                    self.widget.transfer_activity._item_size(item),
                    128,
                )


    @pytest.mark.unit
    def test_transfer_items_from_plan_preserve_known_size_and_leave_unknown_none(self) -> None:
        plan = [
            _PlannedOp("download", "/remote/a.bin", "a.bin", size=4096),
            _PlannedOp("upload", "local.txt", "/remote/local.txt"),
            _PlannedOp("mkdir_local", "", r"D:\target\folder"),
        ]
        items = RemoteDirPanel._transfer_items_from_plan(plan)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].cached_size, 4096)
        self.assertIsNone(items[1].cached_size)
        self.assertIsNone(items[2].cached_size)
