"""A8 regression tests: legacy global transfer-parallelism migration.

v1.4.0 made the per-profile ``transfer_parallelism`` the single authority;
these tests pin the one-time, idempotent copy of the old global setting into
profiles that lack a valid profile-specific value.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from hpc_gui.config import storage


def _config(tmp_path: Path):
    config = tmp_path / "config.json"
    return patch("hpc_gui.config.storage._config_path", return_value=config), config


def _write_config(config: Path, payload: dict) -> None:
    config.write_text(json.dumps(payload), encoding="utf-8")


def test_legacy_global_value_copied_into_profiles_missing_field(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(
        config,
        {
            "profiles": [
                {"name": "a", "id": "1"},
                {"name": "b", "id": "2"},
            ],
            "settings": {"transfer_parallelism": 4},
        },
    )
    with unpatch:
        profiles = storage.load_profiles()
    assert [p["transfer_parallelism"] for p in profiles] == [4, 4]
    # The global value stays readable as a migration source only; it is not
    # removed here (removal is not required and history must stay intact).


def test_existing_profile_specific_value_wins(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(
        config,
        {
            "profiles": [{"name": "a", "id": "1", "transfer_parallelism": 7}],
            "settings": {"transfer_parallelism": 4},
        },
    )
    with unpatch:
        profiles = storage.load_profiles()
    assert profiles[0]["transfer_parallelism"] == 7


def test_malformed_profile_and_legacy_values_fall_back_to_default(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(
        config,
        {
            "profiles": [{"name": "a", "id": "1", "transfer_parallelism": "fast"}],
            "settings": {"transfer_parallelism": "lots"},
        },
    )
    with unpatch:
        profiles = storage.load_profiles()
    assert profiles[0]["transfer_parallelism"] == 1


def test_no_legacy_value_uses_safe_default(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(config, {"profiles": [{"name": "a", "id": "1"}], "settings": {}})
    with unpatch:
        profiles = storage.load_profiles()
    assert profiles[0]["transfer_parallelism"] == 1


def test_out_of_range_values_are_clamped(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(
        config,
        {
            "profiles": [{"name": "a", "id": "1"}],
            "settings": {"transfer_parallelism": 99},
        },
    )
    with unpatch:
        profiles = storage.load_profiles()
    assert profiles[0]["transfer_parallelism"] == 10


def test_multiple_profiles_migrated_in_one_pass(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(
        config,
        {
            "profiles": [
                {"name": "a", "id": "1"},
                {"name": "b", "id": "2", "transfer_parallelism": 3},
                {"name": "c", "id": "3"},
            ],
            "settings": {"transfer_parallelism": 5},
        },
    )
    with unpatch:
        profiles = storage.load_profiles()
    assert [p["transfer_parallelism"] for p in profiles] == [5, 3, 5]


def test_migration_is_idempotent_across_launches(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    _write_config(
        config,
        {
            "profiles": [{"name": "a", "id": "1"}],
            "settings": {"transfer_parallelism": 6},
        },
    )
    with unpatch:
        first = storage.load_profiles()
        assert first[0]["transfer_parallelism"] == 6
        on_disk_after_first = json.loads(config.read_text(encoding="utf-8"))

        # Later launches must not rewrite or change the profile value.
        second = storage.load_profiles()
        assert second[0]["transfer_parallelism"] == 6
        assert json.loads(config.read_text(encoding="utf-8")) == on_disk_after_first


def test_unknown_encrypted_and_nested_fields_survive(tmp_path: Path) -> None:
    unpatch, config = _config(tmp_path)
    profile = {
        "name": "lab",
        "id": "stable-id",
        "password_dpapi": "enc-blob",
        "system_template_source": {"plugin_id": "org.hpcclient.truba"},
        "file_manager": {"local_start_dir": "D:/data"},
        "jump_host": {"enabled": True, "host": "jump"},
        "future_unknown_field": {"x": 1},
    }
    _write_config(
        config,
        {"profiles": [profile], "settings": {"transfer_parallelism": 2}},
    )
    with unpatch:
        migrated = storage.load_profiles()[0]
    assert migrated["password_dpapi"] == "enc-blob"
    assert migrated["system_template_source"] == {"plugin_id": "org.hpcclient.truba"}
    assert migrated["file_manager"] == {"local_start_dir": "D:/data"}
    assert migrated["jump_host"] == {"enabled": True, "host": "jump"}
    assert migrated["future_unknown_field"] == {"x": 1}
    assert migrated["id"] == "stable-id"
