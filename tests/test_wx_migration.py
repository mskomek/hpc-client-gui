"""Existing-user config migration and recovery tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from hpc_gui.config import storage


@pytest.mark.contract
def test_legacy_profile_migration_preserves_unicode_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_config_dir", lambda: tmp_path)
    cfg_path = tmp_path / "config.json"
    legacy = {
        "profiles": [
            {
                "name": "Türkçe İş",
                "host": "levrek1",
                "username": "işçi",
                "home_dir": "/home/işçi",
                "future_field": {"path": "日本語"},
            }
        ],
        "settings": {"transfer_parallelism": 4},
        "version": 1,
    }
    cfg_path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")

    first = storage.load_profiles()
    assert first[0]["name"] == "Türkçe İş"
    assert first[0]["username"] == "işçi"
    assert first[0]["home_dir"] == "/home/işçi"
    assert first[0]["future_field"] == {"path": "日本語"}
    assert first[0]["transfer_parallelism"] == 4
    first_id = first[0]["id"]
    saved = cfg_path.read_bytes()
    assert (tmp_path / "config.json.bak").read_bytes() == json.dumps(legacy, ensure_ascii=False).encode("utf-8")

    second = storage.load_profiles()
    assert second[0]["id"] == first_id
    assert second[0]["transfer_parallelism"] == 4
    assert cfg_path.read_bytes() == saved
    assert list(tmp_path.glob("config.json.bak*")) == [tmp_path / "config.json.bak"]


@pytest.mark.gui
def test_migration_save_failure_keeps_original_config_readable(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_config_dir", lambda: tmp_path)
    cfg_path = tmp_path / "config.json"
    original = json.dumps(
        {"profiles": [{"name": "Türkçe İş"}], "settings": {"transfer_parallelism": 4}},
        ensure_ascii=False,
    ).encode("utf-8")
    cfg_path.write_bytes(original)

    def fail_save(_cfg):
        raise OSError("simulated migration write failure")

    monkeypatch.setattr(storage, "save_config", fail_save)
    with pytest.raises(OSError, match="simulated migration write failure"):
        storage.load_profiles()

    assert cfg_path.read_bytes() == original
    assert (tmp_path / "config.json.bak").read_bytes() == original


@pytest.mark.gui
def test_corrupt_config_keeps_unique_recovery_backups(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_config_dir", lambda: tmp_path)
    cfg_path = tmp_path / "config.json"

    first_corrupt = b"{not-json"
    cfg_path.write_bytes(first_corrupt)
    assert storage.load_config() == {"profiles": [], "settings": {}}
    assert (tmp_path / "config.json.bak").read_bytes() == first_corrupt

    second_corrupt = b"[]"
    cfg_path.write_bytes(second_corrupt)
    assert storage.load_config() == {"profiles": [], "settings": {}}
    assert (tmp_path / "config.json.bak.1").read_bytes() == second_corrupt


@pytest.mark.gui
def test_diagnostic_bundle_excludes_saved_profile_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    data_dir = tmp_path / ".truba_slurm_gui"
    data_dir.mkdir()
    (data_dir / "config.json").write_text(
        json.dumps({"profiles": [{"password": "secret123"}]}), encoding="utf-8"
    )

    from hpc_gui.core.diagnostics import create_diagnostic_bundle

    bundle = create_diagnostic_bundle(str(tmp_path / "out"))
    with zipfile.ZipFile(bundle) as archive:
        assert "config.json" not in archive.namelist()
        assert all("secret123" not in archive.read(name).decode("utf-8") for name in archive.namelist())
