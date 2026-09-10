"""Existing-user config migration and recovery tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from hpc_gui.config import storage


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

    second = storage.load_profiles()
    assert second[0]["id"] == first_id
    assert second[0]["transfer_parallelism"] == 4
    assert cfg_path.read_bytes() == saved


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
