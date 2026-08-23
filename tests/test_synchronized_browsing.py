"""FM-02 tests: synchronized browsing mapping service and widget behavior."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.config.file_manager_profile import (  # noqa: E402
    normalize_file_manager_settings,
    patch_file_manager_settings,
)
from hpc_gui.services.synchronized_browsing import (  # noqa: E402
    SyncRoots,
    local_to_remote,
    normalize_local_root,
    normalize_remote_root,
    remote_to_local,
)


class LocalMappingTests(unittest.TestCase):
    WINDOWS_ROOTS = SyncRoots(
        local_root=r"C:\CFD\new_dpler",
        remote_root="/arf/scratch/user/new_dpler",
    )
    POSIX_ROOTS = SyncRoots(
        local_root="/home/user/work",
        remote_root="/arf/home/user/work",
    )

    def test_local_root_maps_to_remote_root(self) -> None:
        self.assertEqual(
            local_to_remote(r"C:\CFD\new_dpler", self.WINDOWS_ROOTS),
            "/arf/scratch/user/new_dpler",
        )

    def test_one_nested_level(self) -> None:
        self.assertEqual(
            local_to_remote(r"C:\CFD\new_dpler\case1", self.WINDOWS_ROOTS),
            "/arf/scratch/user/new_dpler/case1",
        )
        self.assertEqual(
            remote_to_local(
                "/arf/scratch/user/new_dpler/case1", self.WINDOWS_ROOTS
            ),
            os.path.normpath(r"C:\CFD\new_dpler\case1"),
        )

    def test_deep_nested_both_directions(self) -> None:
        local = r"C:\CFD\new_dpler\a\b\c\d"
        remote = "/arf/scratch/user/new_dpler/a/b/c/d"
        mapped = local_to_remote(local, self.WINDOWS_ROOTS)
        self.assertEqual(mapped, remote)
        back = remote_to_local(remote, self.WINDOWS_ROOTS)
        self.assertEqual(Path(back), Path(local))

    def test_prefix_collision_is_not_contained(self) -> None:
        self.assertIsNone(local_to_remote(r"C:\CFD\new_dpler2", self.WINDOWS_ROOTS))

    def test_outside_root_returns_none(self) -> None:
        self.assertIsNone(local_to_remote(r"C:\Other\dir", self.WINDOWS_ROOTS))

    def test_windows_case_insensitive_containment_preserves_text(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows-only case rule")
        mapped = local_to_remote(r"c:\cfd\NEW_DPLER\Case", self.WINDOWS_ROOTS)
        self.assertEqual(mapped, "/arf/scratch/user/new_dpler/Case")

    def test_different_drives_return_none(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows-only drive rule")
        self.assertIsNone(local_to_remote(r"D:\CFD\new_dpler", self.WINDOWS_ROOTS))

    def test_dot_segments_are_normalized(self) -> None:
        self.assertEqual(
            local_to_remote(r"C:\CFD\.\new_dpler\sub", self.WINDOWS_ROOTS),
            "/arf/scratch/user/new_dpler/sub",
        )

    def test_dotdot_must_not_escape_root(self) -> None:
        self.assertIsNone(
            local_to_remote(r"C:\CFD\new_dpler\..\escape", self.WINDOWS_ROOTS)
        )

    def test_unicode_and_spaces_survive(self) -> None:
        roots = SyncRoots(r"C:\work\projem", "/remote/projem")
        mapped = local_to_remote(r"C:\work\projem\dosya adı - kopya", roots)
        self.assertEqual(mapped, "/remote/projem/dosya adı - kopya")

    def test_trailing_separators_do_not_mismatch(self) -> None:
        roots = SyncRoots(
            r"C:\CFD\new_dpler" + os.sep, "/arf/scratch/user/new_dpler/"
        )
        self.assertEqual(
            local_to_remote(r"C:\CFD\new_dpler\sub", roots),
            "/arf/scratch/user/new_dpler/sub",
        )

    def test_posix_local_roots_stay_case_sensitive_off_windows(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX-only exact-case rule")
        self.assertEqual(
            local_to_remote("/home/user/work/Sub", self.POSIX_ROOTS),
            "/arf/home/user/work/Sub",
        )


class RemoteMappingTests(unittest.TestCase):
    ROOTS = SyncRoots(
        local_root=r"C:\CFD\new_dpler",
        remote_root="/arf/scratch/user",
    )

    def test_remote_root_maps_to_local_root(self) -> None:
        self.assertEqual(
            Path(remote_to_local("/arf/scratch/user", self.ROOTS)),
            Path(r"C:\CFD\new_dpler"),
        )

    def test_nested_maps_back(self) -> None:
        self.assertEqual(
            Path(remote_to_local("/arf/scratch/user/runs/r1", self.ROOTS)),
            Path(r"C:\CFD\new_dpler\runs\r1"),
        )

    def test_remote_prefix_collision_rejected(self) -> None:
        self.assertIsNone(
            remote_to_local("/arf/scratch/user2/run", self.ROOTS)
        )

    def test_outside_remote_root_rejected(self) -> None:
        self.assertIsNone(remote_to_local("/arf/home/user", self.ROOTS))

    def test_dotdot_escape_rejected(self) -> None:
        self.assertIsNone(
            remote_to_local("/arf/scratch/user/../../etc", self.ROOTS)
        )

    def test_slash_root_pair_works(self) -> None:
        roots = SyncRoots(r"C:\mirror", "/")
        self.assertEqual(
            remote_to_local("/arf/x", roots), os.path.normpath(r"C:\mirror\arf\x")
        )
        self.assertEqual(
            local_to_remote(r"C:\mirror\arf\x", roots), "/arf/x"
        )

    def test_trailing_slashes_do_not_mismatch(self) -> None:
        self.assertEqual(
            remote_to_local("/arf/scratch/user/", self.ROOTS),
            remote_to_local("/arf/scratch/user", self.ROOTS),
        )

    def test_normalize_helpers(self) -> None:
        self.assertEqual(normalize_remote_root("/a/b/"), "/a/b")
        self.assertEqual(normalize_remote_root(""), "/")
        raw = "C:\\a\\b\\" if os.name == "nt" else "/a/b"
        expected = Path("C:\\a\\b") if os.name == "nt" else Path("/a/b")
        self.assertEqual(Path(normalize_local_root(raw)), expected)


class SyncSchemaTests(unittest.TestCase):
    def test_malformed_sync_gives_defaults(self) -> None:
        settings = normalize_file_manager_settings({"sync": "junk"})
        sync = settings["sync"]
        self.assertFalse(sync["enabled"])
        self.assertEqual(sync["local_root"], "")
        self.assertEqual(sync["remote_root"], "")

    def test_enabled_normalizes_to_real_bool(self) -> None:
        settings = normalize_file_manager_settings({"sync": {"enabled": 1}})
        self.assertIs(settings["sync"]["enabled"], False)
        settings = normalize_file_manager_settings({"sync": {"enabled": True}})
        self.assertIs(settings["sync"]["enabled"], True)

    def test_patch_preserves_sync_siblings_and_unknown_keys(self) -> None:
        existing = {
            "local_start_dir": "/tmp/w",
            "future_key": {"x": 1},
            "sync": {"enabled": True, "local_root": "/L", "remote_root": "/R"},
        }
        patched = patch_file_manager_settings(existing, {"sync": {"enabled": False}})
        self.assertFalse(patched["sync"]["enabled"])
        self.assertEqual(patched["sync"]["local_root"], "/L")
        self.assertEqual(patched["sync"]["remote_root"], "/R")
        self.assertEqual(patched["local_start_dir"], "/tmp/w")
        self.assertEqual(patched["future_key"], {"x": 1})


class _CountingRemotePanel:
    """Records set_dir calls without touching a real backend."""

    def __init__(self) -> None:
        self.current_dir = "/start"
        self.set_dir_calls: list[str] = []

    def set_dir(self, target: str) -> bool:
        self.set_dir_calls.append(target)
        self.current_dir = target
        return True


class SynchronizationOrchestrationTests(unittest.TestCase):
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

    def test_existing_valid_roots_enable_without_navigation_or_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            widget = self._make_widget(self._saved_cfg(root, "/remote/root", False))
            panel = _CountingRemotePanel()
            with patch.object(widget, "active_remote_panel", return_value=panel):
                widget.btn_sync_browsing.setChecked(True)
            self.assertTrue(widget.btn_sync_browsing.isChecked())
            self.assertEqual(panel.set_dir_calls, [])

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


if __name__ == "__main__":
    unittest.main()
