"""W65 r10: OpenFOAM host registration/dispatch contract (HOST-002/G02).

R9 proved the manifest fragment is validator-clean but inert because the
host allowlist did not know the openfoam.* action ids. R10 registers the
four ids in the host allowlist with a code-owned readiness gate that keeps
every dispatch inert (menu disabled, no execution, no UI construction)
until a real wx/Qt host path is VM-proven.

R12 resolved the trusted-tool blocker below (application-owned approval of
the verified openfoam-linter identity); file-context still has no plugin
hook and stays a recorded concrete API blocker.
"""

from __future__ import annotations

from pathlib import Path

from hpc_gui.plugins import models
from hpc_gui.plugins.openfoam_studio import host_adapter
from hpc_gui.plugins.ui_contributions import (
    parse_ui_contributions,
    validate_ui_contributions_dict,
)
from hpc_gui.services import plugin_menu_actions as pma
from hpc_gui.services.file_context_actions import (
    context_selection,
    visible_actions,
)
from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost
from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool, trusted_tool_error


def _studio_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1,
        plugin_api=1,
        id="openfoam-case-studio",
        name="OpenFOAM Case Studio",
        version="0.3.0-w65r1",
        publisher="HPC Client GUI",
        license="test",
        description="test",
        requires_app=">=1.5.9",
        capabilities=("application-tools",),
        entrypoints={},
        files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def _linter_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1,
        plugin_api=1,
        id="openfoam-linter",
        name="OpenFOAM Linter",
        version="0.2.0-w65r1",
        publisher="HPC Client GUI",
        license="test",
        description="test",
        requires_app=">=1.5.9",
        capabilities=("lint-rules", "linter-tool"),
        entrypoints={},
        files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def _bare_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1,
        plugin_api=1,
        id="openfoam-case-studio",
        name="OpenFOAM Case Studio",
        version="0.3.0-w65r1",
        publisher="HPC Client GUI",
        license="test",
        description="test",
        requires_app=">=1.5.9",
        capabilities=(),
        entrypoints={},
        files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def test_fragment_stays_validator_clean_and_inert():
    frag = host_adapter.manifest_ui_contributions()
    assert validate_ui_contributions_dict(frag) == []
    ident = host_adapter.owning_identity()
    contrib = parse_ui_contributions(
        {"id": ident["id"], "version": ident["version"], "ui_contributions": frag}
    )
    assert contrib is not None
    for item in frag["plugins_menu"]["items"]:
        assert item["unavailable"] == "disable"
        assert "shortcut" not in item and "icon" not in item


def test_host_knows_openfoam_actions_but_keeps_them_pending():
    assert set(host_adapter.host_action_ids()) == set(pma.OPENFOAM_ACTIONS)
    for action in host_adapter.host_action_ids():
        assert pma.is_allowed_action(action) is True
    assert pma.is_openfoam_dispatch_ready(_studio_plugin()) is False
    assert host_adapter.dispatch_readiness()["ready"] is False


def test_can_execute_reports_pending_not_unknown():
    studio = _studio_plugin()
    for action in ("openfoam.open_studio", "openfoam.new_case",
                   "openfoam.create_job_draft"):
        allowed, reason = pma.can_execute_action(action, studio)
        assert allowed is False
        assert reason == pma.OPENFOAM_PENDING_REASON
    allowed, reason = pma.can_execute_action("openfoam.validate", _linter_plugin())
    assert allowed is False
    assert reason == pma.OPENFOAM_PENDING_REASON


def test_capability_guard_still_fires_before_readiness():
    allowed, reason = pma.can_execute_action("openfoam.open_studio", _bare_plugin())
    assert allowed is False
    assert "lacks required capability" in reason
    allowed, reason = pma.can_execute_action("openfoam.validate", _studio_plugin())
    assert allowed is False
    assert "lacks required capability" in reason
    assert pma.can_execute_action("openfoam.does_not_exist", _studio_plugin()) == (
        False, "unknown action 'openfoam.does_not_exist'")


def test_dispatch_stays_inert_without_side_effects():
    studio = _studio_plugin()
    linter = _linter_plugin()
    host = WxPluginMenuHost(editor_page=None)
    for action, plugin in (("openfoam.open_studio", studio),
                           ("openfoam.new_case", studio),
                           ("openfoam.create_job_draft", studio),
                           ("openfoam.validate", linter)):
        assert pma.dispatch_plugin_menu_action(action, plugin) is False
        assert pma.dispatch_plugin_menu_action(action, plugin, host) is False
    assert host.run_openfoam_studio(studio) is False
    assert host.new_openfoam_case(studio) is False
    assert host.create_openfoam_job_draft(studio) is False
    assert host.validate_with_openfoam_linter(linter) is False


def test_file_context_has_no_plugin_dispatch_path():
    one_file = context_selection("case.foam", False, ("case.foam",), (False,))
    one_dir = context_selection("cavity", True, ("cavity",), (True,))
    seen = set(visible_actions(one_file, remote=False))
    seen |= set(visible_actions(one_file, remote=True))
    seen |= set(visible_actions(one_dir, remote=False))
    seen |= set(visible_actions(one_dir, remote=True))
    assert not any("openfoam" in action for action in seen)


def test_trusted_tool_policy_approves_verified_openfoam_linter_engine():
    # W65 r12: application-owned explicit approval of the verified
    # openfoam-linter identity (publisher + entrypoint code-owned here).
    manifest = {
        "plugin_api": 2,
        "id": "openfoam-linter",
        "publisher": "HPC Client GUI",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/openfoam_lint/__init__.py"},
    }
    assert trusted_tool_error(manifest) is None
    assert is_approved_trusted_tool(manifest) is True


def test_trusted_tool_policy_still_rejects_spoofed_openfoam_identity():
    # A manifest cannot self-authorize: same id with a different
    # publisher, entrypoint, capability set or plugin API is rejected.
    base = {
        "plugin_api": 2,
        "id": "openfoam-linter",
        "publisher": "HPC Client GUI",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/openfoam_lint/__init__.py"},
    }
    spoofed_publisher = dict(base, publisher="Evil Corp")
    assert trusted_tool_error(spoofed_publisher) != ""
    spoofed_entrypoint = dict(base, entrypoints={"linter_engine": "engine/evil/__init__.py"})
    assert trusted_tool_error(spoofed_entrypoint) != ""
    spoofed_caps = dict(base, capabilities=["application-tools"])
    assert trusted_tool_error(spoofed_caps) != ""
    legacy_api = dict(base, plugin_api=1, capabilities=["linter-tool"])
    assert trusted_tool_error(legacy_api) != ""
    assert is_approved_trusted_tool(spoofed_publisher) is False
