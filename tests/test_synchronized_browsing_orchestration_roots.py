"""FM-02 tests: synchronized browsing mapping service and widget behavior."""

from __future__ import annotations
from support.test_synchronized_browsing_shared import (
    Path,
    QApplication,
    SimpleNamespace,
    _CountingRemotePanel,
    mock,
    normalize_file_manager_settings,
    os,
    patch,
    pytest,
    sys,
    tempfile,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

class SynchronizationOrchestrationTests(unittest.TestCase):
    pytestmark = [pytest.mark.qt, pytest.mark.semantic]

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from hpc_gui.core.i18n import load_language

        load_language("en")
        state_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
            return_value={
                "local_dir": os.getcwd(),
                "active_remote": "scratch",
                "splitter_sizes": [500, 500],
            },
        )
        type_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_transfer_type",
            return_value="auto",
        )
        update_patch = patch(
            "hpc_gui.ui.widgets.ftp_widget.update_ftp_state",
            return_value={},
        )
        state_patch.start()
        type_patch.start()
        update_patch.start()
        self.addCleanup(state_patch.stop)
        self.addCleanup(type_patch.stop)
        self.addCleanup(update_patch.stop)
        # Isolate profile storage so sync persistence never touches the
        # real user configuration.
        self._home_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._home_tmp.cleanup)
        home_patch = mock.patch.object(Path, "home")
        home_patch.start().return_value = Path(self._home_tmp.name)
        self.addCleanup(home_patch.stop)
        from hpc_gui.config import storage as storage_mod

        storage_mod.upsert_profile({"name": "lab", "host": "h"})

    def _make_widget(self, cfg=None):
        from hpc_gui.ui.widgets.ftp_widget import FtpWidget

        widget = FtpWidget()
        self.addCleanup(widget.shutdown)
        self.addCleanup(widget.deleteLater)
        session = {
            "connected": True,
            "files": SimpleNamespace(supports_progressive_listing=False, listdir_entries=lambda _d: []),
            "cfg": cfg,
            "profile_name": "lab",
        }
        widget.set_session(session)
        return widget

    def _saved_cfg(self, local_root: str, remote_root: str, enabled: bool):
        return SimpleNamespace(
            username="user",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
            file_manager_settings=normalize_file_manager_settings(
                {
                    "sync": {
                        "enabled": enabled,
                        "local_root": local_root,
                        "remote_root": remote_root,
                    }
                }
            ),
        )

    @pytest.mark.gui
    def test_existing_valid_roots_enable_without_navigation_or_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=panel):
                widget.btn_sync_browsing.setChecked(True)
            self.assertTrue(widget.btn_sync_browsing.isChecked())
            self.assertEqual(panel.set_dir_calls, [])

    @pytest.mark.gui
    def test_invalid_saved_local_root_does_not_enable(self) -> None:
        panel = _CountingRemotePanel()
        widget = self._make_widget(
            self._saved_cfg(str(Path("Z:/missing-root")), "/remote/root", True)
        )
        with patch.object(widget, "active_remote_panel", return_value=panel):
            pass
        self.assertFalse(widget.btn_sync_browsing.isChecked())
        self.assertNotEqual(widget._sync_status_reason, "")
        self.assertEqual(panel.set_dir_calls, [])

    @pytest.mark.gui
    def test_local_navigation_causes_exactly_one_remote_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "sub"))
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=panel):
                widget.btn_sync_browsing.setChecked(True)
                target = os.path.join(root, "sub")
                widget.local_panel.directoryChanged.emit(target)
                widget.local_panel.directoryChanged.emit(target)
            self.assertEqual(panel.set_dir_calls, ["/remote/root/sub"])
            self.assertFalse(widget._sync_navigation_guard)

    @pytest.mark.gui
    def test_guard_prevents_ping_pong(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "sub"))
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=panel):
                widget.btn_sync_browsing.setChecked(True)
                # A guarded programmatic remote navigation must not bounce
                # back to the local panel.
                navigations_before = len(widget.local_panel._history)
                widget._sync_navigation_guard = True
                widget._on_synchronized_remote_dir_changed(
                    "/remote/root/sub", widget.panel_scratch
                )
                widget._sync_navigation_guard = False
            self.assertEqual(panel.set_dir_calls, [])
            self.assertEqual(len(widget.local_panel._history), navigations_before)

    @pytest.mark.unit
    def test_inactive_remote_panel_signal_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            active_panel = _CountingRemotePanel()
            inactive_panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=active_panel):
                widget.btn_sync_browsing.setChecked(True)
                widget._on_synchronized_remote_dir_changed("/remote/root/x", inactive_panel)
            self.assertEqual(inactive_panel.set_dir_calls, [])
            self.assertEqual(active_panel.set_dir_calls, [])

    @pytest.mark.gui
    def test_missing_local_counterpart_does_not_navigate_or_create(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            missing_target = os.path.join(root, "does-not-exist")
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=panel):
                widget.btn_sync_browsing.setChecked(True)
                before = set(os.listdir(root))
                widget._on_synchronized_remote_dir_changed(
                    "/remote/root/newdir", widget.panel_scratch
                )
            self.assertEqual(set(os.listdir(root)), before)
            self.assertFalse(Path(missing_target).exists())
            self.assertEqual(panel.set_dir_calls, [])

    @pytest.mark.gui
    def test_no_remote_preflight_on_gui_thread(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            files = SimpleNamespace(supports_progressive_listing=False)
            for forbidden in ("stat", "exists", "listdir"):
                setattr(files, forbidden, None)
            widget.session["files"] = files
            panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=panel):
                widget.btn_sync_browsing.setChecked(True)
                widget.local_panel.directoryChanged.emit(root)

    @pytest.mark.gui
    def test_disconnect_clears_transient_state_but_not_roots(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", True))
            self.assertTrue(widget.btn_sync_browsing.isChecked())
            widget._sync_navigation_guard = True
            widget.set_session(None)
            self.assertFalse(widget.btn_sync_browsing.isEnabled())
            self.assertFalse(widget.btn_sync_browsing.isChecked())
            self.assertFalse(widget._sync_navigation_guard)
            # Saved pair is re-derived on reconnect.
            widget.set_session(
                {
                    "connected": True,
                    "files": SimpleNamespace(supports_progressive_listing=False, listdir_entries=lambda _d: []),
                    "cfg": self._saved_cfg(root, "/remote/root", True),
                    "profile_name": "lab",
                }
            )
            self.assertTrue(widget.btn_sync_browsing.isChecked())
            self.assertEqual(widget._sync_roots.local_root, root)

    @pytest.mark.gui
    def test_profile_change_reloads_state(self) -> None:
        with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
            cfg_a = self._saved_cfg(root_a, "/remote/a", True)
            cfg_b = self._saved_cfg(root_b, "/remote/b", False)
            widget = self._make_widget(cfg_a)
            self.assertTrue(widget.btn_sync_browsing.isChecked())
            widget.set_session(
                {
                    "connected": True,
                    "files": SimpleNamespace(supports_progressive_listing=False, listdir_entries=lambda _d: []),
                    "cfg": cfg_b,
                    "profile_name": "other",
                }
            )
            self.assertFalse(widget.btn_sync_browsing.isChecked())
            self.assertEqual(widget._sync_roots.remote_root, "/remote/b")

class ResetRootsTests(unittest.TestCase):
    pytestmark = [pytest.mark.gui, pytest.mark.qt, pytest.mark.semantic]

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_reset_persists_new_pair_after_confirmation(self) -> None:
        from hpc_gui.core.i18n import load_language
        from hpc_gui.config.storage import load_profiles
        from hpc_gui.ui.widgets.ftp_widget import FtpWidget
        from unittest import mock

        load_language("en")
        stored = {
            "name": "lab",
            "id": "stable-id",
            "host": "h",
            "password_enc": "token",
            "system_template_source": {"kind": "plugin"},
            "file_manager": {
                "sync": {"enabled": True, "local_root": "/old", "remote_root": "/old-r"}
            },
        }
        with (
            mock.patch.object(Path, "home") as home_mock,
            tempfile.TemporaryDirectory() as tmp,
        ):
            home_mock.return_value = Path(tmp)
            from hpc_gui.config import storage as storage_mod

            storage_mod.upsert_profile(dict(stored))
            state_patch = mock.patch(
                "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
                return_value={
                    "local_dir": os.getcwd(),
                    "active_remote": "scratch",
                    "splitter_sizes": [500, 500],
                },
            )
            type_patch = mock.patch(
                "hpc_gui.ui.widgets.ftp_widget.get_ftp_transfer_type",
                return_value="auto",
            )
            update_patch = mock.patch(
                "hpc_gui.ui.widgets.ftp_widget.update_ftp_state",
                return_value={},
            )
            state_patch.start()
            type_patch.start()
            update_patch.start()
            try:
                with tempfile.TemporaryDirectory() as new_root:
                    widget = FtpWidget()
                    try:
                        widget.session = {
                            "connected": True,
                            "files": SimpleNamespace(supports_progressive_listing=False, listdir_entries=lambda _d: []),
                            "cfg": None,
                            "profile_name": "lab",
                        }
                        widget.local_panel.current_dir = new_root
                        widget.panel_scratch.current_dir = "/arf/scratch/user/proje"
                        answers = iter([True])
                        with mock.patch.object(
                            FtpWidget,
                            "_confirm_sync_pair",
                            lambda self, left, right: next(answers),
                        ), mock.patch.object(
                            widget.panel_scratch,
                            "set_dir",
                            lambda target: True,
                        ):
                            widget._reset_synchronized_roots()

                        profile = load_profiles()[0]
                        fm = profile["file_manager"]
                        sync = fm["sync"]
                        self.assertEqual(sync["local_root"], new_root)
                        self.assertEqual(sync["remote_root"], "/arf/scratch/user/proje")
                        self.assertTrue(sync["enabled"])
                        # FM-01 guarantees still hold after a sync write.
                        self.assertEqual(profile["id"], "stable-id")
                        self.assertEqual(profile["password_enc"], "token")
                        self.assertEqual(
                            profile["system_template_source"], {"kind": "plugin"}
                        )
                        self.assertEqual(widget._sync_roots.local_root, new_root)
                    finally:
                        widget.deleteLater()
            finally:
                state_patch.stop()
                type_patch.stop()
                update_patch.stop()
