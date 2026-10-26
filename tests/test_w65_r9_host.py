"""W65 r9: Studio/Linter host-registration contract tests (HOST-002/G02).

The W65 plugins are not installed packages yet (G47 BLOCKED_ENV), so these
tests assert source-level readiness only: the r9 ``manifest_ui_contributions``
fragment must satisfy the REAL host contracts (validator + parser) with zero
errors, and must stay inert-safe (no shortcuts/icons, disabled until dispatch
binding). No host files are modified; no install/VM claim is made.
"""

from __future__ import annotations

from hpc_gui.plugins.openfoam_studio import host_adapter
from hpc_gui.plugins.ui_contributions import validate_ui_contributions_dict
from hpc_gui.plugins._ui_contribution_parser import parse_ui_contributions


def test_manifest_fragment_is_validator_clean():
    frag = host_adapter.manifest_ui_contributions()
    assert validate_ui_contributions_dict(frag) == []


def test_manifest_fragment_parses_for_studio_identity():
    frag = host_adapter.manifest_ui_contributions()
    ident = host_adapter.owning_identity()
    manifest = {"id": ident["id"], "version": ident["version"],
                "ui_contributions": frag}
    contrib = parse_ui_contributions(manifest)
    assert contrib is not None
    assert len(contrib.items) == len(host_adapter.REQUESTED_ACTIONS)


def test_fragment_carries_both_plugins_and_requires_app():
    ident = host_adapter.owning_identity()
    assert ident["id"] == "openfoam-case-studio"
    assert ident["version"] == "0.3.0-w65r1"
    assert ident["requires_app"] == ">=1.5.9"
    ids = [item["id"] for item in
           host_adapter.manifest_ui_contributions()["plugins_menu"]["items"]]
    assert "of.openStudio" in ids
    assert "of.newCase" in ids
    assert "of.createJob" in ids
    assert "of.validate" in ids
    assert "of.linter" in [entry["id"] for entry in host_adapter.PLUGIN_MENU]


def test_fragment_items_stay_inert_safe():
    for item in host_adapter.manifest_ui_contributions()["plugins_menu"]["items"]:
        assert item["kind"] == "action"
        assert item["unavailable"] == "disable"
        assert "shortcut" not in item and "icon" not in item and "icon_path" not in item
        assert set(item) <= {"kind", "id", "label", "labels", "action",
                             "when", "unavailable"}
    assert "tr" in host_adapter.manifest_ui_contributions()["plugins_menu"]["labels"]


def test_legacy_contributions_shape_unchanged():
    legacy = host_adapter.contributions()
    assert set(legacy) == {"file_context", "plugin_menu", "requires_app", "sftp mirrored"}
    assert len(legacy["file_context"]) == 4
    assert len(legacy["plugin_menu"]) == 2


def test_unknown_top_level_key_rejected_by_host_validator():
    bad = {"plugins_menu": host_adapter.manifest_ui_contributions()["plugins_menu"],
           "file_context": []}
    assert validate_ui_contributions_dict(bad) != []
