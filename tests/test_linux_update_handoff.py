import os
from pathlib import Path

import pytest

from hpc_gui.services.linux_update_handoff import (
    appimage_path,
    detect_flatpak,
    replace_appimage,
    stage_appimage,
)


def test_appimage_path_requires_real_runtime_file(tmp_path: Path):
    image = tmp_path / "app.AppImage"
    image.write_bytes(b"image")
    assert appimage_path({"APPIMAGE": str(image)}) == image.resolve()
    assert appimage_path({}) is None


def test_appimage_stages_and_replaces_with_recovery_copy(tmp_path: Path):
    source = tmp_path / "new.AppImage"
    destination = tmp_path / "client.AppImage"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")
    os.chmod(source, 0o755)
    staged = stage_appimage(source, destination)
    backup = replace_appimage(staged, destination)
    assert destination.read_bytes() == b"new"
    assert backup.read_bytes() == b"old"
    if os.name == "posix":
        assert destination.stat().st_mode & 0o111


def test_appimage_rejects_symlink_source(tmp_path: Path):
    source = tmp_path / "source.AppImage"
    source.write_bytes(b"image")
    link = tmp_path / "link.AppImage"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows test host")
    with pytest.raises(ValueError):
        stage_appimage(link, tmp_path / "destination.AppImage")


def test_flatpak_detection_exposes_external_handoff_only():
    class Result:
        returncode = 0

    def runner(command, **_kwargs):
        result = Result()
        result.stdout = "flathub" if "--show-origin" in command else "app/io.github.mskomek.HpcClientGui/x86_64/stable"
        return result

    context = detect_flatpak("io.github.mskomek.HpcClientGui", runner)
    assert context.origin == "flathub"
    assert context.update_command == ("flatpak", "update", "--app", "io.github.mskomek.HpcClientGui")
