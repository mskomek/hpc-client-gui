"""W65 r11: i18n parity + inert-registration regression (HOST-002/UI-012).

R10 registered the four openfoam.* host actions with a code-owned
readiness gate that keeps every dispatch inert. R12 resolved the
trusted-tool blocker (application-owned approval of the verified
openfoam-linter identity); the file-context hook stays a recorded
concrete API blocker, asserted here as a tested fact, not modified.
"""

from __future__ import annotations

import json
from pathlib import Path

from hpc_gui.plugins import models
from hpc_gui.plugins.openfoam_studio import host_adapter
from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool, trusted_tool_error
from hpc_gui.services import plugin_menu_actions as pma
from hpc_gui.services.file_context_actions import (
    context_selection,
    visible_actions,
)
from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_OPENFOAM_KEYS = frozenset({
    "blocked_external", "create_job", "draft_only", "linter", "new_case",
    "no_findings", "open_studio", "title", "validate", "flow", "inspector",
    "source_diff", "validation", "run_preview", "results", "apply_confirm",
    "revert", "linter_unavailable",
})


def _i18n_locale(name: str) -> dict:
    return json.loads((REPO_ROOT / "src" / "hpc_gui" / "i18n" / name).read_text(
        encoding="utf-8"))


def test_openfoam_i18n_keys_match_en_tr():
    en = _i18n_locale("en.json")["openfoam"]
    tr = _i18n_locale("tr.json")["openfoam"]
    assert set(en) == set(tr) == set(EXPECTED_OPENFOAM_KEYS)
    for key in EXPECTED_OPENFOAM_KEYS:
        assert isinstance(en[key], str) and en[key].strip()
        assert isinstance(tr[key], str) and tr[key].strip()


def test_inert_registration_unchanged():
    assert set(host_adapter.host_action_ids()) == set(pma.OPENFOAM_ACTIONS)
    assert len(pma.OPENFOAM_ACTIONS) == 4
    for action in pma.OPENFOAM_ACTIONS:
        assert pma.is_allowed_action(action) is True
    assert pma.is_openfoam_dispatch_ready() is False
    assert host_adapter.dispatch_readiness()["ready"] is False


def _studio_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1,
        plugin_api=1,
        id="openfoam-case-studio",
        name="OpenFOAM Case Studio",
        version="0.3.0-w65r17-auditfix1",
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
        version="0.2.0-w65r17-auditfix1",
        publisher="HPC Client GUI",
        license="test",
        description="test",
        requires_app=">=1.5.9",
        capabilities=("lint-rules", "linter-tool"),
        entrypoints={},
        files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def test_dispatch_stays_inert():
    host = WxPluginMenuHost(editor_page=None)
    studio = _studio_plugin()
    linter = _linter_plugin()
    assert host.run_openfoam_studio(studio) is False
    assert host.new_openfoam_case(studio) is False
    assert host.create_openfoam_job_draft(studio) is False
    assert host.validate_with_openfoam_linter(linter) is False


def test_file_context_hook_still_has_no_plugin_dispatch_path():
    one_file = context_selection("case.foam", False, ("case.foam",), (False,))
    one_dir = context_selection("cavity", True, ("cavity",), (True,))
    seen = set(visible_actions(one_file, remote=False))
    seen |= set(visible_actions(one_file, remote=True))
    seen |= set(visible_actions(one_dir, remote=False))
    seen |= set(visible_actions(one_dir, remote=True))
    assert not any("openfoam" in action for action in seen)


def test_trusted_tool_policy_now_approves_verified_openfoam_linter():
    # W65 r12: application-owned explicit approval (see test_w65_r10_host
    # for spoof negatives); manifests still cannot self-authorize.
    manifest = {
        "plugin_api": 2,
        "id": "openfoam-linter",
        "publisher": "HPC Client GUI",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/openfoam_lint/__init__.py"},
    }
    assert trusted_tool_error(manifest) is None
    assert is_approved_trusted_tool(manifest) is True
