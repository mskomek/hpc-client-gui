from __future__ import annotations

from support.ftp_widget_test_support import (
    DIRECTORY_CACHE_TTL_SECONDS,
    FtpWidgetTestCase,
    QApplication,
    QEvent,
    QKeyEvent,
    Qt,
    RemoteDirPanel,
    SimpleNamespace,
    _CountingFiles,
    patch,
    pytest,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_directory_cache_reuses_recently_visited_directory(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}

        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.monotonic",
            side_effect=[0.0, 10.0, 20.0],
        ):
            panel.set_dir("/remote")
            panel.set_dir("/remote/child")
            panel.set_dir("/remote")

        self.assertEqual(files.calls, ["/remote", "/remote/child"])
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_directory_cache_force_refresh_bypasses_cache(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}

        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.monotonic",
            side_effect=[0.0, 10.0, 20.0],
        ):
            panel.set_dir("/remote")
            panel.refresh()
            panel.refresh(force=True)

        self.assertEqual(files.calls, ["/remote", "/remote"])
    @pytest.mark.gui
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_tree_f5_forces_refresh(self) -> None:
        panel = self.widget.panel_scratch
        view = panel.views["all"]
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_F5,
            Qt.KeyboardModifier.NoModifier,
        )

        with patch.object(panel, "refresh") as refresh:
            QApplication.sendEvent(view, event)

        refresh.assert_called_once_with(force=True)
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_directory_cache_expires_after_ttl(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}

        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.monotonic",
            side_effect=[0.0, 3601.0],
        ):
            panel.set_dir("/remote")
            panel.refresh()

        self.assertEqual(files.calls, ["/remote", "/remote"])
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_directory_cache_expires_after_its_ttl(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}

        ttl = DIRECTORY_CACHE_TTL_SECONDS
        self.assertEqual(ttl, 60.0)
        with patch(
            "hpc_gui.ui.widgets.remote_dir_panel.monotonic",
            side_effect=[0.0, ttl - 1.0, ttl + 1.0],
        ):
            panel.set_dir("/remote")
            panel.refresh()
            panel.refresh()

        self.assertEqual(files.calls, ["/remote", "/remote"])
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_panel_shutdown_unregisters_idempotently_and_by_identity(self) -> None:
        panel = RemoteDirPanel()
        panel_id = panel.panel_id
        replacement = object()
        try:
            self.assertIs(RemoteDirPanel._instances.get(panel_id), panel)

            panel.shutdown()
            panel.shutdown()
            self.assertNotIn(panel_id, RemoteDirPanel._instances)

            RemoteDirPanel._instances[panel_id] = replacement
            panel.shutdown()
            self.assertIs(RemoteDirPanel._instances.get(panel_id), replacement)
        finally:
            if RemoteDirPanel._instances.get(panel_id) is replacement:
                RemoteDirPanel._instances.pop(panel_id, None)
            panel.deleteLater()
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    @pytest.mark.concurrency
    def test_remote_panel_shutdown_waits_once_for_active_thread_without_planning_jobs(self) -> None:
        panel = RemoteDirPanel()

        class FakeThread:
            def __init__(self) -> None:
                self.quit_calls = 0
                self.wait_calls: list[int] = []

            def quit(self) -> None:
                self.quit_calls += 1

            def wait(self, timeout: int) -> None:
                self.wait_calls.append(timeout)

        active_thread = FakeThread()
        panel._active_thread = active_thread
        panel._planning_jobs.clear()
        try:
            panel.shutdown()

            self.assertEqual(active_thread.quit_calls, 1)
            self.assertEqual(active_thread.wait_calls, [1500])
        finally:
            panel.deleteLater()
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    @pytest.mark.concurrency
    def test_remote_panel_shutdown_waits_once_for_active_and_each_planning_thread(self) -> None:
        panel = RemoteDirPanel()

        class FakeThread:
            def __init__(self) -> None:
                self.quit_calls = 0
                self.wait_calls: list[int] = []

            def quit(self) -> None:
                self.quit_calls += 1

            def wait(self, timeout: int) -> None:
                self.wait_calls.append(timeout)

            def isRunning(self) -> bool:
                return False

        active_thread = FakeThread()
        planning_threads = [FakeThread(), FakeThread(), FakeThread()]
        planning_workers = [SimpleNamespace(cancelled=False) for _thread in planning_threads]
        panel._active_thread = active_thread
        panel._planning_jobs = {
            index: (thread, worker)
            for index, (thread, worker) in enumerate(zip(planning_threads, planning_workers))
        }
        try:
            panel.shutdown()

            self.assertEqual(active_thread.quit_calls, 1)
            self.assertEqual(active_thread.wait_calls, [1500])
            for thread in planning_threads:
                self.assertEqual(thread.quit_calls, 1)
                self.assertEqual(thread.wait_calls, [1500])
            self.assertTrue(all(worker.cancelled for worker in planning_workers))
            # Threads that stopped in time (isRunning() == False) are dropped;
            # a thread still running after the wait() timeout must stay
            # referenced so shutdown() never drops the last reference to a
            # QThread whose OS thread is still alive.
            self.assertEqual(panel._planning_jobs, {})
        finally:
            panel.deleteLater()
    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.qt
    @pytest.mark.concurrency
    def test_remote_panel_shutdown_keeps_still_running_planning_thread_referenced(self) -> None:
        panel = RemoteDirPanel()

        class FakeThread:
            def __init__(self, running_after_wait: bool) -> None:
                self.quit_calls = 0
                self.wait_calls: list[int] = []
                self._running_after_wait = running_after_wait

            def quit(self) -> None:
                self.quit_calls += 1

            def wait(self, timeout: int) -> None:
                self.wait_calls.append(timeout)

            def isRunning(self) -> bool:
                return self._running_after_wait

        stuck_thread = FakeThread(running_after_wait=True)
        finished_thread = FakeThread(running_after_wait=False)
        stuck_worker = SimpleNamespace(cancelled=False)
        finished_worker = SimpleNamespace(cancelled=False)
        panel._planning_jobs = {
            0: (stuck_thread, stuck_worker),
            1: (finished_thread, finished_worker),
        }
        try:
            panel.shutdown()

            self.assertTrue(stuck_worker.cancelled)
            self.assertTrue(finished_worker.cancelled)
            # Still-running thread must stay referenced (not dropped) so
            # PySide6 never destroys it while its OS thread is alive.
            self.assertEqual(panel._planning_jobs, {0: (stuck_thread, stuck_worker)})
        finally:
            panel.deleteLater()
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    @pytest.mark.resource
    def test_remote_panel_deferred_delete_unregisters_instance(self) -> None:
        panel = RemoteDirPanel()
        panel_id = panel.panel_id
        try:
            self.assertIs(RemoteDirPanel._instances.get(panel_id), panel)
            panel.deleteLater()
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QApplication.processEvents()

            self.assertNotIn(panel_id, RemoteDirPanel._instances)
        finally:
            if RemoteDirPanel._instances.get(panel_id) is panel:
                RemoteDirPanel._instances.pop(panel_id, None)
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    @pytest.mark.resource
    def test_remote_panel_deferred_delete_preserves_replacement_identity(self) -> None:
        panel = RemoteDirPanel()
        panel_id = panel.panel_id
        replacement = object()
        try:
            RemoteDirPanel._instances[panel_id] = replacement
            panel.deleteLater()
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QApplication.processEvents()

            self.assertIs(RemoteDirPanel._instances.get(panel_id), replacement)
        finally:
            if RemoteDirPanel._instances.get(panel_id) is replacement:
                RemoteDirPanel._instances.pop(panel_id, None)
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_remote_mutation_removes_panel_that_raises_deleted_qt_error(self) -> None:
        source = RemoteDirPanel()
        stale = RemoteDirPanel()
        stale.current_dir = "/remote"
        stale_id = stale.panel_id
        try:
            with patch.object(
                stale,
                "refresh",
                side_effect=RuntimeError(
                    "Internal C++ object (_RemoteTree) already deleted"
                ),
            ):
                source._finish_remote_directory_mutation(["/remote"])

            self.assertNotIn(stale_id, RemoteDirPanel._instances)
        finally:
            source.shutdown()
            stale.shutdown()
            source.deleteLater()
            stale.deleteLater()
