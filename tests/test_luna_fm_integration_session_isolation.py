"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations
from support.test_luna_fm_integration_shared import (
    Path,
    QApplication,
    SimpleNamespace,
    _WidgetHarness,
    normalize_file_manager_settings,
    normalize_jump_host_settings,
    pytest,
    sys,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

@pytest.mark.integration
@pytest.mark.qt
class ProfileSessionIsolationTests(unittest.TestCase):
    """Part B: A -> disconnect -> B -> disconnect -> A leaks nothing."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def _cfg(self, name: str):
        fm = normalize_file_manager_settings(
            {
                "local_start_dir": f"/start/{name}",
                "comparison_enabled": True,
                "sync": {
                    "enabled": True,
                    "local_root": f"/L/{name}",
                    "remote_root": f"/R/{name}",
                },
            }
        )
        return SimpleNamespace(
            username=f"user-{name}",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
            file_manager_settings=fm,
            jump_host_settings=normalize_jump_host_settings(
                {"enabled": True, "host": f"gw-{name}", "port": 2222}
            ),
            transfer_parallelism=4 if name == "beta" else 1,
            keepalive_interval_seconds=60 if name == "beta" else 30,
            host_key_policy="strict" if name == "beta" else "accept-new",
            ssh_timeout=None,
        )

    def test_switching_profiles_does_not_leak_state(self) -> None:
        from hpc_gui.ui.widgets.ftp_widget import FtpWidget

        harness = _WidgetHarness()
        self.addCleanup(harness.stop)
        widget = FtpWidget()
        self.addCleanup(widget.shutdown)
        self.addCleanup(widget.deleteLater)
        files = SimpleNamespace(
            supports_progressive_listing=False,
            listdir_entries=lambda _d: [],
        )

        def connect(cfg_name):
            widget.set_session(
                {
                    "connected": True,
                    "files": files,
                    "cfg": self._cfg(cfg_name),
                    "profile_name": cfg_name,
                }
            )

        connect("alpha")
        alpha_roots = widget._sync_roots
        alpha_parallelism = widget.session["cfg"].transfer_parallelism
        alpha_policy = widget.session["cfg"].host_key_policy
        widget.set_session(None)
        connect("beta")
        self.assertNotEqual(
            (widget._sync_roots.local_root, widget._sync_roots.remote_root),
            (alpha_roots.local_root, alpha_roots.remote_root),
        )
        self.assertEqual(widget.session["cfg"].transfer_parallelism, 4)
        self.assertEqual(widget.session["cfg"].keepalive_interval_seconds, 60)
        self.assertEqual(widget.session["cfg"].host_key_policy, "strict")
        self.assertEqual(widget.session["cfg"].jump_host_settings["host"], "gw-beta")
        widget.set_session(None)
        connect("alpha")
        self.assertEqual(
            (widget._sync_roots.local_root, widget._sync_roots.remote_root),
            ("/L/alpha", "/R/alpha"),
        )
        self.assertEqual(widget.session["cfg"].transfer_parallelism, alpha_parallelism)
        self.assertEqual(widget.session["cfg"].host_key_policy, alpha_policy)
        self.assertEqual(widget.session["cfg"].jump_host_settings["host"], "gw-alpha")
