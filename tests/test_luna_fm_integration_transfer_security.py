"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations
from support.test_luna_fm_integration_shared import (
    Path,
    normalize_jump_host_settings,
    pytest,
    sys,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
