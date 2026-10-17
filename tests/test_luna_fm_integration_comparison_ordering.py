"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations
from support.test_luna_fm_integration_shared import (
    CompareStatus,
    Path,
    QApplication,
    SimpleNamespace,
    _Entry,
    _FakeActivePanel,
    _WidgetHarness,
    mock,
    normalize_file_manager_settings,
    pytest,
    sys,
    tempfile,
    time,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
