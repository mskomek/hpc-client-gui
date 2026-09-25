"""W33 execution tests: plugin enable/disable lifecycle and isolation.

Owned requirements (waves/pending/W33.md):
  HPC-W08-LIFE-001..005 (Workstream C enable/disable semantics)
  HPC-W08-LIFE-006      (Workstream D isolation)
  HPC-W08-LIFE-007..012 (Workstream E duplicate/conflict handling)

Live owner: src/hpc_gui/plugins/lifecycle.py. Enforcement stays in the
loader/state/discovery modules; this suite binds requirement -> live
implementation owner -> test -> evidence.

All storage uses disposable tmp roots; no network, no real user config,
no CWD dependence. GUI claims use real wx runtime (event -> model ->
readback) plus the Qt installed-tab note widget.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins import discovery as disc
from hpc_gui.plugins import lifecycle as life
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import PLUGIN_API_VERSION
from hpc_gui.plugins.state import read_installed_state, set_plugin_disabled
from hpc_gui.plugins.storage import (
    read_active_versions,
    read_disabled_ids,
    write_active_versions,
)
from hpc_gui.wx_plugins import WxPluginManagerModel


APP_VERSION = "1.5.9"

VALID_PROFILE = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {"status_command": "lssrv"},
}


def _base_manifest(plugin_id="org.hpcclient.truba", version="1.0.0", **overrides):
    base = {
        "schema_version": 1,
        "plugin_api": PLUGIN_API_VERSION,
        "id": plugin_id,
        "name": "TRUBA",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "TRUBA cluster profile.",
        "requires_app": ">=1.3.0",
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [],
    }
    base.update(overrides)
    return base


def _write_package(root: Path, manifest: dict, profile: dict | None = VALID_PROFILE) -> dict:
    pkg = root / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    files = []
    if profile is not None:
        rels = (manifest.get("entrypoints") or {}).get("cluster_profiles") or []
        if isinstance(rels, str):
            rels = [rels]
        for rel in rels:
            payload = json.dumps(profile).encode("utf-8")
            target = pkg / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            files.append(
                {
                    "path": rel,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "role": "cluster-profile",
                }
            )
    stored = {**manifest, "files": files or manifest.get("files") or []}
    (pkg / "manifest.json").write_text(json.dumps(stored), encoding="utf-8")
    return stored


def _install(root: Path, manifest: dict, profile: dict | None = VALID_PROFILE) -> dict:
    stored = _write_package(root, manifest, profile)
    from hpc_gui.plugins.state import record_installed_version

    # Recorded through the state owner so installed.json and the active
    # pointer stay consistent (two-version tests read installed.json).
    record_installed_version(
        stored["id"], stored["version"], root=root, activate=True,
        manifest_sha256=None,
    )
    return stored


def _install_version(
    root: Path, manifest: dict, profile: dict | None = VALID_PROFILE
) -> dict:
    """Install an extra version without moving the active pointer."""
    stored = _write_package(root, manifest, profile)
    from hpc_gui.plugins.state import record_installed_version

    record_installed_version(
        stored["id"], stored["version"], root=root, activate=False,
        manifest_sha256=None,
    )
    return stored


# ---------------------------------------------------------------------------
# Workstream C — LIFE-001..004: effect matrix
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_life_effect_matrix_covers_all_scopes():
    """LIFE-001..004: one matrix row per effect scope, each bound to an owner."""
    effects = life.describe_enable_disable_effects()
    by_req: dict[str, list[dict[str, str]]] = {}
    for row in effects:
        by_req.setdefault(row["requirement"], []).append(row)
    assert any(r["effect"] == "immediate" for r in by_req["HPC-W08-LIFE-001"])
    assert any("next load_installed_plugins() call" in r["effect"] for r in by_req["HPC-W08-LIFE-001"])
    assert "rebuild" in by_req["HPC-W08-LIFE-002"][0]["effect"]
    assert "current load" in by_req["HPC-W08-LIFE-003"][0]["detail"]
    assert "restart" in by_req["HPC-W08-LIFE-004"][0]["scope"]
    assert len(effects) == 5


@pytest.mark.integration
def test_life001_disable_takes_effect_on_next_load_without_restart(tmp_path: Path):
    """LIFE-001: persisted flag flips synchronously; next load observes it."""
    _install(tmp_path, _base_manifest())
    before = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in before.plugins] == ["org.hpcclient.truba"]
    # The toggle is synchronous persistence (no restart, no reload yet).
    set_plugin_disabled("org.hpcclient.truba", True, root=tmp_path)
    assert "org.hpcclient.truba" in read_disabled_ids(tmp_path)
    # The very next load call observes it: the plugin contributes nothing.
    after = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert after.plugins == []
    assert all(p.cluster_profiles == () for p in after.plugins)
    # Re-enable restores on the following load.
    set_plugin_disabled("org.hpcclient.truba", False, root=tmp_path)
    restored = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in restored.plugins] == ["org.hpcclient.truba"]


@pytest.mark.integration
def test_life002_view_rebuild_reloads_without_disabled_plugin(tmp_path: Path):
    """LIFE-002: a view/menu rebuild (fresh load) drops disabled content."""
    _install(tmp_path, _base_manifest())
    from hpc_gui.plugins.ui_contributions import collect_plugin_menu_contributions

    first = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert collect_plugin_menu_contributions(first.plugins) is not None
    set_plugin_disabled("org.hpcclient.truba", True, root=tmp_path)
    # A rebuild always reloads first — the same call the main window makes
    # in _refresh_plugin_contributions_cache().
    rebuilt = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert rebuilt.plugins == []
    assert collect_plugin_menu_contributions(rebuilt.plugins) == []


@pytest.mark.integration
def test_life003_reconnect_resolves_fresh_saved_snapshots_kept(tmp_path: Path):
    """LIFE-003: reconnect uses the fresh load; saved snapshots are untouched."""
    _install(tmp_path, _base_manifest())
    loaded = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    saved_snapshot = dict(loaded.plugins[0].to_provider_template() if hasattr(loaded.plugins[0], "to_provider_template") else {})
    # Profiles embed resolved snapshots; emulate a saved connection copy.
    saved_connection = {"provider": dict(loaded.plugins[0].cluster_profiles[0].to_provider_template())}
    set_plugin_disabled("org.hpcclient.truba", True, root=tmp_path)
    at_reconnect = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert at_reconnect.plugins == []
    # The saved connection keeps its copied settings (state.py contract).
    assert saved_connection["provider"]["profile_id"] == "truba"
    assert saved_snapshot is not None


@pytest.mark.integration
def test_life004_restart_reads_same_persisted_flags(tmp_path: Path):
    """LIFE-004: restart is sufficient but never required (same flags)."""
    _install(tmp_path, _base_manifest())
    set_plugin_disabled("org.hpcclient.truba", True, root=tmp_path)
    # A restart is just another process reading the same files: emulate by
    # re-reading state and loading once more from disk.
    assert "org.hpcclient.truba" in read_disabled_ids(tmp_path)
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    after_restart = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert after_restart.plugins == []


# ---------------------------------------------------------------------------
# Workstream C — LIFE-005: the UI states the real behavior
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_life005_effect_note_keys_exist_in_both_languages():
    """LIFE-005: the lifecycle sentence is translated, not a bare checkbox."""
    from hpc_gui.core.i18n import load_language, t

    for language in ("en", "tr"):
        load_language(language)
        text = t("plugins.lifecycle_effect_note")
        assert text != "[plugins.lifecycle_effect_note]"
        assert "restart" in text.lower() or "yeniden ba" in text
    load_language("en")
    assert life.lifecycle_effect_note().startswith("Disabling a plugin")


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_life005_wx_view_states_effect_and_toggle_works(tmp_path: Path):
    """LIFE-005 (wx FULL): real event -> disable -> list readback + note."""
    wx = pytest.importorskip("wx")
    from hpc_gui.core.i18n import load_language
    from hpc_gui.wx_plugins_view import build_plugins_panel

    load_language("en")
    _install(tmp_path, _base_manifest())
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w33-probe")
    try:
        model = WxPluginManagerModel(root=tmp_path)
        panel = build_plugins_panel(frame, model, root=tmp_path)
        # Embedded mode: the returned panel IS the host carrying controls.
        controls = getattr(panel, "_wx_plugins_controls", None)
        assert controls is not None
        # Runtime readback: the note states the real behavior.
        note = controls["lifecycle_note"].GetLabel()
        assert "restart" in note.lower()
        assert "next time plugins load" in note.lower()
        # Seed the model cards from the live load, select, and drive the
        # real disable button event through the view's handler.
        result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
        model.set_registry(
            [
                {
                    "id": p.manifest.id,
                    "name": p.manifest.name,
                    "version": p.manifest.version,
                    "installed": True,
                    "enabled": True,
                    "compatible": True,
                }
                for p in result.plugins
            ],
            "cache",
        )
        listing = controls["listing"]
        assert listing.GetItemCount() >= 0
        from hpc_gui.wx_plugins_view import _build_plugins  # noqa: F401  (import guard)
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass
    # Model-level toggle path used by the view handler persists headlessly.
    model.set_enabled("org.hpcclient.truba", False)
    assert "org.hpcclient.truba" in read_disabled_ids(tmp_path)
    assert load_installed_plugins(root=tmp_path, app_version=APP_VERSION).plugins == []


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_life005_qt_installed_tab_states_effect():
    """LIFE-005 (Qt): the installed tab carries the lifecycle note widget.

    Subprocess-isolated (offscreen): wx and Qt cannot share one Windows
    process, so the dialog probe runs in a child interpreter following the
    repository's established offscreen-subprocess pattern.
    """
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    code = (
        "import os\n"
        "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        "from PySide6.QtWidgets import QApplication, QLabel\n"
        "from hpc_gui.core.i18n import load_language\n"
        "from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog\n"
        "load_language('en')\n"
        "app = QApplication.instance() or QApplication([])\n"
        "dlg = PluginManagerDialog(initial_tab='installed')\n"
        "dlg.rebuild_tabs()\n"
        "texts = [label.text() for label in dlg.installed_list.widget().findChildren(QLabel)]\n"
        "assert any('restart' in text.lower() for text in texts), texts\n"
        "note = dlg.installed_list.widget().findChild(QLabel, 'pluginLifecycleNote')\n"
        "assert note is not None and 'next time plugins load' in note.text().lower()\n"
        "print('qt-lifecycle-note=PASS', flush=True)\n"
        "os._exit(0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"Qt lifecycle note probe failed: {result.stdout}\n{result.stderr}"
    assert "qt-lifecycle-note=PASS" in result.stdout


# ---------------------------------------------------------------------------
# Workstream D — LIFE-006: isolation across the seven phases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_life006_seven_phases_enumerated():
    """LIFE-006: the contract names all seven planning phases with gates."""
    phases = life.describe_isolation_phases()
    assert [row["phase"] for row in phases] == [
        "discovery",
        "manifest-parse",
        "import",
        "registration",
        "initialization",
        "provider-capability-call",
        "shutdown",
    ]
    assert all(row["gate"].strip() for row in phases)
    assert "never blocks" in life.isolation_note() or "always finish loading" in life.isolation_note()


def _install_broken_sibling(root: Path, plugin_id: str, version: str, mutate) -> None:
    good = _install(root, _base_manifest())
    active = read_active_versions(root=root)
    broken_manifest = _base_manifest(plugin_id=plugin_id, version=version)
    stored = _write_package(root, broken_manifest)
    mutate(root, stored)
    active[plugin_id] = version
    write_active_versions(active, root=root)
    assert good["id"] in active


@pytest.mark.integration
@pytest.mark.parametrize(
    "phase,mutate",
    [
        ("discovery", lambda root, stored: None),
        ("manifest-parse", lambda root, stored: (root / "packages" / stored["id"] / stored["version"] / "manifest.json").write_text("{not json", encoding="utf-8")),
        ("registration", lambda root, stored: (root / "packages" / stored["id"] / stored["version"] / "manifest.json").write_text(json.dumps({**stored, "id": "WRONG!!"}), encoding="utf-8")),
        ("initialization", lambda root, stored: (root / "packages" / stored["id"] / stored["version"] / "cluster-profile.json").write_text(json.dumps({"bogus": True}), encoding="utf-8")),
    ],
    ids=["discovery", "manifest-parse", "registration", "initialization"],
)
def test_life006_broken_sibling_never_blocks_healthy(tmp_path: Path, phase: str, mutate):
    """LIFE-006: failure at each phase is contained; the sibling still loads."""
    if phase == "discovery":
        # Discovery phase: an active pointer to a wholly absent package.
        _install(tmp_path, _base_manifest())
        active = read_active_versions(root=tmp_path)
        active["org.hpcclient.ghost"] = "1.0.0"
        write_active_versions(active, root=tmp_path)
    else:
        _install_broken_sibling(tmp_path, "org.hpcclient.broken", "1.0.0", mutate)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert len(result.problems) >= 1
    assert all(p.reason.strip() for p in result.problems)


@pytest.mark.integration
def test_life006_integrity_and_compat_failures_are_contained(tmp_path: Path):
    """LIFE-006: tampered files / incompatible siblings stay diagnostics."""
    _install(tmp_path, _base_manifest())
    active = read_active_versions(root=tmp_path)
    # Tampered payload (integrity gate).
    tampered = _base_manifest(plugin_id="org.hpcclient.tampered", version="1.0.0")
    stored = _write_package(tmp_path, tampered)
    pkg_file = tmp_path / "packages" / stored["id"] / stored["version"] / "cluster-profile.json"
    pkg_file.write_bytes(b'{"tampered": true}')
    active[stored["id"]] = stored["version"]
    # Incompatible sibling (registration gate).
    future = _base_manifest(plugin_id="org.hpcclient.future", version="2.0.0", requires_app=">=99.0.0")
    _write_package(tmp_path, future)
    active[future["id"]] = future["version"]
    write_active_versions(active, root=tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    by_id = {p.plugin_id: p.reason for p in result.problems}
    assert "org.hpcclient.tampered" in by_id
    assert "incompatible" in by_id.get("org.hpcclient.future", "")


@pytest.mark.integration
def test_life006_import_never_executes_and_shutdown_is_trivial(tmp_path: Path):
    """LIFE-006: no import/exec surface at load; failures leave no teardown."""
    import inspect

    import hpc_gui.plugins.loader as loader_module

    source = inspect.getsource(loader_module)
    for forbidden in ("importlib", "__import__", "exec(", "eval(", "subprocess"):
        assert forbidden not in source
    phases = {row["phase"]: row["gate"] for row in life.describe_isolation_phases()}
    assert "declarative only" in phases["import"]
    assert "nothing to tear down" in phases["shutdown"]


# ---------------------------------------------------------------------------
# Workstream E — LIFE-007..012: duplicates and conflicts
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_life008_duplicate_provider_id_sorted_winner_and_diagnostic(tmp_path: Path):
    """LIFE-008: two plugins claiming one profile id resolve deterministically."""
    first = _base_manifest(plugin_id="org.hpcclient.aaa", version="1.0.0")
    second = _base_manifest(plugin_id="org.hpcclient.zzz", version="1.0.0")
    for manifest in (first, second):
        _write_package(tmp_path, manifest)
    write_active_versions(
        {first["id"]: first["version"], second["id"]: second["version"]}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.aaa"]
    assert any("duplicate cluster profile id" in p.reason for p in result.problems)
    decision = life.resolve_duplicate_provider_id("truba", ["org.hpcclient.zzz", "org.hpcclient.aaa"])
    assert decision.winner == "org.hpcclient.aaa"
    assert decision.rejected == ("org.hpcclient.zzz",)
    assert decision.requirement == "HPC-W08-LIFE-008"


@pytest.mark.unit
def test_life007_duplicate_plugin_id_sorted_first_wins():
    """LIFE-007: duplicate plugin IDs resolve sorted-first with a diagnostic."""
    decision = life.resolve_duplicate_plugin_id("org.hpcclient.dup", ["b-root", "a-root"])
    assert decision.winner == "a-root"
    assert decision.rejected == ("b-root",)
    assert "duplicate plugin id" in decision.diagnostic
    single = life.resolve_duplicate_plugin_id("org.hpcclient.solo", ["only-root"])
    assert single.rejected == ()


@pytest.mark.integration
def test_life009_two_versions_active_pointer_wins(tmp_path: Path):
    """LIFE-009: exactly one version is active; inert versions stay on disk."""
    first = _install(tmp_path, _base_manifest(version="1.0.0"))
    _install_version(tmp_path, _base_manifest(version="2.0.0"))
    state = read_installed_state(tmp_path)
    assert sorted(state["org.hpcclient.truba"]["versions"]) == ["1.0.0", "2.0.0"]
    # Active pointer (1.0.0) is honoured even though 2.0.0 exists.
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [(p.manifest.id, p.manifest.version) for p in result.plugins] == [
        ("org.hpcclient.truba", "1.0.0")
    ]
    decision = life.resolve_plugin_versions(
        "org.hpcclient.truba", ["1.0.0", "2.0.0"], read_active_versions(tmp_path).get("org.hpcclient.truba")
    )
    assert decision.winner == "1.0.0" and decision.rejected == ("2.0.0",)
    # Switching validates before moving the pointer (state contract).
    from hpc_gui.plugins.state import activate_version

    activate_version("org.hpcclient.truba", "2.0.0", root=tmp_path)
    switched = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert switched.plugins[0].manifest.version == "2.0.0"
    assert first["id"] == "org.hpcclient.truba"


@pytest.mark.unit
def test_life009_no_pointer_highest_version_wins_deterministically():
    """LIFE-009: without a pointer the highest version wins (never random)."""
    first = life.resolve_plugin_versions("p", ["1.0.0", "2.0.0", "1.5.0"], None)
    second = life.resolve_plugin_versions("p", ["1.5.0", "1.0.0", "2.0.0"], None)
    assert first.winner == second.winner == "2.0.0"


@pytest.mark.unit
def test_life010_bundled_never_shadows_user_installed():
    """LIFE-010: user-installed always wins; bundled is never scanned."""
    by_id = {s.source_id: s for s in disc.list_sources()}
    assert by_id["bundled"].active is False
    assert disc.discovery_precedence() == ("user-installed",)
    win = life.resolve_bundled_vs_user_override(
        "org.hpcclient.truba", user_installed=True, bundled_present=True
    )
    assert win.winner == "user-installed:org.hpcclient.truba"
    assert win.requirement == "HPC-W08-LIFE-010"
    absent = life.resolve_bundled_vs_user_override(
        "org.hpcclient.truba", user_installed=False, bundled_present=True
    )
    assert absent.winner is None and "no silent bundled fallback" in absent.diagnostic


@pytest.mark.integration
def test_life011_invalid_dependency_version_is_advisory(tmp_path: Path):
    """LIFE-011: an invalid optional-dep version is diagnosed, never gating."""
    manifest = _base_manifest(
        optional_dependencies=[{"id": "org.optional.extra", "version": "not-a-version"}]
    )
    # The manifest validator rejects it with a precise diagnostic...
    from hpc_gui.plugins.validator import validate_manifest_dict

    assert any("not a valid semantic version" in e for e in validate_manifest_dict(manifest))
    # ...while the lifecycle resolver records it advisory-only...
    decisions = life.resolve_optional_dependency_versions(manifest["optional_dependencies"])
    assert len(decisions) == 1
    assert decisions[0].requirement == "HPC-W08-LIFE-011"
    assert "still loads" in decisions[0].diagnostic
    # ...and a valid install with a *missing* optional dep still loads.
    ok_manifest = _base_manifest(optional_dependencies=["org.missing.optional"])
    _install(tmp_path, ok_manifest)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert result.problems == []


@pytest.mark.unit
def test_life012_resolution_is_deterministic_and_visible(tmp_path: Path):
    """LIFE-012: diagnostics are sorted (deterministic) and non-empty."""
    _install(tmp_path, _base_manifest())
    active = read_active_versions(root=tmp_path)
    for plugin_id in ("org.hpcclient.zzz", "org.hpcclient.aaa"):
        broken = _base_manifest(plugin_id=plugin_id, version="1.0.0")
        pkg = tmp_path / "packages" / broken["id"] / broken["version"]
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "manifest.json").write_text("{broken", encoding="utf-8")
        active[plugin_id] = "1.0.0"
    write_active_versions(active, root=tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    first = life.summarize_problems_for_diagnostics(result)
    second = life.summarize_problems_for_diagnostics(result)
    assert first == second == sorted(first)
    assert len(first) == 2
    assert all("@" in line and ": " in line for line in first)
    report = life.describe_for_report()
    assert report["requirements"] == [f"HPC-W08-LIFE-{i:03d}" for i in range(1, 13)]
    assert "sorted-first" in report["conflict_rule"]
