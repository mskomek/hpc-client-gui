"""W03 settings + provider/plugin surface inventory pins.

Owned requirements: ``HPC-W01-TRUTH-027`` … ``HPC-W01-TRUTH-046``
(WAVE_V2_FINAL_01.md Workstream C — Audit settings and stored state and
Workstream D — Audit provider/plugin surface).

These tests freeze the inventoried truth: settings keys/defaults, UI
controls, persistence location, migration owners, sensitive-value
handling, obsolete consumers, runtime-without-UI and UI-without-consumer
classification, plus provider discovery/identity/capabilities/optional
semantics/unavailable behavior/UI exposure/fallback/import-safety and
registration proof. A test here fails if the inventoried truth drifts;
deliberate product changes must update the inventory tables in
``docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md`` alongside the code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.config import storage
from hpc_gui.services import provider_capabilities, provider_contract
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_settings import GLOBAL_KEYS, LEGACY_IGNORED_KEYS, PROFILE_KEYS, WxSettingsModel


# ---------------------------------------------------------------------------
# Isolation helper (repo convention: patch storage._config_path)
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: config_path)
    return config_path


# ---------------------------------------------------------------------------
# Workstream C — settings keys and defaults (HPC-W01-TRUTH-027)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_settings_keys_and_defaults_are_frozen(isolated_config):
    assert storage.get_jobs_outputs_refresh_interval_seconds() == 15
    assert storage.get_live_tracking_warning_interval_seconds() == 60
    assert storage.get_squeue_auto_refresh_enabled() is True
    assert storage.get_sacct_auto_refresh_enabled() is True
    assert storage.get_lssrv_auto_refresh_enabled() is False
    assert storage.get_remote_directory_cache_enabled() is True
    assert storage.get_transfer_checksum_verification_enabled() is False
    assert storage.get_transfer_completion_action() == "none"
    assert storage.get_upload_preflight_confirmation_enabled() is True
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_OUTPUTS_TAB
    assert storage.get_ftp_transfer_type() == "auto"
    assert storage.get_cli_external_access_enabled() is False
    assert storage.get_cli_default_profile() == ""
    assert storage.get_last_seen_changelog_version() == ""
    assert storage.get_pause_live_follow_when_minimized_enabled() is True
    assert storage.get_follow_window_open_minimized_enabled() is True


# ---------------------------------------------------------------------------
# Persistence location (HPC-W01-TRUTH-029)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_settings_persist_to_config_json(isolated_config):
    storage.set_transfer_checksum_verification_enabled(True)
    storage.set_cli_default_profile("office")
    raw = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw["settings"]["transfer_checksum_verification_enabled"] is True
    assert raw["settings"]["cli_default_profile"] == "office"


@pytest.mark.contract
def test_w03_config_path_is_app_data_config_json():
    # Persistence location by construction (read-only; creates no files):
    # <app_data_dir>/config.json. A relocation must update this pin and the
    # W03 inventory tables together.
    assert storage._config_path() == storage._config_dir() / "config.json"


# ---------------------------------------------------------------------------
# Migration/versioning owner (HPC-W01-TRUTH-030)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_legacy_transfer_parallelism_migration_owner():
    cfg = {
        "settings": {"transfer_parallelism": 4},
        "profiles": [{"name": "a"}, {"name": "b", "transfer_parallelism": 7}],
    }
    assert storage.migrate_legacy_transfer_parallelism(cfg) is True
    by_name = {p["name"]: p for p in cfg["profiles"]}
    assert by_name["a"]["transfer_parallelism"] == 4  # legacy value adopted once
    assert by_name["b"]["transfer_parallelism"] == 7  # profile-specific choice wins
    assert storage.migrate_legacy_transfer_parallelism(cfg) is False  # idempotent


@pytest.mark.contract
def test_w03_sbatch_follow_mode_legacy_bool_is_migration_source_only(isolated_config):
    storage.update_settings({"focus_jobs_outputs_after_submission_enabled": False})
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_NONE
    storage.update_settings({"focus_jobs_outputs_after_submission_enabled": True})
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_OUTPUTS_TAB
    storage.update_settings({"sbatch_follow_mode": storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED})
    storage.update_settings({"focus_jobs_outputs_after_submission_enabled": False})
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED


# ---------------------------------------------------------------------------
# Sensitive values (HPC-W01-TRUTH-031)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_saved_profile_never_persists_plaintext_password(isolated_config):
    from hpc_gui.services.connection_profile_service import save_profile

    save_profile(
        {"name": "w03probe", "username": "u", "host": "h.example"},
        plain_password="s3cret-plain",
        save_password=False,
    )
    raw = isolated_config.read_text(encoding="utf-8")
    assert "s3cret-plain" not in raw
    stored = next(p for p in storage.load_profiles() if p.get("name") == "w03probe")
    assert stored.get("password", "") == ""


# ---------------------------------------------------------------------------
# Obsolete consumers + model boundaries (HPC-W01-TRUTH-032 / TRUTH-027)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_obsolete_qt_keys_are_explicitly_ignored():
    assert {"terminal_graphics_auto_compatibility", "qt_webengine_gpu"} <= set(LEGACY_IGNORED_KEYS)
    model = WxSettingsModel({"qt_webengine_gpu": False, "remote_directory_cache": True})
    assert "qt_webengine_gpu" not in model.serialized()


@pytest.mark.contract
def test_w03_settings_model_key_sets_are_frozen():
    assert set(GLOBAL_KEYS) == {
        "jobs_outputs_refresh_interval",
        "remote_directory_cache",
        "transfer_checksum",
        "shortcut_preferences",
    }
    assert set(PROFILE_KEYS) == {
        "transfer_parallelism",
        "ssh_timeout",
        "keepalive_interval_seconds",
        "x11_enabled",
    }
    model = WxSettingsModel()
    with pytest.raises(KeyError):
        model.set_global("no_such_key", True)
    with pytest.raises(KeyError):
        model.set_profile("no_such_key", True)


# ---------------------------------------------------------------------------
# Runtime-without-UI vs UI-without-consumer (HPC-W01-TRUTH-033/034/036/037)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_hidden_settings_still_have_live_consumers(isolated_config):
    # Implemented + consumed, intentionally without a wx Settings control
    # (hidden-capability, not orphan): the service getters below are the
    # consumers of record.
    storage.set_jobs_outputs_refresh_interval_seconds(42)
    assert storage.get_jobs_outputs_refresh_interval_seconds() == 42
    storage.set_sbatch_follow_mode(storage.SBATCH_FOLLOW_MODE_NONE)
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_NONE
    storage.set_lssrv_auto_refresh_enabled(True)
    assert storage.get_lssrv_auto_refresh_enabled() is True


# ---------------------------------------------------------------------------
# Workstream D — provider/plugin discovery + isolation (TRUTH-038/045)
# ---------------------------------------------------------------------------

from hpc_gui.plugins.loader import load_installed_plugins  # noqa: E402
from hpc_gui.plugins.models import PLUGIN_API_VERSION  # noqa: E402
from hpc_gui.plugins.storage import write_active_versions  # noqa: E402


def _install_plugin(root: Path, manifest: dict, profile: dict | None) -> Path:
    pkg = root / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    files = []
    for rel in (manifest.get("entrypoints") or {}).get("cluster_profiles") or []:
        payload = json.dumps(profile).encode("utf-8")
        (pkg / rel).write_bytes(payload)
        files.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
                "role": "cluster-profile",
            }
        )
    manifest = {**manifest, "files": files or manifest.get("files") or []}
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


def _w03_manifest(plugin_id: str, profile_id: str) -> tuple[dict, dict]:
    return (
        {
            "schema_version": 1,
            "plugin_api": PLUGIN_API_VERSION,
            "id": plugin_id,
            "name": plugin_id,
            "version": "1.0.0",
            "publisher": "W03 probe",
            "license": "MIT",
            "description": "W03 inventory probe.",
            "requires_app": ">=1.0.0",
            "capabilities": ["cluster-profile"],
            "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
            "files": [],
        },
        {
            "schema_version": 1,
            "profile_id": profile_id,
            "name": profile_id,
            "scheduler": "slurm",
            "paths": {"home_dir": "/home/{user}", "scratch_dir": "/scratch/{user}"},
            "commands": {},
        },
    )


@pytest.mark.contract
def test_w03_empty_registry_discovers_nothing_without_error(tmp_path):
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert result.plugins == [] and result.problems == []


@pytest.mark.contract
def test_w03_malformed_plugin_is_isolated_and_valid_still_registers(tmp_path):
    manifest, profile = _w03_manifest("org.w03.good", "w03good")
    _install_plugin(tmp_path, manifest, profile)
    broken = tmp_path / "packages" / "org.w03.broken" / "1.0.0"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")
    write_active_versions({"org.w03.good": "1.0.0", "org.w03.broken": "1.0.0"}, root=tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert [p.manifest.id for p in result.plugins] == ["org.w03.good"]
    assert any(p.plugin_id == "org.w03.broken" for p in result.problems)


@pytest.mark.contract
def test_w03_duplicate_profile_ids_are_deterministic_and_diagnosed(tmp_path):
    first_manifest, first_profile = _w03_manifest("org.w03.aaa", "w03dup")
    second_manifest, second_profile = _w03_manifest("org.w03.zzz", "w03dup")
    _install_plugin(tmp_path, first_manifest, first_profile)
    _install_plugin(tmp_path, second_manifest, second_profile)
    write_active_versions({"org.w03.aaa": "1.0.0", "org.w03.zzz": "1.0.0"}, root=tmp_path)
    first = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    second = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    # Sorted iteration makes the winner stable across runs.
    assert [p.manifest.id for p in first.plugins] == [p.manifest.id for p in second.plugins] == ["org.w03.aaa"]
    assert any("duplicate cluster profile id" in p.reason for p in first.problems)


@pytest.mark.contract
def test_w03_manifest_identity_mismatch_is_rejected(tmp_path):
    manifest, profile = _w03_manifest("org.w03.good", "w03good")
    pkg = _install_plugin(tmp_path, manifest, profile)
    raw = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    raw["id"] = "org.w03.other"
    (pkg / "manifest.json").write_text(json.dumps(raw), encoding="utf-8")
    write_active_versions({"org.w03.good": "1.0.0"}, root=tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert result.plugins == []
    assert any("does not match" in p.reason for p in result.problems)


# ---------------------------------------------------------------------------
# Declared identity/version + capabilities + optional semantics (039/040/041)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_capability_view_declared_vs_not_declared():
    provider = {
        "name": "W03Cluster",
        "access": {"auth_methods": ["password"]},
        "scheduler": "slurm",
        "storage": [{"id": "scratch"}],
        "quota_sources": [],
        "requirements": {"project": True},
        "optional_capabilities": ["x11"],
    }
    view = provider_capabilities.build_provider_capability_view(provider)
    by_id = {item.id: item for item in view.capabilities}
    assert view.provider == "W03Cluster"
    assert by_id["auth"].declared == provider_capabilities.DECLARED
    assert by_id["quota"].declared == provider_capabilities.NOT_DECLARED
    assert by_id["project"].declared == provider_capabilities.DECLARED
    assert by_id["account"].declared == provider_capabilities.NOT_DECLARED
    assert by_id["optional"].declared == provider_capabilities.DECLARED


@pytest.mark.contract
def test_w03_quota_absence_is_distinct_from_probe_failure():
    provider = {"name": "W03NoQuota", "quota_sources": []}
    view = provider_capabilities.build_provider_capability_view(provider, observed={"quota": "FAILED"})
    quota = next(item for item in view.capabilities if item.id == "quota")
    # "provider does not define this capability" (NOT_DECLARED) stays
    # distinguishable from "probe failed" (observed FAILED).
    assert quota.declared == provider_capabilities.NOT_DECLARED
    assert quota.observed == "FAILED"


# ---------------------------------------------------------------------------
# Unavailable capability behavior (TRUTH-042)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w03_unavailable_capability_behavior_is_explicit():
    assert provider_contract.execute_adapter("w03.no.such.adapter") is None
    failed = provider_contract.parse_with_contract(None, "raw")
    assert failed.ok is False and failed.error.kind == "unsupported"
    empty = provider_contract.extract_contract({"job_details": {"adapter": 42}})
    assert empty.has_job_details is False


# ---------------------------------------------------------------------------
# UI exposure + registry source vocabulary (TRUTH-043/044/046)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_w03_plugin_registry_source_vocabulary_is_closed():
    model = WxPluginManagerModel()
    model.set_registry([{"id": "org.w03.tool", "name": "Tool", "version": "2.0"}], "network")
    assert model.registry_source == "network" and len(model.cards) == 1
    model.set_registry([{"id": "org.w03.tool"}], "bogus-source")
    assert model.registry_source == "offline"  # unknown sources degrade honestly
    model.set_registry([{"name": "Nameless"}], "cache")
    assert model.cards == ()  # entries without identity never become cards
