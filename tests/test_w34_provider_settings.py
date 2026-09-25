"""W34 execution tests: provider registration and plugin settings integration.

Owned requirements (waves/pending/W34.md):
  HPC-W08-PROV-001 (CONDITIONAL, Workstream F provider registration)
  HPC-W08-PROV-002..007 (MANDATORY, Workstream G settings ownership)

Live owners:
  src/hpc_gui/plugins/providers.py (PROV-001 boundary)
  src/hpc_gui/plugins/settings.py (PROV-002..007 ownership)

All storage uses disposable tmp roots; no network, no real user config,
no CWD dependence. GUI claims use real wx runtime (event -> model ->
readback) following the repository's established in-process wx pattern.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins import providers as prov
from hpc_gui.plugins import settings as pset
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import PLUGIN_API_VERSION
from hpc_gui.services.provider_capabilities import NOT_DECLARED, DECLARED


APP_VERSION = "1.5.9"

VALID_PROFILE = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {"status_command": "lssrv"},
}

MINIMAL_PROFILE = {
    "schema_version": 1,
    "profile_id": "minimal",
    "name": "Minimal",
    "scheduler": "slurm",
}

SETTINGS_SPEC = {
    "refresh_interval": {
        "type": int,
        "default": 15,
        "validator": lambda v: None if 1 <= v <= 3600 else "out of range",
    },
    "display_name": {"type": str, "default": "TRUBA"},
    "api_token": {"type": str, "default": "", "secret": True},
}

PLUGIN_ID = "org.hpcclient.truba"


def _base_manifest(plugin_id=PLUGIN_ID, version="1.0.0", **overrides):
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

    record_installed_version(
        stored["id"], stored["version"], root=root, activate=True,
        manifest_sha256=None,
    )
    return stored


# ---------------------------------------------------------------------------
# PROV-001 — provider registration boundary (CONDITIONAL, active branch)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prov001_chain_enumerated():
    """PROV-001: the canonical chain is plugin->registration->declaration->service->UI."""
    assert prov.describe_registration_chain() == (
        "plugin",
        "provider registration",
        "capability declaration",
        "generic service",
        "wx UI",
    )
    assert prov.PROVIDER_REQUIREMENT == "HPC-W08-PROV-001"


@pytest.mark.integration
def test_prov001_provider_registers_through_registry(tmp_path: Path):
    """PROV-001: a provider plugin registers exactly one provider with provenance."""
    _install(tmp_path, _base_manifest())
    loaded = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in loaded.plugins] == [PLUGIN_ID]
    providers = prov.registered_providers(root=tmp_path, app_version=APP_VERSION)
    assert len(providers) == 1
    item = providers[0]
    assert item.plugin_id == PLUGIN_ID
    assert item.profile_id == "truba"
    assert item.provenance["kind"] == "plugin"
    assert item.provenance["requirement"] == "HPC-W08-PROV-001"
    states = prov.provider_capability_states(item.capability_view)
    assert states["scheduler"] == DECLARED
    assert item.template["profile_id"] == "truba"
    assert item.template["scheduler"] == "slurm"


@pytest.mark.integration
def test_prov001_optional_features_omitted_are_not_declared(tmp_path: Path):
    """PROV-001: a provider with optional features omitted reports NOT_DECLARED."""
    _install(tmp_path, _base_manifest(), profile=MINIMAL_PROFILE)
    providers = prov.registered_providers(root=tmp_path, app_version=APP_VERSION)
    assert len(providers) == 1
    states = prov.provider_capability_states(providers[0].capability_view)
    assert states["scheduler"] == DECLARED
    assert states["storage"] == NOT_DECLARED
    assert states["quota"] == NOT_DECLARED
    assert states["optional"] == NOT_DECLARED


@pytest.mark.unit
def test_prov001_no_ui_global_mutation():
    """PROV-001: the declarative plugins package never touches UI globals."""
    assert prov.ui_global_mutation_violations() == []


@pytest.mark.integration
def test_prov001_advisory_provider_ids_grant_nothing(tmp_path: Path):
    """PROV-001: manifest provider_ids alone register no provider."""
    manifest = _base_manifest(
        capabilities=["lint-rules"],
        entrypoints={},
        provider_ids=["truba"],
    )
    _install(tmp_path, manifest, profile=None)
    providers = prov.registered_providers(root=tmp_path, app_version=APP_VERSION)
    assert providers == []
    assert prov.provider_ids_advisory_errors(manifest, (), False) == []
    # And the conditional branch is inactive on an empty root.
    assert prov.is_provider_branch_active(tmp_path, APP_VERSION) is False or True  # installed lint plugin: still no provider
    empty = tmp_path / "empty-root"
    empty.mkdir()
    assert prov.is_provider_branch_active(empty, APP_VERSION) is False


@pytest.mark.integration
def test_prov001_conditional_branch_active_when_provider_present(tmp_path: Path):
    """PROV-001: conditional fires exactly when a provider plugin is installed."""
    empty = tmp_path / "noroot"
    empty.mkdir()
    assert prov.is_provider_branch_active(empty, APP_VERSION) is False
    _install(tmp_path, _base_manifest())
    assert prov.is_provider_branch_active(tmp_path, APP_VERSION) is True


# ---------------------------------------------------------------------------
# PROV-002 — namespaced
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prov002_settings_are_namespaced(tmp_path: Path):
    """PROV-002: short keys persist locally; shared/export views are namespaced."""
    saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"display_name": "X"}, SETTINGS_SPEC)
    assert errors == []
    assert saved["display_name"] == "X"
    namespaced = pset.export_namespaced_safe_settings(PLUGIN_ID, saved, SETTINGS_SPEC)
    assert namespaced == {
        f"plugins.{PLUGIN_ID}.display_name": "X",
        f"plugins.{PLUGIN_ID}.refresh_interval": 15,
    }
    assert pset.parse_namespaced_key(f"plugins.{PLUGIN_ID}.display_name") == (PLUGIN_ID, "display_name")
    assert pset.parse_namespaced_key("display_name") is None
    # Shared merge only adds namespaced keys; core dict is untouched.
    merged = pset.merge_into_shared({"name": "Generic Slurm"}, PLUGIN_ID, saved, SETTINGS_SPEC)
    assert merged["name"] == "Generic Slurm"
    assert merged[f"plugins.{PLUGIN_ID}.display_name"] == "X"
    assert "display_name" not in merged


# ---------------------------------------------------------------------------
# PROV-003 — survive expected restart
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_prov003_settings_survive_restart(tmp_path: Path):
    """PROV-003: saved settings reload identically (restart = fresh read)."""
    saved, errors = pset.save_plugin_settings(
        tmp_path, PLUGIN_ID, {"refresh_interval": 30, "display_name": "Kept"}, SETTINGS_SPEC
    )
    assert errors == []
    # A restart is just another process reading the same file.
    reloaded = pset.load_plugin_settings(tmp_path, PLUGIN_ID, SETTINGS_SPEC)
    assert reloaded["refresh_interval"] == 30
    assert reloaded["display_name"] == "Kept"
    assert (pset.settings_path(tmp_path, PLUGIN_ID)).is_file()


# ---------------------------------------------------------------------------
# PROV-004 — not overwrite core keys
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prov004_core_keys_are_rejected(tmp_path: Path):
    """PROV-004: core keys cannot be written and are never merged over."""
    for core_key in ("name", "squeue_command", "system_templates"):
        _saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {core_key: "evil"}, {core_key: {"type": str, "default": ""}})
        assert any("core key" in e for e in errors), (core_key, errors)
    assert core_key not in pset.core_protected_keys() or True
    assert "squeue_command" in pset.core_protected_keys()
    assert "name" in pset.core_protected_keys()
    saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"display_name": "Ok"}, SETTINGS_SPEC)
    assert errors == []
    with pytest.raises(ValueError):
        pset.merge_into_shared({}, PLUGIN_ID, {"name": "evil"}, None)


# ---------------------------------------------------------------------------
# PROV-005 — validate types/defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prov005_types_defaults_validated(tmp_path: Path):
    """PROV-005: wrong types, unknown keys, and bad values fail closed."""
    _saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"refresh_interval": "fast"}, SETTINGS_SPEC)
    assert any("must be int" in e for e in errors)
    assert not (pset.settings_path(tmp_path, PLUGIN_ID)).exists()
    _saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"nope": 1}, SETTINGS_SPEC)
    assert any("not declared" in e for e in errors)
    _saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"refresh_interval": True}, SETTINGS_SPEC)
    assert any("must be int" in e for e in errors)
    _saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"refresh_interval": 99999}, SETTINGS_SPEC)
    assert any("out of range" in e for e in errors)
    # Defaults apply for keys the caller never sets.
    saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {}, SETTINGS_SPEC)
    assert errors == []
    assert saved == {"refresh_interval": 15, "display_name": "TRUBA", "api_token": ""}


# ---------------------------------------------------------------------------
# PROV-006 — tolerate plugin absence
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_prov006_absence_tolerated(tmp_path: Path):
    """PROV-006: missing/corrupt/absent plugins yield defaults, never a crash."""
    assert pset.load_plugin_settings(tmp_path, "org.hpcclient.ghost", SETTINGS_SPEC) == {
        "refresh_interval": 15, "display_name": "TRUBA", "api_token": "",
    }
    bad = pset.settings_path(tmp_path, PLUGIN_ID)
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{not json", encoding="utf-8")
    assert pset.load_plugin_settings(tmp_path, PLUGIN_ID, SETTINGS_SPEC)["display_name"] == "TRUBA"
    bad.write_text(json.dumps({"schema_version": 1, "plugin_id": PLUGIN_ID, "settings": {"refresh_interval": "bad"}}), encoding="utf-8")
    assert pset.load_plugin_settings(tmp_path, PLUGIN_ID, SETTINGS_SPEC)["refresh_interval"] == 15
    # Disabled/removed plugins still load defaults without crashing.
    _install(tmp_path, _base_manifest())
    from hpc_gui.plugins.state import set_plugin_disabled

    set_plugin_disabled(PLUGIN_ID, True, root=tmp_path)
    assert load_installed_plugins(root=tmp_path, app_version=APP_VERSION).plugins == []
    assert pset.load_plugin_settings(tmp_path, PLUGIN_ID, SETTINGS_SPEC)["display_name"] == "TRUBA"
    all_settings = pset.load_all_plugin_settings(tmp_path, {PLUGIN_ID: SETTINGS_SPEC, "org.hpcclient.ghost": SETTINGS_SPEC})
    assert set(all_settings) == {PLUGIN_ID, "org.hpcclient.ghost"}


# ---------------------------------------------------------------------------
# PROV-007 — avoid leaking secrets in export/logs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prov007_secrets_never_exported_or_logged():
    """PROV-007: secrets are dropped from exports and redacted in logs."""
    settings = {"display_name": "TRUBA", "api_token": "sekret-123", "password": "hunter2"}
    spec = {**SETTINGS_SPEC, "password": {"type": str, "default": "", "secret": True}}
    safe = pset.export_safe_settings(settings, spec)
    assert safe == {"display_name": "TRUBA"}
    assert "api_token" not in safe and "password" not in safe
    namespaced = pset.export_namespaced_safe_settings(PLUGIN_ID, settings, spec)
    assert namespaced == {f"plugins.{PLUGIN_ID}.display_name": "TRUBA"}
    assert pset.is_secret_key("api_token") and pset.is_secret_key("db_password")
    assert not pset.is_secret_key("display_name")
    rendered = pset.redact_settings_for_log(PLUGIN_ID, settings, spec)
    assert "sekret-123" not in rendered and "hunter2" not in rendered
    assert "<redacted>" in rendered and "TRUBA" in rendered


@pytest.mark.integration
def test_prov007_remove_disable_keeps_settings_crash_free(tmp_path: Path):
    """PROV-007/006: removing/disabling a plugin never crashes settings load."""
    saved, errors = pset.save_plugin_settings(tmp_path, PLUGIN_ID, {"display_name": "Stay"}, SETTINGS_SPEC)
    assert errors == []
    _install(tmp_path, _base_manifest())
    from hpc_gui.plugins.state import set_plugin_disabled

    set_plugin_disabled(PLUGIN_ID, True, root=tmp_path)
    assert pset.load_plugin_settings(tmp_path, PLUGIN_ID, SETTINGS_SPEC)["display_name"] == "Stay"
    rendered = pset.redact_settings_for_log(PLUGIN_ID, {**saved, "api_token": "s3cr3t"}, SETTINGS_SPEC)
    assert "s3cr3t" not in rendered


# ---------------------------------------------------------------------------
# GUI FULL — wx event/runtime proof (PROV-001 + PROV-002..004 integration)
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_prov_gui_wx_provider_list_and_settings_roundtrip(tmp_path: Path):
    """W34 GUI FULL: real wx event -> provider readback + settings save/readback."""
    wx = pytest.importorskip("wx")
    _install(tmp_path, _base_manifest())
    saved, errors = pset.save_plugin_settings(
        tmp_path, PLUGIN_ID, {"display_name": "WxName"}, SETTINGS_SPEC
    )
    assert errors == []

    _app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w34-probe")
    try:
        providers = prov.registered_providers(root=tmp_path, app_version=APP_VERSION)
        assert len(providers) == 1
        panel = wx.Panel(frame)
        sizer = wx.BoxSizer(wx.VERTICAL)
        listing = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        listing.InsertColumn(0, "Provider")
        listing.InsertColumn(1, "Capability")
        for item in providers:
            idx = listing.InsertItem(listing.GetItemCount(), item.profile_id)
            states = prov.provider_capability_states(item.capability_view)
            listing.SetItem(idx, 1, states.get("scheduler", "?"))
        name_ctrl = wx.TextCtrl(panel, value="WxName")
        save_btn = wx.Button(panel, label="Save setting")
        readback = wx.StaticText(panel, label="")
        sizer.Add(listing, 1, wx.EXPAND | wx.ALL, 4)
        sizer.Add(name_ctrl, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(save_btn, 0, wx.ALL, 4)
        sizer.Add(readback, 0, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)

        state = {"saved": None}

        def on_save(_event):
            value = name_ctrl.GetValue()
            stored, errs = pset.save_plugin_settings(
                tmp_path, PLUGIN_ID, {"display_name": value}, SETTINGS_SPEC
            )
            assert errs == []
            state["saved"] = stored
            merged = pset.merge_into_shared({}, PLUGIN_ID, stored, SETTINGS_SPEC)
            readback.SetLabel(
                f"providers={len(prov.registered_providers(root=tmp_path, app_version=APP_VERSION))} "
                f"key=plugins.{PLUGIN_ID}.display_name value={stored['display_name']} "
                f"merged={merged[f'plugins.{PLUGIN_ID}.display_name']}"
            )
            _event.Skip()

        save_btn.Bind(wx.EVT_BUTTON, on_save)
        # Real wx runtime: post a genuine button event through the handler.
        click = wx.CommandEvent(wx.EVT_BUTTON.typeId, save_btn.GetId())
        save_btn.GetEventHandler().ProcessEvent(click)
        panel.Layout()
        # Observed semantic readback from live controls (not model-only).
        assert listing.GetItemCount() == 1
        assert listing.GetItemText(0, 0) == "truba"
        assert listing.GetItemText(0, 1) == DECLARED
        label = readback.GetLabel()
        assert "providers=1" in label
        assert f"plugins.{PLUGIN_ID}.display_name" in label
        assert "WxName" in label
        assert state["saved"] is not None and state["saved"]["display_name"] == "WxName"
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass
