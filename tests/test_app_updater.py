import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.services.app_updater import (
    UpdateRelease,
    _download,
    download_and_verify_release,
    launch_update_installer,
    release_asset_names,
)
from hpc_gui.ui.main_window import MainWindow


class _Response:
    headers = {"Content-Length": "2"}

    def __init__(self):
        self._chunks = iter((b"a", b"b"))

    def read(self, _size):
        return next(self._chunks, b"")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_cancelled_update_download_removes_partial_file(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("hpc_gui.services.app_updater._request", lambda *_args, **_kwargs: _Response())
    cancelled = False

    def progress(*_args):
        nonlocal cancelled
        cancelled = True

    with pytest.raises(RuntimeError, match="cancelled"):
        _download("https://example.invalid/update.zip", tmp_path / "update.zip", progress_cb=progress, cancelled=lambda: cancelled)

    assert not (tmp_path / "update.zip.part").exists()


def test_update_reuses_verified_download(monkeypatch, tmp_path: Path):
    release = UpdateRelease("1.4.2", "v1.4.2", "update.zip", "zip", "update.zip.sha256", "sha", "page")
    update_dir = tmp_path / "updates" / "v1.4.2"
    update_dir.mkdir(parents=True)
    archive = update_dir / release.zip_name
    archive.write_bytes(b"ready")
    (update_dir / release.sha_name).write_text(f"{hashlib.sha256(b'ready').hexdigest()}  update.zip\n")
    monkeypatch.setattr("hpc_gui.services.app_updater.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("hpc_gui.services.app_updater._download", lambda *_args, **_kwargs: pytest.fail("must reuse archive"))

    assert download_and_verify_release(release) == archive


def test_closing_update_progress_cancels_active_download():
    class Worker:
        cancelled = False

        def cancel(self):
            self.cancelled = True

    worker = Worker()
    closed = False

    def close():
        nonlocal closed
        closed = True

    window = SimpleNamespace(_update_cancelled=False, _update_workers={object(): worker}, _close_update_progress=close)
    MainWindow._cancel_update_jobs(window)

    assert worker.cancelled and window._update_cancelled and closed


def test_release_assets_are_platform_specific():
    assert release_asset_names("windows_x86_64")[0].endswith(".zip")
    assert release_asset_names("macos_arm64")[0].endswith("_arm64.dmg")
    assert release_asset_names("macos_x86_64")[0].endswith("_x86_64.dmg")
    assert release_asset_names("linux_x86_64") is None


def test_unknown_update_platform_is_rejected():
    with pytest.raises(RuntimeError, match="Unsupported update platform"):
        release_asset_names("macos_ppc64")


def test_macos_never_launches_windows_installer(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("hpc_gui.services.app_updater.current_os", lambda: "macos")

    with pytest.raises(RuntimeError, match="only on Windows"):
        launch_update_installer(tmp_path / "update.dmg", "1.5.0")
