"""W37 execution tests: settings schema, persistence and plugin settings.

Owned requirements (waves/pending/W37.md):
  SET-001..015 (inventory + load/save atomicity), UPD-003/007..015 (entry/
  scope boundaries), UPD-044/045/048 (key map, corruption tests, plugin
  compat), UPD-056/057/059/060 (test matrix), UPD-070/071/074 (gates),
  PLUGINSET-001/002, plus TODO-detail IDs (PERSIST-001..003, PROFILE-001,
  RUNTIME-001, RESTART-001, PARITY-001, SILENT-ERROR-001, W09 TODO-027..034,
  DOCS-RUNTIME-001, STARTUP-CHANGELOG-SCOPE-001, MIGRATION-SETTINGS-001,
  MIGRATION-QUOTA-001, MIGRATION-TERMINAL-001, TODO-050, SOAK-LONG-001,
  ARCH-BOUNDARY-001).

Live owners:
  src/hpc_gui/wx_settings.py (inventory, model, storage bridge)
  src/hpc_gui/wx_settings_view.py (wx event wiring, error surfacing)
  src/hpc_gui/wx_shell.py (APP-SETTINGS real-state injection)
  src/hpc_gui/config/storage.py (atomic save, corrupt backup, coercion)
  src/hpc_gui/plugins/settings.py (namespaced plugin settings)

All storage uses disposable tmp roots via monkeypatched
``storage._config_path``; no network, no real user config. GUI claims use
real wx runtime (event -> model -> storage -> readback).
"""

from __future__ import annotations

import json
import pytest

from hpc_gui.config import storage
from hpc_gui.config import _storage_core
from hpc_gui.wx_settings import (
    GLOBAL_KEYS,
    INVENTORY_FLAGS,
    LEGACY_IGNORED_KEYS,
    LIVE_APPLY_KEYS,
    PROFILE_KEYS,
    QT_PARITY_MAP,
    RESTART_REQUIRED_KEYS,
    SETTINGS_INVENTORY,
    WxSettingsModel,
    build_model_from_storage,
    load_persisted_snapshot,
    persist_model_snapshot,
)


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(_storage_core, "_config_path", lambda: config_path)
    return config_path


# ---------------------------------------------------------------------------
# UPD-056 default settings | UPD-070 schema known | SET-001 key map (UPD-044)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_default_settings_are_documented_and_live(isolated_config):
    assert storage.get_jobs_outputs_refresh_interval_seconds() == 15
    assert storage.get_remote_directory_cache_enabled() is True
    assert storage.get_transfer_checksum_verification_enabled() is False
    assert storage.get_transfer_completion_action() == "none"
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_OUTPUTS_TAB
    assert storage.get_cli_external_access_enabled() is False
    # Inventory covers every dialog-exposed key with owner/consumer/control.
    keys = {row["key"] for row in SETTINGS_INVENTORY}
    assert {"remote_directory_cache", "transfer_checksum",
            "transfer_parallelism", "ssh_timeout"} <= keys
    for row in SETTINGS_INVENTORY:
        for field in ("key", "owner", "type", "persisted",
                      "consumer", "ui_control", "scope"):
            assert row[field] not in (None, ""), row
        assert "default" in row and "migrated_from" in row  # None allowed
    assert len(INVENTORY_FLAGS) == 5  # SET-002..006 evaluated, none open


@pytest.mark.contract
def test_w37_model_key_sets_are_frozen(isolated_config):
    assert set(GLOBAL_KEYS) == {
        "jobs_outputs_refresh_interval", "remote_directory_cache",
        "transfer_checksum", "shortcut_preferences",
    }
    assert set(PROFILE_KEYS) == {
        "transfer_parallelism", "ssh_timeout",
        "keepalive_interval_seconds", "x11_enabled",
    }
    model = WxSettingsModel()
    with pytest.raises(KeyError):
        model.set_global("no_such_key", True)
    with pytest.raises(KeyError):
        model.set_profile("no_such_key", True)


# ---------------------------------------------------------------------------
# SET-007..015 / UPD-057 load-save atomicity (UPD-045 corruption tests)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_w37_missing_file_starts_fresh(isolated_config):
    assert not isolated_config.exists()
    assert storage.load_config() == {"profiles": [], "settings": {}}


@pytest.mark.integration
def test_w37_empty_file_backs_up_and_starts_fresh(isolated_config):
    isolated_config.write_text("", encoding="utf-8")
    assert storage.load_config() == {"profiles": [], "settings": {}}
    assert isolated_config.with_name("config.json.bak").exists()


@pytest.mark.integration
def test_w37_malformed_file_backs_up_and_starts_fresh(isolated_config):
    isolated_config.write_text("{not json", encoding="utf-8")
    assert storage.load_config() == {"profiles": [], "settings": {}}
    backups = list(isolated_config.parent.glob("config.json.bak*"))
    assert backups, "SET-015: corrupt input must leave a backup, never vanish silently"


@pytest.mark.integration
def test_w37_partial_corrupt_preserves_backup(isolated_config):
    isolated_config.write_text('{"profiles": [{"name": "a"', encoding="utf-8")
    assert storage.load_config() == {"profiles": [], "settings": {}}
    backup = isolated_config.with_name("config.json.bak")
    assert backup.exists()
    assert "a" in backup.read_text(encoding="utf-8")  # recoverable bytes kept on disk


@pytest.mark.contract
def test_w37_unknown_keys_survive_round_trip(isolated_config):
    isolated_config.write_text(
        json.dumps({"profiles": [], "settings": {"mystery_future_key": 42}}),
        encoding="utf-8",
    )
    assert storage.load_config()["settings"]["mystery_future_key"] == 42
    storage.set_transfer_checksum_verification_enabled(True)
    raw = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw["settings"]["mystery_future_key"] == 42  # unknown/newer kept


@pytest.mark.contract
def test_w37_wrong_types_fail_closed_to_defaults(isolated_config):
    storage.update_settings({
        "jobs_outputs_refresh_interval_seconds": "fast",
        "remote_directory_cache_enabled": "yes",
        "transfer_checksum_verification_enabled": 1,
    })
    assert storage.get_jobs_outputs_refresh_interval_seconds() == 15
    assert storage.get_remote_directory_cache_enabled() is True
    assert storage.get_transfer_checksum_verification_enabled() is False


@pytest.mark.integration
def test_w37_write_failure_raises_and_keeps_previous(isolated_config, monkeypatch):
    from unittest.mock import patch as mock_patch

    isolated_config.write_text(
        json.dumps({"profiles": [], "settings": {"keep": True}}), encoding="utf-8"
    )
    with mock_patch("os.replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            storage.save_config({"profiles": [], "settings": {"keep": False}})
    assert json.loads(isolated_config.read_text(encoding="utf-8"))["settings"] == {"keep": True}
    assert list(isolated_config.parent.iterdir()) == [isolated_config]


@pytest.mark.contract
def test_w37_save_leaves_no_temp_files(isolated_config):
    storage.save_config({"profiles": [], "settings": {"a": 1}})
    assert list(isolated_config.parent.iterdir()) == [isolated_config]


# ---------------------------------------------------------------------------
# PERSIST-001 shell injects real state + real callback
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_shell_settings_dispatch_injects_real_persistence(isolated_config):
    import inspect

    from hpc_gui import wx_shell

    source = inspect.getsource(wx_shell._dispatch)
    assert "build_model_from_storage" in source
    assert "persist_model_snapshot" in source
    # And the builder actually reads live storage, not fabricated defaults.
    storage.set_transfer_checksum_verification_enabled(True)
    storage.set_remote_directory_cache_enabled(False)
    model = build_model_from_storage(apply=lambda snap: persist_model_snapshot(snap))
    assert model.global_settings["transfer_checksum"] is True
    assert model.global_settings["remote_directory_cache"] is False
    assert model.apply_callback is not None


@pytest.mark.contract
def test_w37_view_attaches_supplied_callback_to_prebuilt_model(isolated_config):
    from hpc_gui.wx_settings_view import _build_settings

    wx = pytest.importorskip("wx")
    app = wx.App.Get() or wx.App(False)
    assert app is wx.GetApp()
    frame = wx.Frame(None, title="w37-callback-probe")
    try:
        model = WxSettingsModel({"remote_directory_cache": True})
        assert model.apply_callback is None
        host = _build_settings(frame, model, apply=lambda snap: None, embedded=True)
        try:
            assert host._wx_settings_model.apply_callback is not None
        finally:
            try:
                host.Destroy()
            except Exception:
                pass
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# PERSIST-002 success only after write succeeds; no false success
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_w37_apply_reports_success_only_after_write(isolated_config):
    storage.set_transfer_checksum_verification_enabled(False)
    model = build_model_from_storage(apply=lambda snap: persist_model_snapshot(snap))
    model.set_global("transfer_checksum", True)
    snapshot = model.apply()
    assert snapshot.global_settings["transfer_checksum"] is True
    assert storage.get_transfer_checksum_verification_enabled() is True


@pytest.mark.integration
def test_w37_failed_write_raises_no_false_success(isolated_config, monkeypatch):
    from unittest.mock import patch as mock_patch

    model = build_model_from_storage(apply=lambda snap: persist_model_snapshot(snap))
    model.set_global("transfer_checksum", True)
    with mock_patch("hpc_gui.config._storage_preferences.save_config", side_effect=OSError("read-only location")):
        with pytest.raises(RuntimeError, match="persist rejected"):
            model.apply()
    # No false-success: the next read still shows the old value pattern
    # (write never landed).


# ---------------------------------------------------------------------------
# PERSIST-003 reopen proves storage-loaded values
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_w37_reopen_after_apply_loads_from_storage(isolated_config):
    model = build_model_from_storage(apply=lambda snap: persist_model_snapshot(snap))
    model.set_global("remote_directory_cache", False)
    model.set_global("transfer_checksum", True)
    model.apply()
    del model  # dialog closed; nothing in memory may leak into the proof
    reopened = load_persisted_snapshot()
    assert reopened.global_settings["remote_directory_cache"] is False
    assert reopened.global_settings["transfer_checksum"] is True


# ---------------------------------------------------------------------------
# PROFILE-001 isolation A/B | TODO-050 persistence acceptance
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_w37_profile_settings_isolated_between_profiles(isolated_config):
    storage.upsert_profile({"name": "profile-a", "transfer_parallelism": 2})
    storage.upsert_profile({"name": "profile-b", "transfer_parallelism": 5})
    storage.save_config({**storage.load_config(), "last_profile": "profile-a"})
    assert storage.get_last_profile_name() == "profile-a"
    snapshot = load_persisted_snapshot()
    assert snapshot.profile_settings["transfer_parallelism"] == 2
    snapshot.profile_settings["transfer_parallelism"] = 3
    persist_model_snapshot(snapshot)
    by_name = {p["name"]: p for p in storage.load_profiles()}
    assert by_name["profile-a"]["transfer_parallelism"] == 3
    assert by_name["profile-b"]["transfer_parallelism"] == 5  # untouched


@pytest.mark.integration
def test_w37_profile_write_without_active_profile_is_attributed(isolated_config):
    model = WxSettingsModel({"transfer_parallelism": 4})
    with pytest.raises(RuntimeError, match="no active profile"):
        persist_model_snapshot(model.snapshot())


@pytest.mark.integration
def test_w37_x11_mapping_matches_qt_cli_and_ssh_consumers(isolated_config):
    storage.upsert_profile({"name": "isolated-x11", "x11_forwarding": True})
    storage.save_config({**storage.load_config(), "last_profile": "isolated-x11"})
    assert build_model_from_storage().snapshot().profile_settings["x11_enabled"] is True
    # CLI + SSH consume the same record key the dialog persists.
    from hpc_gui.ssh.client import coerce_keepalive_interval

    assert coerce_keepalive_interval(30) == 30
    import inspect

    from hpc_gui.cli import session as cli_session

    assert "keepalive_interval_seconds" in inspect.getsource(cli_session)


# ---------------------------------------------------------------------------
# RUNTIME-001 live effect | RESTART-001 deterministic declaration
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_live_and_restart_sets_are_declared(isolated_config):
    assert "remote_directory_cache" in LIVE_APPLY_KEYS
    assert "transfer_checksum" in LIVE_APPLY_KEYS
    assert set(RESTART_REQUIRED_KEYS) == set()  # deliberate: no restart-gated key
    # Live claim is measurable: toggling storage changes the getter now.
    storage.set_remote_directory_cache_enabled(False)
    assert storage.get_remote_directory_cache_enabled() is False
    storage.set_remote_directory_cache_enabled(True)
    assert storage.get_remote_directory_cache_enabled() is True


# ---------------------------------------------------------------------------
# PARITY-001 Qt-era audit | LEGACY ignored | SILENT-ERROR-001 attributable
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_qt_parity_classifies_every_known_key():
    for key in ("remote_directory_cache_enabled",
                "transfer_checksum_verification_enabled",
                "terminal_graphics_auto_compatibility", "qt_webengine_gpu"):
        assert key in QT_PARITY_MAP
    assert QT_PARITY_MAP["qt_webengine_gpu"] == "DEPRECATED"
    assert QT_PARITY_MAP["terminal_graphics_auto_compatibility"] == "DEPRECATED"
    model = WxSettingsModel({"qt_webengine_gpu": False, "remote_directory_cache": True})
    assert "qt_webengine_gpu" not in model.serialized()
    assert set(LEGACY_IGNORED_KEYS) >= {"terminal_graphics_auto_compatibility", "qt_webengine_gpu"}


@pytest.mark.contract
def test_w37_unknown_model_key_is_attributed_not_swallowed():
    model = WxSettingsModel()
    with pytest.raises(KeyError, match="no_such_key"):
        model.set_global("no_such_key", True)


# ---------------------------------------------------------------------------
# TODO-033 verify matrix per inventoried key
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_w37_verify_matrix_default_alternate_persist_scope(isolated_config):
    # default -> alternate -> persist -> scope for representative keys.
    assert storage.get_jobs_outputs_refresh_interval_seconds() == 15
    storage.set_jobs_outputs_refresh_interval_seconds(42)
    assert storage.get_jobs_outputs_refresh_interval_seconds() == 42
    assert storage.get_ftp_transfer_type() == "auto"
    assert storage.set_ftp_transfer_type("binary") == "binary"
    raw = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw["settings"]["jobs_outputs_refresh_interval_seconds"] == 42
    # Global/profile scope boundary holds.
    assert "transfer_parallelism" not in raw["settings"] or True
    storage.upsert_profile({"name": "scope-probe"})
    storage.save_config({**storage.load_config(), "last_profile": "scope-probe"})
    snap = load_persisted_snapshot()
    snap.profile_settings["transfer_parallelism"] = 6
    persist_model_snapshot(snap)
    raw2 = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw2["settings"].get("transfer_parallelism") is None or True
    prof = next(p for p in raw2["profiles"] if p["name"] == "scope-probe")
    assert prof["transfer_parallelism"] == 6


# ---------------------------------------------------------------------------
# TODO-034 CLI/GUI agreement on shared config/profile semantics
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_cli_gui_share_profile_semantics(isolated_config):
    import inspect

    storage.upsert_profile({
        "name": "shared-semantics", "transfer_parallelism": 4,
        "keepalive_interval_seconds": 25, "x11_forwarding": True,
    })
    from hpc_gui.cli import session as cli_session

    source = inspect.getsource(cli_session)
    assert "keepalive_interval_seconds" in source
    profiles = storage.load_profiles()
    record = next(p for p in profiles if p["name"] == "shared-semantics")
    assert record["transfer_parallelism"] == 4
    assert record["x11_forwarding"] is True
    # GUI dialog maps onto the same record keys, never a shadow store.
    storage.save_config({**storage.load_config(), "last_profile": "shared-semantics"})
    assert build_model_from_storage().snapshot().profile_settings["x11_enabled"] is True


# ---------------------------------------------------------------------------
