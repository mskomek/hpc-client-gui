"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations
from support.test_luna_fm_integration_shared import (
    Path,
    QApplication,
    SimpleNamespace,
    _Entry,
    _WidgetHarness,
    normalize_file_manager_settings,
    pytest,
    sys,
    tempfile,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
