from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.core import paths


def test_macos_paths_use_application_support_and_logs(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(paths, "current_os", lambda: "macos")
    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)

    assert paths.app_data_dir() == tmp_path / "Library" / "Application Support" / "HPC Client GUI"
    assert paths.app_log_dir() == tmp_path / "Library" / "Logs" / "HPC Client GUI"


def test_non_macos_keeps_legacy_path(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(paths, "current_os", lambda: "windows")
    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)

    assert paths.app_data_dir() == tmp_path / ".truba_slurm_gui"


def test_macos_copies_known_legacy_data_once(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(paths, "current_os", lambda: "macos")
    legacy = paths.legacy_app_data_dir(tmp_path)
    legacy.mkdir()
    (legacy / "config.json").write_text("{}", encoding="utf-8")
    (legacy / "app.log").write_text("log", encoding="utf-8")
    (legacy / "ignored.txt").write_text("ignored", encoding="utf-8")

    assert paths.migrate_legacy_app_data(home=tmp_path) is True
    target = tmp_path / "Library" / "Application Support" / "HPC Client GUI"
    assert (target / "config.json").read_text(encoding="utf-8") == "{}"
    assert not (target / "ignored.txt").exists()
    assert (tmp_path / "Library" / "Logs" / "HPC Client GUI" / "app.log").is_file()
    assert paths.migrate_legacy_app_data(home=tmp_path) is False
    assert (legacy / "config.json").exists()


def test_macos_migration_rejects_symlinked_entries(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(paths, "current_os", lambda: "macos")
    legacy = paths.legacy_app_data_dir(tmp_path)
    legacy.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("x", encoding="utf-8")
    try:
        (legacy / "plugins").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable")

    with pytest.raises(RuntimeError, match="symlinked"):
        paths.migrate_legacy_app_data(home=tmp_path)
