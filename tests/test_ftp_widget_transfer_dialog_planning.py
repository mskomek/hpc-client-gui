from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    Path,
    QApplication,
    RemoteDirPanel,
    SimpleNamespace,
    TransferDialog,
    TransferItem,
    _CountingFiles,
    _PlannedOp,
    patch,
    pytest,
    tempfile,
    threading,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
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
    def test_transfer_item_trailing_cached_size_keeps_positional_construction(self) -> None:
        plain = TransferItem("download", "/remote/a.txt", "a.txt")
        self.assertIsNone(plain.cached_size)
        self.assertFalse(plain.recursive)
        self.assertEqual(plain.priority, "Normal")

        sized = TransferItem("upload", "local.bin", "/remote/local.bin", False, "High", 2048)
        self.assertEqual(sized.cached_size, 2048)
        self.assertEqual(sized.priority, "High")

        keyword = TransferItem("download", "/remote/b.bin", "b.bin", cached_size=777)
        self.assertEqual(keyword.cached_size, 777)
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
    def test_transfer_item_size_falls_back_to_stat_when_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.bin"
            source.write_bytes(b"x" * 333)
            item = TransferItem("upload", str(source), "/remote/data.bin")
            self.assertEqual(self.widget.transfer_activity._item_size(item), 333)
    @pytest.mark.integration
    def test_download_plan_carries_listed_remote_size(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp:
            result = panel._build_remote_download_plan_background(
                SimpleNamespace(cancelled=False),
                files,
                ["/remote"],
                tmp,
            )
        plan = result.get("plan") or []
        transfers = [op for op in plan if op.op == "download"]
        sizes = {op.src: op.size for op in transfers}
        self.assertEqual(sizes.get("/remote/root.txt"), 4)
        self.assertEqual(sizes.get("/remote/child/nested.txt"), 6)
        self.assertNotIn("/remote/child", sizes)
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
    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_transfer_dialog_runs_up_to_parallel_limit(self) -> None:
        started: list[str] = []
        finished: list[str] = []
        release = threading.Event()
        lock = threading.Lock()
        items = [
            TransferItem("download", "/remote/a.bin", "a.bin"),
            TransferItem("download", "/remote/b.bin", "b.bin"),
            TransferItem("download", "/remote/c.bin", "c.bin"),
        ]

        def run_item(item, _progress=None):
            with lock:
                started.append(item.src)
            release.wait(5)
            with lock:
                finished.append(item.src)

        dialog = TransferDialog(
            title="Download",
            items=items,
            run_item=run_item,
            parallel_limit=2,
        )
        try:
            dialog.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                QApplication.processEvents()
                with lock:
                    if len(started) >= 2:
                        break
                time.sleep(0.01)
            with lock:
                self.assertEqual(len(started), 2)
                self.assertEqual(finished, [])

            release.set()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not dialog.finished_cleanly():
                QApplication.processEvents()
                time.sleep(0.01)
            self.assertTrue(dialog.finished_cleanly())
            with lock:
                self.assertCountEqual(started, [item.src for item in items])
                self.assertCountEqual(finished, [item.src for item in items])
        finally:
            dialog.cancel_all()
            dialog.deleteLater()
    @pytest.mark.integration
    @pytest.mark.concurrency
    def test_transfer_dialog_finishes_mkdir_before_parallel_transfer_batch(self) -> None:
        prepared = threading.Event()
        started_uploads: list[str] = []
        lock = threading.Lock()
        items = [
            TransferItem("mkdir_remote", "", "/remote/folder"),
            TransferItem("upload", "first.bin", "/remote/folder/first.bin"),
            TransferItem("upload", "second.bin", "/remote/folder/second.bin"),
        ]

        def run_item(item, _progress=None):
            if item.op == "mkdir_remote":
                time.sleep(0.03)
                prepared.set()
                return
            self.assertTrue(prepared.is_set())
            with lock:
                started_uploads.append(item.src)

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
            self.assertCountEqual(started_uploads, ["first.bin", "second.bin"])
        finally:
            dialog.cancel_all()
            dialog.deleteLater()
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
