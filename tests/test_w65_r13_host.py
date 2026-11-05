"""W65 r13 compatibility checks for legacy, unpinned File-menu plugins.

Live API 3 menu discovery and dispatch are covered by the r15 integration
tests. These fixtures deliberately represent historical API 1 packages;
they must remain absent from the menu even when supplied by a caller.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hpc_gui.plugins import models
from hpc_gui.plugins.trusted_tools import APPROVED_TRUSTED_TOOLS, trusted_tool_error
from hpc_gui.services import file_context_actions as fca
from hpc_gui.wx_local_files_interactions import (
    _openfoam_plugins as local_plugins,
    local_menu_actions,
    run_openfoam_file_context_action as local_run_of,
)
from hpc_gui.wx_remote_files_actions import install_actions
from hpc_gui.wx_local_files_mutations import install_mutations
from hpc_gui.wx_remote_files_interactions import (
    REMOTE_CANDIDATE_ACTIONS,
    _openfoam_plugins as remote_plugins,
    remote_menu_actions,
    run_openfoam_file_context_action as remote_run_of,
)


def _studio_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=1, id="openfoam-case-studio",
        name="OpenFOAM Case Studio", version="0.3.0-w65r17-auditfix1",
        publisher="HPC Client GUI", license="test", description="test",
        requires_app=">=1.5.9", capabilities=("application-tools",),
        entrypoints={}, files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def _linter_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=1, id="openfoam-linter",
        name="OpenFOAM Linter", version="0.2.0-w65r17-auditfix1",
        publisher="HPC Client GUI", license="test", description="test",
        requires_app=">=1.5.9", capabilities=("lint-rules", "linter-tool"),
        entrypoints={}, files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def _evil_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=1, id="openfoam-case-studio",
        name="x", version="0.3.0-w65r17-auditfix1", publisher="Evil Corp",
        license="test", description="test", requires_app=">=1.5.9",
        capabilities=("application-tools",), entrypoints={}, files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def _one_dir():
    return fca.context_selection("cavity", True, ("cavity",), (True,))


def _one_file():
    return fca.context_selection("case.foam", False, ("case.foam",), (False,))


# --- legacy API 1 packages cannot authorize OpenFOAM actions --------------

def test_local_menu_unchanged_when_not_ready():
    for selection in (_one_dir(), _one_file()):
        base = fca.visible_actions(selection, remote=False)
        assert local_menu_actions(selection, [_studio_plugin()]) == base
        assert local_menu_actions(selection, [_linter_plugin()], upload=False) == (
            tuple(a for a in base if a != "upload"))
        assert not any(a.startswith("of.") for a in local_menu_actions(selection, []))


def test_remote_menu_unchanged_when_not_ready():
    for selection in (_one_dir(), _one_file()):
        allowed = set(fca.visible_actions(selection, remote=True))
        legacy = tuple(a for a in REMOTE_CANDIDATE_ACTIONS if a in allowed)
        assert remote_menu_actions(selection, [_studio_plugin()]) == legacy
        assert remote_menu_actions(selection, [_linter_plugin()]) == legacy
        assert not any(a.startswith("of.") for a in remote_menu_actions(selection, []))


# --- discovery always uses the host's normal plugin loader ----------------

def test_plugin_discovery_ignores_view_supplied_objects(monkeypatch):
    import hpc_gui.wx_local_files_interactions as local_view
    import hpc_gui.wx_remote_files_interactions as remote_view

    monkeypatch.setattr(local_view, "installed_openfoam_file_context_plugins", lambda: ())
    monkeypatch.setattr(remote_view, "installed_openfoam_file_context_plugins", lambda: ())
    supplied = SimpleNamespace(openfoam_file_context_plugins=[_studio_plugin()])
    assert local_plugins(supplied) == ()
    assert remote_plugins(supplied) == ()


# --- legacy packages cannot cross the API 3 trust boundary ----------------

def test_of_dispatch_rejects_legacy_packages():
    studio, linter = _studio_plugin(), _linter_plugin()
    pairs = [("of.newCase", studio), ("of.openStudio", studio),
             ("of.createJob", studio), ("of.validate", linter)]
    for runner in (local_run_of, remote_run_of):
        for action, plugin in pairs:
            ok, reason = runner(action, _one_dir(), [plugin])
            assert ok is False and "approved owner" in reason
        ok, reason = runner("of.bogus", _one_dir(), [studio])
        assert ok is False and "unknown" in reason


def test_of_dispatch_rejects_wrong_owner_and_unsupported_path():
    studio, linter = _studio_plugin(), _linter_plugin()
    for runner in (local_run_of, remote_run_of):
        ok, reason = runner("of.validate", _one_dir(), [studio])
        assert ok is False and "approved owner" in reason
        ok, reason = runner("of.openStudio", _one_dir(), [linter])
        assert ok is False and "approved owner" in reason
        ok, reason = runner("of.openStudio", _one_dir(), [])
        assert ok is False and "approved owner" in reason

# --- real run_action owners never execute of.* ---------------------------

def _local_mutation_view(calls: list):
    def _refresh(selection_after=()):
        calls.append(("refresh", tuple(selection_after)))

    return SimpleNamespace(
        active_tab_state=lambda: {"path": "/tmp", "entries": []},
        confirm_local_delete=lambda names, location: True,
        create_tab=lambda path: {"panel": object(), "listing": object()},
        host=SimpleNamespace(), model=SimpleNamespace(
            clipboard=[], new_tab=lambda p: calls.append(("new_tab", p))),
        navigate=lambda target: calls.append(("navigate", target)),
        notebook=SimpleNamespace(), open_editor=None,
        open_editor_new_window=None, path_ctrl=SimpleNamespace(),
        refresh=_refresh, render_entries=lambda *a: None, run_shell=None,
        safe_call_after=lambda cb, *a: None, selected_entries=lambda: [],
        state={"context_target": None}, tab_label=lambda p: str(p),
        tabs=[], threading_lock=SimpleNamespace(), upload=None,
        wx=SimpleNamespace(),
    )


def test_local_mutations_ignore_of_actions():
    view = _local_mutation_view(calls := [])
    install_mutations(view)
    for action in fca.OPENFOAM_FILE_CONTEXT_IDS:
        assert view.run_action(action) is None
    assert calls == []
    view.run_action("refresh")
    assert calls == [("refresh", ())]


def _remote_action_view(calls: list):
    return SimpleNamespace(
        _current_navigation_store=lambda: None,
        _show_follow_menu=lambda target: calls.append(("follow", target)),
        active_tab_state=lambda: {"path": "/tmp", "entries": []},
        chmod=None, create_tab=lambda path: {"panel": object()},
        host=SimpleNamespace(), load=lambda: calls.append(("load",)),
        lock=SimpleNamespace(), model=SimpleNamespace(),
        move_history=SimpleNamespace(pop_last=lambda: None),
        navigate=lambda target: calls.append(("navigate", target)),
        notebook=SimpleNamespace(), open_editor=None,
        open_editor_new_window=None, open_in_editor=None, operation=None,
        path=SimpleNamespace(),
        run_direct_operation=lambda op: calls.append(("direct",)),
        run_operation=lambda *a: calls.append(("run_operation", a)),
        run_shell=None, safe_call_after=lambda cb, *a: None,
        state={}, submit_slurm=None, tab_label=lambda p: str(p),
        wx=SimpleNamespace(),
    )


def test_remote_actions_never_route_of_to_run_operation():
    view = _remote_action_view(calls := [])
    install_actions(view)
    for action in fca.OPENFOAM_FILE_CONTEXT_IDS:
        assert view.run_action(action, ("case.foam",), "/tmp") is None
    assert calls == []
    assert not any(kind == "run_operation" for kind, *_ in calls)
    view.run_action("refresh", ("case.foam",), "/tmp")
    assert calls == [("load",)]


# --- r12 protections preserved: no broadening, labels paired ------------

def test_trust_policy_not_broadened():
    assert set(APPROVED_TRUSTED_TOOLS) == {
        "org.hpcclient.ansyslint", "openfoam-linter"}
    assert trusted_tool_error({
        "plugin_api": 2, "id": "openfoam-linter-evil",
        "publisher": "HPC Client GUI", "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/openfoam_lint/__init__.py"},
    })


def test_of_label_keys_still_resolve():
    import json

    repo = Path(__file__).resolve().parents[1]
    en = json.loads((repo / "src" / "hpc_gui" / "i18n" / "en.json").read_text(
        encoding="utf-8"))["openfoam"]
    tr = json.loads((repo / "src" / "hpc_gui" / "i18n" / "tr.json").read_text(
        encoding="utf-8"))["openfoam"]
    assert set(en) == set(tr)
    for action in fca.OPENFOAM_FILE_CONTEXT_IDS:
        assert fca.FILE_CONTEXT_LABEL_KEYS[action].startswith("openfoam.")
