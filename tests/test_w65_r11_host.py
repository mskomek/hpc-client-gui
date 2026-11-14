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

BASE_OPENFOAM_KEYS = frozenset({
    "add_case", "add_file", "apply_confirm", "blocked_external", "cancel",
    "cancel_requested", "cancelled", "create_job", "details", "diagnostics",
    "dictionary_filter", "draft_only", "edition", "export_json", "file",
    "files", "finding", "flow", "inspector", "line", "lint_failed",
    "lint_running", "lint_summary", "linter", "linter_title",
    "linter_unavailable", "local_path_required", "location", "new_case",
    "no_findings", "open_studio", "remote_path_invalid", "remote_selection",
    "remote_session_missing", "report_saved", "results", "results_stale",
    "revert", "rule", "rules", "run_before_export", "run_preview",
    "select_path", "severity", "source_diff", "source_open_failed",
    "static_only", "title", "validate", "validation", "verification",
})

EXPECTED_OPENFOAM_KEYS = BASE_OPENFOAM_KEYS | frozenset({
    "add_workflow_step", "allrun_create_failed", "allrun_created",
    "allrun_preserved", "apply_parameter", "case_create_failed",
    "case_exists", "case_name", "case_name_prompt", "case_open_failed",
    "case_opened", "case_preview", "case_root", "case_structure",
    "choose_case_mode", "choose_parent", "close", "close_tab",
    "command_library", "commands_draft_only", "create_allrun",
    "create_allrun_create_only", "dictionary_count", "dictionary_open_failed",
    "diff", "discard_unsaved_edits", "draft_allrun_mismatch",
    "draft_allrun_required", "draft_build_failed", "draft_preview_header",
    "draft_preview_summary", "draft_save_requires_writable_case",
    "filter_commands", "generated_allrun_review", "generated_slurm_review",
    "generating_allrun", "invalid_case_name", "invalid_job_inputs",
    "invalid_workflow_command", "job_draft_title", "job_name",
    "linter_not_installed", "local", "modified_files", "module",
    "move_workflow_down", "move_workflow_up", "no_case", "no_case_prompt",
    "no_changes", "no_parameters_verified", "no_regions_declared", "nodes",
    "nothing_submitted", "ntasks_integer_required", "open_case", "open_snapshot",
    "parameter_applied", "parameter_invalid", "parameter_type",
    "parameter_type_unknown", "partition", "problems", "raw_value_locked",
    "read_only_allrun", "read_only_draft_blocked", "read_only_snapshot",
    "read_only_snapshot_mode", "recover_save", "recovery_failed",
    "recovery_failed_simple", "recovery_index_unavailable",
    "recovery_not_persisted", "recovery_remote_unavailable", "recovery_running",
    "recovery_wrong_profile", "redo", "refresh_preview", "regions",
    "regions_unresolved", "remote", "remote_case_path", "remote_loading",
    "remote_snapshot_path", "remote_unavailable", "remove_workflow_step",
    "review_scripts_before_saving", "runtime_not_run", "save_before_allrun",
    "save_case", "save_failed", "save_failed_simple", "save_recovered",
    "save_recovery", "save_success", "save_wrapper_create_only", "search_case",
    "search_dictionaries", "select_scalar", "snapshot_mode", "snapshot_read_only",
    "solver", "source", "starter_readme", "tasks", "undo", "unknown_solver",
    "unsaved_draft_blocked", "validation_complete", "validation_failed",
    "validation_unavailable", "visual_flow", "walltime", "workflow_added",
    "lint_status_profile", "lint_status_version",
    "workflow_drag_hint", "workflow_removed", "wrapper_created",
    "wrapper_preserved", "wrapper_save_failed",
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
