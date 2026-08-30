from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
from hpc_gui.plugins.validator import validate_manifest_dict
from hpc_gui.services import process_registry
from hpc_gui.services.xserver_manager import _vcxsrv_args


def test_process_registry_never_persists_password(tmp_path: Path):
    target = tmp_path / "processes.json"
    with patch("hpc_gui.services.process_registry._registry_path", return_value=target):
        process_registry.register(123, kind="x11_plink", cmd="plink -pw FakeX11Password host")
    assert "FakeX11Password" not in target.read_text(encoding="utf-8")


def test_x11_launch_has_separate_safe_display_args():
    from hpc_gui.services import x11_system_ssh

    with patch.object(x11_system_ssh.platform, "system", return_value="Windows"), patch.object(
        x11_system_ssh, "_find_plink_program", return_value="plink.exe"
    ):
        launch = x11_system_ssh.build_x11_launch("host", 22, "user", "xclock", password="FakeX11Password")
    assert launch.args[launch.args.index("-pw") + 1] == "FakeX11Password"
    assert launch.display_args[launch.display_args.index("-pw") + 1] == "<redacted>"


def test_python_plugin_payload_and_legacy_engine_fail_closed(tmp_path: Path):
    marker = tmp_path / "executed"
    manifest = {
        "schema_version": 1, "plugin_api": 2, "id": "org.example.bad", "name": "bad",
        "version": "1.0.0", "publisher": "test", "license": "MIT", "description": "bad",
        "requires_app": ">=1.0.0", "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/__init__.py"},
        "files": [{"path": "engine/__init__.py", "sha256": "a" * 64, "size": 1, "role": "linter-engine"}],
    }
    assert validate_manifest_dict(manifest)
    with pytest.raises(ToolLoadError, match="disabled|declarative"):
        load_tool_for_plugin(type("Installed", (), {"directory": tmp_path, "manifest": type("M", (), {"id": "x", "version": "1"})()})())
    assert not marker.exists()


def test_plugin_runtime_has_no_dynamic_source_execution():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/hpc_gui/plugins").glob("*.py")
    )
    for forbidden in ("spec_from_file_location", "exec_module(", "create_plugin("):
        assert forbidden not in source


def test_unknown_declarative_engine_id_fails_closed():
    manifest = {
        "schema_version": 1, "plugin_api": 1, "id": "org.example.rules", "name": "rules",
        "version": "1.0.0", "publisher": "test", "license": "MIT", "description": "rules",
        "requires_app": ">=1.0.0", "capabilities": ["lint-rules"],
        "entrypoints": {"engine": "python-anything"},
        "files": [{"path": "rules.json", "sha256": "a" * 64, "size": 1, "role": "lint-rules"}],
    }
    assert any("unknown declarative engine" in error for error in validate_manifest_dict(manifest))


def test_vcxsrv_does_not_disable_access_control():
    assert "-ac" not in _vcxsrv_args(Path("vcxsrv.exe"), 0)


def test_provider_substitution_is_shell_quoted():
    from hpc_gui.services.slurm_ssh import SSHSlurmBackend

    backend = SSHSlurmBackend(type("SSH", (), {})(), {"squeue_command": "squeue -u {user}"})
    assert backend._command("squeue_command", user="user; touch marker") == "squeue -u 'user; touch marker'"


def test_plugin_paths_reject_traversal_and_windows_forms():
    from hpc_gui.plugins.models import is_safe_relative_path

    for path in ("../x.json", "%2e%2e/x.json", "..\\x.json", "C:/x.json", "//server/x.json"):
        assert not is_safe_relative_path(path)


def test_plugin_integrity_rejects_symlink_escape(tmp_path: Path):
    import hashlib
    from hpc_gui.plugins.integrity import verify_version_dir

    package = tmp_path / "package"
    package.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("safe", encoding="utf-8")
    link = package / "README.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    manifest = {
        "schema_version": 1, "plugin_api": 1, "id": "org.example.safe", "name": "safe",
        "version": "1.0.0", "publisher": "test", "license": "MIT", "description": "safe",
        "requires_app": ">=1.0.0", "capabilities": ["cluster-profile"], "entrypoints": {},
        "files": [{"path": "README.md", "sha256": hashlib.sha256(b"safe").hexdigest(), "size": 4, "role": "documentation"}],
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert any("symlink" in error for error in verify_version_dir(package))


def test_update_download_rejects_untrusted_final_redirect(monkeypatch, tmp_path: Path):
    from hpc_gui.services.app_updater import _download

    class Response:
        headers = {"Content-Length": "0"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self):
            return "https://evil.example/update.zip"

        def read(self, _size):
            return b""

    monkeypatch.setattr("hpc_gui.services.app_updater._request", lambda *_a, **_k: Response())
    with pytest.raises(Exception, match="host"):
        _download("https://github.com/x/update.zip", tmp_path / "update.zip", verify_update_host=True)


def test_unverified_download_cannot_reach_installer(monkeypatch, tmp_path: Path):
    from hpc_gui.services import app_updater

    payload = tmp_path / "downloaded.exe"
    payload.write_bytes(b"unverified")
    monkeypatch.setattr(app_updater, "is_frozen_exe", lambda: True)
    with pytest.raises(RuntimeError, match="authenticated"):
        app_updater.launch_update_installer(payload, "9.9.9")


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_sensitive_config_file_is_owner_only(tmp_path: Path):
    from hpc_gui.config import storage

    target = tmp_path / "config.json"
    with patch("hpc_gui.config.storage._config_path", return_value=target):
        storage.save_config({"profiles": []})
    assert target.stat().st_mode & 0o777 == 0o600
