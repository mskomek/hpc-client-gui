from __future__ import annotations

from support.ftp_widget_test_support import (
    DirectoriesWidget,
    FtpWidgetTestCase,
    MIME_REMOTE_PATHS,
    Path,
    QMimeData,
    QUrl,
    _DragPayload,
    _FakeDropEvent,
    _encode_payload,
    patch,
    pytest,
    tempfile,
    time,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_local_file_drop_on_remote_panel_uploads_to_current_remote_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "drop-me.txt")
            source.write_text("drop", encoding="utf-8")
            panel = self.widget.panel_scratch
            panel.current_dir = "/remote/target"
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(source))])
            event = _FakeDropEvent(mime)

            with patch.object(panel, "_apply_local_upload_incremental", return_value=True) as upload:
                panel.views["all"].dropEvent(event)

                upload.assert_not_called()
                self.app.processEvents()

            upload.assert_called_once()
            uploaded_paths, target_dir = upload.call_args.args
            self.assertEqual([Path(path) for path in uploaded_paths], [source])
            self.assertEqual(target_dir, "/remote/target")
            self.assertTrue(event.accepted)
            self.assertFalse(event.ignored)
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_directories_widget_accepts_local_file_drop_for_remote_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "drop-dir.txt")
            source.write_text("drop", encoding="utf-8")
            widget = DirectoriesWidget()
            try:
                widget.panel_scratch.current_dir = "/scratch/drop-target"
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(str(source))])
                event = _FakeDropEvent(mime)

                with patch.object(
                    widget.panel_scratch,
                    "_apply_local_upload",
                    return_value=True,
                ) as upload:
                    widget.dropEvent(event)

                    upload.assert_not_called()
                    self.app.processEvents()

                upload.assert_called_once()
                uploaded_paths, target_dir = upload.call_args.args
                self.assertEqual([Path(path) for path in uploaded_paths], [source])
                self.assertEqual(target_dir, "/scratch/drop-target")
                self.assertTrue(event.accepted)
                self.assertFalse(event.ignored)
            finally:
                widget.shutdown()
                widget.deleteLater()
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_panel_accepts_local_file_drop_on_panel_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "panel-drop.txt")
            source.write_text("drop", encoding="utf-8")
            panel = self.widget.panel_scratch
            panel.current_dir = "/remote/body-target"
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(source))])
            event = _FakeDropEvent(mime)

            with patch.object(panel, "_apply_local_upload_incremental", return_value=True) as upload:
                panel.dropEvent(event)

                upload.assert_not_called()
                self.app.processEvents()

            upload.assert_called_once()
            uploaded_paths, target_dir = upload.call_args.args
            self.assertEqual([Path(path) for path in uploaded_paths], [source])
            self.assertEqual(target_dir, "/remote/body-target")
            self.assertTrue(event.accepted)
            self.assertFalse(event.ignored)
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.concurrency
    def test_remote_panel_drop_upload_planning_yields_before_transfer_start(self) -> None:
        class Files:
            supports_parallel_transfers = True

            def exists(self, _path: str) -> bool:
                return False

        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": Files()}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, "folder")
            folder.mkdir()
            for index in range(30):
                (folder / f"file-{index}.txt").write_text("x", encoding="utf-8")

            with patch.object(panel, "_run_plan_with_progress", return_value=True) as run_plan:
                self.assertTrue(
                    panel._apply_local_upload_incremental([str(folder)], "/remote")
                )
                run_plan.assert_not_called()

                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and not run_plan.called:
                    self.app.processEvents()
                    time.sleep(0.01)

            self.assertTrue(run_plan.called)
            plan = run_plan.call_args.args[0]
            self.assertEqual(
                len([item for item in plan if item.op == "upload"]),
                30,
            )
    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic
    def test_remote_file_drop_on_local_panel_downloads_after_drop_event(self) -> None:
        panel = self.widget.panel_scratch
        panel.current_dir = "/remote"
        remote_path = "/remote/result.txt"
        mime = QMimeData()
        mime.setData(
            MIME_REMOTE_PATHS,
            _encode_payload(_DragPayload(paths=[remote_path], src_panel_id=panel.panel_id)),
        )
        event = _FakeDropEvent(mime)

        with patch.object(
            panel,
            "_apply_remote_download_incremental",
            return_value=True,
        ) as download:
            self.widget.local_panel.tree.dropEvent(event)

            download.assert_not_called()
            self.app.processEvents()

        download.assert_called_once_with([remote_path], self.widget.local_panel.current_dir)
        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)
