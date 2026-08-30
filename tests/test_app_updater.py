import hashlib
import base64
import inspect
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.services import app_updater
from hpc_gui.services.app_updater import (
    UpdateRelease,
    _download,
    build_update_script,
    download_and_verify_release,
    launch_update_installer,
    parse_release_security,
    release_asset_names,
)
from hpc_gui.services.installation_context import InstallationContext
from hpc_gui.ui.main_window import MainWindow
from hpc_gui.ui.splash_screen import UpdateSplash


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


def test_download_reports_transferred_and_total_bytes(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("hpc_gui.services.app_updater._request", lambda *_args, **_kwargs: _Response())
    progress = []

    _download("https://example.invalid/update.zip", tmp_path / "update.zip", progress_cb=lambda *args: progress.append(args))

    assert progress[-1] == (100, "", 2, 2)


def test_download_percentage_is_actual_package_percentage(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("hpc_gui.services.app_updater._request", lambda *_args, **_kwargs: _Response())
    progress = []

    _download("https://example.invalid/update.zip", tmp_path / "update.zip", progress_cb=lambda *args: progress.append(args))

    assert progress[0] == (50, "", 1, 2)
    assert progress[1] == (100, "", 2, 2)


def test_unknown_content_length_reports_bytes_without_fake_percentage(monkeypatch, tmp_path: Path):
    class UnknownLength(_Response):
        headers = {}

    monkeypatch.setattr("hpc_gui.services.app_updater._request", lambda *_args, **_kwargs: UnknownLength())
    progress = []

    _download("https://example.invalid/update.zip", tmp_path / "update.zip", progress_cb=lambda *args: progress.append(args))

    assert progress[0] == (0, "", 1, 0)
    assert progress[-1] == (100, "", 2, 0)


def test_update_reuses_verified_download(monkeypatch, tmp_path: Path):
    release = UpdateRelease(
        "1.4.2", "v1.4.2", "update.zip", "zip", "update.zip.sha256", "sha", "page",
        signed_artifact={"size": 5, "sha256": hashlib.sha256(b"ready").hexdigest(), "url": "https://github.com/x/update.zip"},
    )
    update_dir = tmp_path / "updates" / "v1.4.2"
    update_dir.mkdir(parents=True)
    archive = update_dir / release.zip_name
    archive.write_bytes(b"ready")
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


def test_manual_update_check_shows_splash_before_worker_starts():
    source = inspect.getsource(MainWindow).split("def _check_for_updates", 1)[1]
    source = source.split("def _on_release_checked", 1)[0]
    assert source.index("_show_update_progress") < source.index("_run_update_job")


def test_update_splash_formats_binary_units():
    assert UpdateSplash._format_bytes(1024) == "1.0 KB"
    assert UpdateSplash._format_bytes(1024**2) == "1.0 MB"
    assert UpdateSplash._format_bytes(1024**3) == "1.0 GB"


def test_release_assets_are_platform_specific():
    assert release_asset_names("windows_x86_64")[0].endswith(".zip")
    assert release_asset_names("macos_arm64")[0].endswith("_arm64.dmg")
    assert release_asset_names("macos_x86_64")[0].endswith("_x86_64.dmg")
    assert release_asset_names("linux_x86_64", "source", "1.5.6") is None
    assert release_asset_names("linux_x86_64", "linux-appimage", "1.5.6")[0].endswith("x86_64.AppImage")
    assert release_asset_names("linux_x86_64", "linux-deb", "1.5.6")[0].endswith("_amd64.deb")
    assert release_asset_names("linux_x86_64", "linux-flatpak", "1.5.6")[0].endswith(".flatpak")


def test_unknown_update_platform_is_rejected():
    with pytest.raises(RuntimeError, match="Unsupported update platform"):
        release_asset_names("macos_ppc64")


def test_unpackaged_app_never_launches_installer(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("hpc_gui.services.app_updater.current_os", lambda: "macos")

    with pytest.raises(RuntimeError, match="packaged app"):
        launch_update_installer(tmp_path / "update.dmg", "1.5.0")


def test_install_handoff_never_shows_complete_before_helper_starts():
    source = Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")
    handoff = source[source.index("def _on_update_downloaded"):source.index("def _on_update_error")]
    assert '_show_update_progress(100, "installing")' not in handoff
    assert '_show_update_progress(0, "preparing")' in handoff


def test_appimage_handoff_runs_helper_from_verified_new_image(monkeypatch, tmp_path: Path):
    current = tmp_path / "current.AppImage"
    package = tmp_path / "new.AppImage"
    current.write_bytes(b"old")
    package.write_bytes(b"new")
    context = InstallationContext(
        "appimage", "APPIMAGE", current, "hpc-client-gui", "1.0", "x86_64",
        "linux-appimage", "identified",
    )
    commands = []

    def popen(command, **_kwargs):
        commands.append(command)
        Path(command[-1]).with_suffix(".ready").write_text("ready", encoding="ascii")
        return SimpleNamespace()

    monkeypatch.setattr(app_updater, "is_frozen_exe", lambda: True)
    monkeypatch.setattr(app_updater, "current_os", lambda: "linux")
    monkeypatch.setattr(app_updater, "detect_installation", lambda: context)
    monkeypatch.setattr(app_updater.subprocess, "Popen", popen)
    app_updater._VERIFIED_UPDATE_ARTIFACTS[package.resolve()] = {
        "size": 3, "sha256": hashlib.sha256(b"new").hexdigest()
    }
    launch_update_installer(package, "2.0", "linux-appimage")
    assert commands[0][:2] == [str(package.resolve()), "--updater-helper"]


def test_updater_selects_arch_specific_dmg_per_platform():
    # arm64 DMG only for Apple Silicon, x86_64 only for Intel Mac.
    assert release_asset_names("macos_arm64")[0] == "hpc-client-gui_macos_arm64.dmg"
    assert release_asset_names("macos_x86_64")[0] == "hpc-client-gui_macos_x86_64.dmg"
    assert "dmg" not in release_asset_names("windows_x86_64")[0]
    assert release_asset_names("linux_x86_64", "source", "1.5.6") is None


def test_security_metadata_parsing_matches_modes():
    signed = {
        "macos_mode": "signed-notarized",
        "developer_id_verification_passed": True,
        "notarization_passed": True,
        "stapling_passed": True,
        "gatekeeper_assessment_passed": True,
    }
    assert parse_release_security(signed) == app_updater.SECURITY_SIGNED
    assert parse_release_security({"macos_mode": "unsigned"}) == app_updater.SECURITY_UNSIGNED
    assert parse_release_security(None) == app_updater.SECURITY_UNKNOWN
    assert parse_release_security({}) == app_updater.SECURITY_UNKNOWN
    # Signing claimed without verification is unknown, never signed.
    unverified = dict(signed, developer_id_verification_passed=False)
    assert parse_release_security(unverified) == app_updater.SECURITY_UNKNOWN


def test_missing_security_metadata_defaults_to_unknown():
    release = UpdateRelease("1.5.1", "v1.5.1", "a.zip", "u", "a.sha256", "s", "page")
    assert release.security_status == app_updater.SECURITY_UNKNOWN


def test_unknown_installation_is_manual_only():
    context = InstallationContext("unknown", "test", None, "", "", "x86_64", "unsupported", "not identified")
    assert context.capability == "unsupported"


def test_windows_installer_script_has_independent_real_progress_and_rollback(tmp_path: Path):
    script = build_update_script(
        zip_path=tmp_path / "update.zip",
        install_dir=tmp_path / "app",
        current_exe=tmp_path / "app" / "hpc-client-gui.exe",
        new_version="1.5.6",
        process_id=42,
    )

    assert "System.Windows.Forms.Form" in script
    assert "$extractDone += $read" in script
    assert "$copyDone += $read" in script
    assert "[Math]::Max($script:lastProgress" in script
    assert "Rollback started" in script
    assert "New process healthy" in script
    assert "Copy-Item -Path (Join-Path $stagingDir" not in script

    if os.name == "nt":
        encoded = base64.b64encode(script.encode()).decode()
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "[scriptblock]::Create([Text.Encoding]::UTF8.GetString("
                f"[Convert]::FromBase64String('{encoded}'))) | Out-Null",
            ],
            check=True,
        )
