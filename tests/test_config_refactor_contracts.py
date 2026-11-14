"""Portable storage invariants for the already modularized develop config layer."""

from __future__ import annotations

import json

import pytest

from hpc_gui.config import _storage_core as core
from hpc_gui.config import _storage_profiles as profiles


pytestmark = pytest.mark.unit


def test_legacy_parallelism_migrates_without_losing_unrelated_fields():
    profile = {
        "name": "cluster", "id": "stable-id", "password_enc": "opaque",
        "plugin_meta": {"future_key": True},
    }
    existing = {"name": "other", "transfer_parallelism": 3}
    config = {
        "profiles": [profile, existing],
        "settings": {"transfer_parallelism": 42, "future_setting": False},
    }

    assert core.migrate_legacy_transfer_parallelism(config) is True
    assert profile["transfer_parallelism"] == 10
    assert existing["transfer_parallelism"] == 3
    assert profile["password_enc"] == "opaque"
    assert profile["plugin_meta"] == {"future_key": True}
    assert config["settings"]["future_setting"] is False
    assert core.migrate_legacy_transfer_parallelism(config) is False


def test_corrupt_config_is_backed_up_before_fallback(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    raw = '{"profiles": [broken json'
    path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(core, "_config_path", lambda: path)

    assert core.load_config() == {"profiles": [], "settings": {}}
    assert (tmp_path / "config.json.bak").read_text(encoding="utf-8") == raw


def test_profile_migration_creates_backup_once_and_retains_identity(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "profiles": [{"name": "cluster", "password_enc": "opaque"}],
        "settings": {"transfer_parallelism": 4},
        "future_root": {"supported": True},
    }), encoding="utf-8")
    monkeypatch.setattr(core, "_config_path", lambda: path)

    first = profiles.load_profiles()
    assert first[0]["id"]
    assert first[0]["transfer_parallelism"] == 4
    assert first[0]["password_enc"] == "opaque"
    assert profiles.load_profiles()[0]["id"] == first[0]["id"]
    assert (tmp_path / "config.json.bak").is_file()
    assert not (tmp_path / "config.json.bak.1").exists()
    assert core.load_config()["future_root"] == {"supported": True}


def test_upsert_rename_preserves_id_and_unknown_fields(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    monkeypatch.setattr(core, "_config_path", lambda: path)

    profiles.upsert_profile({
        "name": "before", "id": "stable-id", "password_enc": "opaque",
        "plugin_meta": {"future": 1},
    })
    saved = profiles.load_profiles()[0]
    updated = core.merge_profile_patch(saved, {"name": "after", "host": "login.example"})
    profiles.upsert_profile(updated)

    config = core.load_config()
    assert len(config["profiles"]) == 1
    assert config["profiles"][0]["name"] == "after"
    assert config["profiles"][0]["id"] == "stable-id"
    assert config["profiles"][0]["plugin_meta"] == {"future": 1}
    assert config["profiles"][0]["password_enc"] == "opaque"
