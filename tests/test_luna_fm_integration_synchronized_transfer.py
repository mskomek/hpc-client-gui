"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations

import os

import tempfile

import time

import unittest

from pathlib import Path

from types import SimpleNamespace

from unittest import mock

import pytest

from PySide6.QtWidgets import QApplication

from hpc_gui.config.file_manager_profile import normalize_file_manager_settings

from hpc_gui.config.jump_host_profile import normalize_jump_host_settings

from hpc_gui.services.directory_comparison import CompareStatus

class _WidgetHarness:
    """Shared get_ftp_state/update_ftp_state patching for widget tests."""

    def __init__(self, local_dir: str | None = None) -> None:
        state_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
            return_value={
                "local_dir": local_dir or os.getcwd(),
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
        self._patches = (state_patch, type_patch, update_patch)

    def stop(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()

class _Entry:
    def __init__(self, name: str, *, size: int = 1):
        self.name = name
        self.path = name
        self.is_dir = False
        self.size = size
        self.mtime = int(time.time())
        self.mode = 0o644

class _FakeActivePanel:
    """Minimal active-remote-panel double for comparison orchestration."""

    def __init__(self, directory: str) -> None:
        self.current_dir = directory
        self._snapshot: tuple[str, list] = ("", [])

    def set_dir(self, target: str) -> None:
        self.current_dir = target

    def commit(self, directory: str, entries: list) -> None:
        self._snapshot = (directory, list(entries))

    def current_entries_snapshot(self):
        if self._snapshot[0] != self.current_dir:
            return "", []
        return self._snapshot

    def clear_comparison_statuses(self) -> None:
        return None

    def apply_comparison_statuses(self, statuses: dict) -> None:
        self.applied = dict(statuses)

@pytest.mark.integration
@pytest.mark.qt
class SyncPlusComparisonOrderingTests(unittest.TestCase):
    """Part C critical scenario: never render B(local) vs A(remote)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def _run_pending(self, widget) -> None:
        widget._comparison_recompute_timer.stop()
        widget._recompute_directory_comparison()

    def test_navigation_ordering_never_shows_mixed_result(self) -> None:
        with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
            Path(root_a, "markerA.txt").write_text("a", encoding="utf-8")
            Path(root_b, "markerB.txt").write_text("b", encoding="utf-8")
            harness = _WidgetHarness(local_dir=root_a)
            self.addCleanup(harness.stop)
            from hpc_gui.ui.widgets.ftp_widget import FtpWidget

            listing_calls: list[str] = []

            def fake_listdir(d):
                listing_calls.append(d)
                # Remote B contains markerB; remote A contains markerA.
                if d.rstrip("/").endswith("/remote/B"):
                    return [_Entry("markerB.txt")]
                return [_Entry("markerA.txt")]

            files = SimpleNamespace(
                supports_progressive_listing=False,
                listdir_entries=fake_listdir,
            )
            cfg = SimpleNamespace(
                username="user",
                system_settings={
                    "scratch_dir": "/arf/scratch/{user}",
                    "home_dir": "/arf/home/{user}",
                },
                file_manager_settings=normalize_file_manager_settings(
                    {
                        "comparison_enabled": True,
                        "sync": {
                            "enabled": True,
                            "local_root": "/syncroot",
                            "remote_root": "/remote",
                        },
                    }
                ),
            )
            widget = FtpWidget()
            self.addCleanup(widget.shutdown)
            self.addCleanup(widget.deleteLater)
            widget.set_session(
                {
                    "connected": True,
                    "files": files,
                    "cfg": cfg,
                    "profile_name": "lab",
                }
            )
            active_panel = _FakeActivePanel("/remote/A")
            with mock.patch.object(
                FtpWidget, "active_remote_panel", return_value=active_panel
            ):
                widget.btn_sync_browsing.setChecked(True)
                # Stage 1: A/A displayed and compared as SAME.
                widget.local_panel.refresh()
                active_panel.commit(
                    "/remote/A",
                    [
                        SimpleNamespace(
                            name="markerA.txt",
                            path="/remote/A/markerA.txt",
                            is_dir=False,
                            size=1,
                            mtime=int(time.time()),
                            mode=0o644,
                        )
                    ],
                )
                self._run_pending(widget)
                self.assertEqual(
                    widget.local_panel._comparison_statuses.get("markerA.txt"),
                    CompareStatus.SAME,
                )
                # Stage 2/3: user navigates local to B; sync maps the remote
                # side immediately.  While the remote B listing has not
                # landed, the old result must be cleared/waiting - never a
                # mixed A/B view.
                widget.local_panel.current_dir = root_b
                widget.local_panel.refresh()
                active_panel.set_dir("/remote/B")
                self._run_pending(widget)
                self.assertEqual(widget.local_panel._comparison_statuses or {}, {})
                self.assertNotEqual(widget._comparison_waiting_reason, "")
                # Stage 5/7: remote B listing lands and commits.
                active_panel.commit(
                    "/remote/B",
                    [
                        SimpleNamespace(
                            name="markerB.txt",
                            path="/remote/B/markerB.txt",
                            is_dir=False,
                            size=1,
                            mtime=int(time.time()),
                            mode=0o644,
                        )
                    ],
                )
                self._run_pending(widget)
                # Only B-vs-B is rendered, exactly once coherent.
                self.assertEqual(
                    widget.local_panel._comparison_statuses,
                    {"markerB.txt": CompareStatus.SAME},
                )

@pytest.mark.integration
@pytest.mark.qt
class ZeroExtraNetworkIntegrationTests(unittest.TestCase):
    """Part E: comparison never causes extra SFTP traffic end-to-end."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def test_full_scenario_counters(self) -> None:
        with tempfile.TemporaryDirectory() as local_dir:
            Path(local_dir, "same.txt").write_text("x", encoding="utf-8")
            harness = _WidgetHarness(local_dir=local_dir)
            self.addCleanup(harness.stop)
            from hpc_gui.ui.widgets.ftp_widget import FtpWidget

            counters = {"list": 0, "stat": 0, "checksum": 0}

            def counting_listdir(_d):
                counters["list"] += 1
                return [_Entry("same.txt")]

            files = SimpleNamespace(
                supports_progressive_listing=False,
                listdir_entries=counting_listdir,
                stat=lambda *_a, **_k: counters.__setitem__("stat", counters["stat"] + 1),
            )
            cfg = SimpleNamespace(
                username="user",
                system_settings={
                    "scratch_dir": "/arf/scratch/{user}",
                    "home_dir": "/arf/home/{user}",
                },
                file_manager_settings=normalize_file_manager_settings({}),
            )
            widget = FtpWidget()
            self.addCleanup(widget.shutdown)
            self.addCleanup(widget.deleteLater)

            def run_pending():
                if widget._comparison_recompute_timer.isActive():
                    widget._comparison_recompute_timer.stop()
                    widget._recompute_directory_comparison()

            # 1. normal remote folder load -> exactly one listing (from
            # set_session's Scratch navigation).
            widget.set_session(
                {
                    "connected": True,
                    "files": files,
                    "cfg": cfg,
                    "profile_name": "lab",
                }
            )
            baseline = counters["list"]
            self.assertGreaterEqual(baseline, 1)
            # 2. enable comparison -> unchanged.
            widget.panel_scratch.current_dir = "/arf/scratch/user"
            widget.panel_scratch._commit_snapshot("/arf/scratch/user", [_Entry("same.txt")])
            widget.btn_compare_directories.setChecked(True)
            # 3. repeated recomputes -> unchanged.
            for _ in range(3):
                widget._schedule_comparison_recompute()
                run_pending()
            self.assertEqual(counters["list"], baseline)
            self.assertEqual(counters["stat"], 0)
            self.assertEqual(counters["checksum"], 0)
            # 4. explicit refresh -> increments exactly because of refresh.
            widget.panel_scratch.refresh(force=True)
            self.assertEqual(counters["list"], baseline + 1)
            # 5. comparison after refresh -> no further increment.
            widget._schedule_comparison_recompute()
            run_pending()
            self.assertEqual(counters["list"], baseline + 1)

class TransferSourceOfTruthAndSecurityTests(unittest.TestCase):
    """Part F/G spot checks that pin the integrated guarantees."""

    @pytest.mark.audit
    def test_global_parallel_setting_is_not_imported_by_remote_panel(self) -> None:
        from hpc_gui.ui.widgets import remote_dir_panel

        self.assertFalse(
            hasattr(remote_dir_panel, "get_transfer_parallelism"),
            "Remote panel must not consult the deprecated global setting",
        )

    @pytest.mark.audit
    def test_no_auto_add_policy_anywhere_in_ssh_layer(self) -> None:
        for source in (
            Path("src/hpc_gui/ssh/client.py"),
            Path("src/hpc_gui/ssh/jump.py"),
        ):
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("AutoAddPolicy", text)

    @pytest.mark.contract
    def test_jump_profile_schema_has_no_password_key(self) -> None:
        settings = normalize_jump_host_settings(
            {"enabled": True, "host": "gw", "password": "should-not-survive"}
        )
        self.assertNotIn("password", settings)
