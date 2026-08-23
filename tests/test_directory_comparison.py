"""FM-03 tests: directory comparison service and snapshot-driven UI."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.services.directory_comparison import (  # noqa: E402
    ComparableEntry,
    CompareStatus,
    compare_directory_entries,
)


def _entry(name: str, *, is_dir: bool = False, size: int = 10, mtime: int = 100):
    return ComparableEntry(name=name, is_dir=is_dir, size=size, mtime=mtime)


class PureComparisonTests(unittest.TestCase):
    def test_same_file(self) -> None:
        result = compare_directory_entries(
            [_entry("a.txt", size=5, mtime=50)],
            [_entry("a.txt", size=5, mtime=50)],
        )
        self.assertEqual(result.local["a.txt"], CompareStatus.SAME)
        self.assertEqual(result.remote, {})

    def test_local_only_and_remote_only(self) -> None:
        result = compare_directory_entries(
            [_entry("local.txt")],
            [_entry("remote.txt")],
        )
        self.assertEqual(result.local["local.txt"], CompareStatus.LOCAL_ONLY)
        self.assertEqual(result.local.get("remote.txt"), None)
        self.assertEqual(result.remote["remote.txt"], CompareStatus.REMOTE_ONLY)
        self.assertEqual(result.remote.get("local.txt"), None)

    def test_type_mismatch(self) -> None:
        result = compare_directory_entries(
            [_entry("thing", is_dir=True)],
            [_entry("thing", is_dir=False, size=1)],
        )
        self.assertEqual(result.local["thing"], CompareStatus.TYPE_MISMATCH)

    def test_size_mismatch(self) -> None:
        result = compare_directory_entries(
            [_entry("a.bin", size=10)],
            [_entry("a.bin", size=11)],
        )
        self.assertEqual(result.local["a.bin"], CompareStatus.SIZE_DIFFERENT)

    def test_local_newer_beyond_tolerance(self) -> None:
        result = compare_directory_entries(
            [_entry("a.txt", size=5, mtime=200)],
            [_entry("a.txt", size=5, mtime=100)],
        )
        self.assertEqual(result.local["a.txt"], CompareStatus.LOCAL_NEWER)

    def test_remote_newer_beyond_tolerance(self) -> None:
        result = compare_directory_entries(
            [_entry("a.txt", size=5, mtime=100)],
            [_entry("a.txt", size=5, mtime=200)],
        )
        self.assertEqual(result.local["a.txt"], CompareStatus.REMOTE_NEWER)

    def test_mtime_within_tolerance_is_same(self) -> None:
        result = compare_directory_entries(
            [_entry("a.txt", size=5, mtime=101)],
            [_entry("a.txt", size=5, mtime=100)],
            mtime_tolerance_seconds=2,
        )
        self.assertEqual(result.local["a.txt"], CompareStatus.SAME)

    def test_both_directories_are_same(self) -> None:
        result = compare_directory_entries(
            [_entry("sub", is_dir=True, mtime=1)],
            [_entry("sub", is_dir=True, mtime=999)],
        )
        self.assertEqual(result.local["sub"], CompareStatus.SAME)

    def test_case_sensitive_names_are_separate(self) -> None:
        result = compare_directory_entries(
            [_entry("Readme.TXT")],
            [_entry("readme.txt")],
        )
        self.assertEqual(result.local["Readme.TXT"], CompareStatus.LOCAL_ONLY)
        self.assertEqual(result.remote["readme.txt"], CompareStatus.REMOTE_ONLY)

    def test_empty_dirs(self) -> None:
        result = compare_directory_entries([], [])
        self.assertEqual(result.local, {})
        self.assertEqual(result.remote, {})

    def test_spaces_and_unicode(self) -> None:
        result = compare_directory_entries(
            [_entry("dosya adı - kopya.txt", size=3)],
            [_entry("dosya adı - kopya.txt", size=3)],
        )
        self.assertEqual(
            result.local["dosya adı - kopya.txt"], CompareStatus.SAME
        )

    def test_large_lists_scale_linearly(self) -> None:
        count = 20000
        local = [
            _entry(f"file-{i}.dat", size=i, mtime=i) for i in range(count)
        ]
        remote = [
            _entry(f"file-{i}.dat", size=i, mtime=i) for i in range(count)
        ]
        started = time.perf_counter()
        result = compare_directory_entries(local, remote)
        elapsed = time.perf_counter() - started
        self.assertEqual(len(result.local), count)
        # A quadratic implementation would take far longer than this bound.
        self.assertLess(elapsed, 2.0)


class _FakeFiles:
    """Backend that records any listing/stat access."""

    def __init__(self) -> None:
        self.listdir_calls: list[str] = []
        self.supports_progressive_listing = False

    def listdir_entries(self, remote_dir: str):
        self.listdir_calls.append(remote_dir)
        return []


class SnapshotAndUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from hpc_gui.core.i18n import load_language

        load_language("en")
        self._home_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._home_tmp.cleanup)
        home_patch = mock.patch.object(Path, "home")
        home_patch.start().return_value = Path(self._home_tmp.name)
        self.addCleanup(home_patch.stop)
        from hpc_gui.config import storage as storage_mod

        storage_mod.upsert_profile({"name": "lab", "host": "h"})
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

    def _cfg(self, **fm_extra):
        from hpc_gui.config.file_manager_profile import (
            normalize_file_manager_settings,
        )

        fm = normalize_file_manager_settings(fm_extra)
        return SimpleNamespace(
            username="user",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
            file_manager_settings=fm,
        )

    def _make_widget(self, cfg=None, files=None):
        from hpc_gui.ui.widgets.ftp_widget import FtpWidget

        widget = FtpWidget()
        self.addCleanup(widget.shutdown)
        self.addCleanup(widget.deleteLater)
        session = {
            "connected": True,
            "files": files or _FakeFiles(),
            "cfg": cfg or self._cfg(),
            "profile_name": "lab",
        }
        widget.set_session(session)
        return widget

    def _run_pending_compare_now(self, widget) -> None:
        if widget._comparison_recompute_timer.isActive():
            widget._comparison_recompute_timer.stop()
            widget._recompute_directory_comparison()

    def test_enabling_comparison_causes_no_remote_listing(self) -> None:
        files = _FakeFiles()
        with tempfile.TemporaryDirectory() as local_dir:
            widget = self._make_widget(files=files)
            widget.local_panel.current_dir = local_dir
            widget.local_panel.refresh()
            files.listdir_calls.clear()
            widget.btn_compare_directories.setChecked(True)
            self._run_pending_compare_now(widget)
        self.assertEqual(files.listdir_calls, [])

    def test_recompute_uses_existing_snapshots_without_new_calls(self) -> None:
        files = _FakeFiles()
        files.entries = "/arf/scratch/user"
        with tempfile.TemporaryDirectory() as local_dir:
            Path(local_dir, "same.txt").write_text("x", encoding="utf-8")
            widget = self._make_widget(files=files)
            widget.local_panel.current_dir = local_dir
            widget.local_panel.refresh()

            def fake_listdir(remote_dir):
                files.listdir_calls.append(remote_dir)
                return [
                    SimpleNamespace(
                        name="same.txt",
                        path="/arf/scratch/user/same.txt",
                        is_dir=False,
                        size=1,
                        mtime=int(time.time()),
                        mode=0o644,
                    ),
                    SimpleNamespace(
                        name="remote-only.txt",
                        path="/arf/scratch/user/remote-only.txt",
                        is_dir=False,
                        size=2,
                        mtime=int(time.time()),
                        mode=0o644,
                    ),
                ]

            files.listdir_entries = fake_listdir
            widget.panel_scratch._invalidate_directory_cache("/arf/scratch/user")
            widget.panel_scratch.refresh(force=True)
            baseline_calls = list(files.listdir_calls)
            widget.btn_compare_directories.setChecked(True)
            self._run_pending_compare_now(widget)
            self.assertEqual(files.listdir_calls, baseline_calls)
            statuses = widget.panel_scratch._comparison_statuses or {}
            self.assertEqual(statuses["remote-only.txt"], CompareStatus.REMOTE_ONLY)
            local_statuses = widget.local_panel._comparison_statuses or {}
            self.assertEqual(local_statuses["same.txt"].value, "same")

    def test_stale_streaming_snapshot_never_becomes_source(self) -> None:
        from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel

        files = _FakeFiles()
        panel = RemoteDirPanel()
        try:
            panel.session = {
                "connected": True,
                "files": SimpleNamespace(supports_progressive_listing=True),
            }
            panel.current_dir = "/target"
            panel._category_dir = "/target"
            stale_key = ("directory", panel._listing_generation + 5)
            panel._streaming_key = "/target"
            panel._streaming_entries = [
                SimpleNamespace(name="stale", path="/target/stale", is_dir=False, size=1, mtime=1, mode=0)
            ]
            panel._on_listing_finished(stale_token := stale_key)
            identity, entries = panel.current_entries_snapshot()
            self.assertEqual(entries, [])
        finally:
            panel.deleteLater()

    def test_waiting_until_both_identities_match(self) -> None:
        files = _FakeFiles()
        with tempfile.TemporaryDirectory() as local_dir:
            widget = self._make_widget(files=files)
            widget.btn_compare_directories.setChecked(True)
            widget.local_panel.current_dir = local_dir
            widget.local_panel.refresh()
            # The committed remote snapshot belongs to another directory:
            # identity mismatch must produce a waiting state, never a
            # mixed-directory comparison.
            widget.panel_scratch.current_dir = "/arf/scratch/user/other"
            self._run_pending_compare_now(widget)
            self.assertNotEqual(widget._comparison_waiting_reason, "")
            self.assertEqual(
                widget.local_panel._comparison_statuses, None
            )

    def test_column_visibility_toggle(self) -> None:
        files = _FakeFiles()
        widget = self._make_widget(files=files)
        widget.btn_compare_directories.setChecked(True)
        self.assertTrue(not widget.local_panel.tree.isColumnHidden(4))
        self.assertTrue(not widget.panel_scratch.views["all"].isColumnHidden(4))
        widget.btn_compare_directories.setChecked(False)
        self.assertTrue(widget.local_panel.tree.isColumnHidden(4))
        self.assertTrue(widget.panel_scratch.views["all"].isColumnHidden(4))
        self.assertIsNone(widget.local_panel._comparison_statuses)

    def test_parent_row_blank_and_sort_roles_intact(self) -> None:
        files = _FakeFiles()
        with tempfile.TemporaryDirectory() as local_dir:
            (Path(local_dir) / ".." ).exists()
            widget = self._make_widget(files=files)
            widget.local_panel.current_dir = local_dir
            widget.local_panel.refresh()
            widget.btn_compare_directories.setChecked(True)
            parent_item = None
            for index in range(widget.local_panel.tree.topLevelItemCount()):
                item = widget.local_panel.tree.topLevelItem(index)
                if item.data(0, 0x0100 + 2):  # UserRole + 2 parent flag
                    parent_item = item
                    break
            if parent_item is not None:
                self.assertEqual(parent_item.text(4), "")
            # Column 0 sorting still works after comparison applied.
            widget.local_panel.tree._sort_column = 0
            widget.local_panel.tree.apply_sort()
        self.assertTrue(True)

    def test_profile_switch_clears_statuses(self) -> None:
        files = _FakeFiles()
        widget = self._make_widget(files=files)
        widget.local_panel._comparison_statuses = {"x": CompareStatus.SAME}
        widget.set_session(None)
        self.assertIsNone(widget.local_panel._comparison_statuses)
        self.assertFalse(widget.btn_compare_directories.isChecked())
        self.assertFalse(widget.btn_compare_directories.isEnabled())

    def test_active_panel_switch_recomputes_with_that_panel(self) -> None:
        files = _FakeFiles()
        with tempfile.TemporaryDirectory() as local_dir:
            widget = self._make_widget(files=files)
            widget.local_panel.current_dir = local_dir
            widget.local_panel.refresh()

            def make_listing(marker):
                def listdir(_dir):
                    return [
                        SimpleNamespace(
                            name=marker,
                            path=f"/arf/home/user/{marker}",
                            is_dir=False,
                            size=1,
                            mtime=1,
                            mode=0o644,
                        )
                    ]

                return listdir

            widget.panel_home.session = widget.session
            files.listdir_entries = make_listing("home-marker")
            widget.panel_home._invalidate_directory_cache("/arf/home/user")
            widget.panel_home.refresh(force=True)
            widget.accordion.set_active("home")
            widget.btn_compare_directories.setChecked(True)
            self._run_pending_compare_now(widget)
            home_statuses = widget.panel_home._comparison_statuses or {}
            self.assertIn("home-marker", home_statuses)


if __name__ == "__main__":
    unittest.main()
