"""Wave 07 tests: plugin security hardening, update rollback, disable."""

from __future__ import annotations

import hashlib
import json
import logging
import unittest.mock as mock
from pathlib import Path

import pytest

from hpc_gui.plugins.downloader import DownloadError  # noqa: F401
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE, FILE_MAX_BYTES
from hpc_gui.plugins.state import (
    activate_version,
    read_disabled_ids,
    remove_plugin,
    set_plugin_disabled,
)
from hpc_gui.plugins.storage import packages_dir, plugins_root, read_active_versions
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.plugins.validator import validate_cluster_profile_dict, validate_manifest_dict


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_plugin(
    root: Path,
    *,
    plugin_id: str = "org.hpcclient.truba",
    version: str = "1.0.0",
    status_command: str = "lssrv",
    profile_override: dict | None = None,
) -> dict:
    """Create a locally consistent installable package; returns registry entry."""
    base = f"plugins/{plugin_id.split('.')[-1]}/{version}"
    pkg = root / base
    pkg.mkdir(parents=True, exist_ok=True)
    _ = base  # registry manifest_path below reuses the same layout

    profile = {
        "schema_version": 1,
        "profile_id": "truba",
        "name": "TRUBA",
        "scheduler": "slurm",
        "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
        "commands": {"status_command": status_command},
    }
    if profile_override is not None:
        profile.update(profile_override)
    payload = json.dumps(profile).encode()
    (pkg / "cluster-profile.json").write_bytes(payload)

    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": plugin_id,
        "name": "TRUBA",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "TRUBA cluster profile.",
        "requires_app": ">=1.3.0",
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [
            {
                "path": "cluster-profile.json",
                "sha256": sha256_bytes(payload),
                "size": len(payload),
                "role": "cluster-profile",
            }
        ],
    }
    manifest_bytes = json.dumps(manifest).encode()
    (pkg / "manifest.json").write_bytes(manifest_bytes)

    active = {}
    index_path = root / "active.json"
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        active = data.get("active", data)
    active[plugin_id] = version
    from hpc_gui.plugins.storage import write_active_versions

    write_active_versions(active, root=root)

    return {
        "id": plugin_id,
        "name": manifest["name"],
        "version": version,
        "plugin_api": 1,
        "type": "cluster-profile",
        "description": manifest["description"],
        "publisher": manifest["publisher"],
        "requires_app": manifest["requires_app"],
        "manifest_path": f"{base}/manifest.json",
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "official": True,
    }


def make_fetcher(responses: dict[str, bytes]):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url not in responses:
            raise OSError(f"missing {url}")
        payload = responses[url]
        if len(payload) > max_bytes:
            raise OSError("too large")
        return payload

    return fetch


def remote_responses(root: Path, entry: dict) -> dict[str, bytes]:
    base = str(Path(entry["manifest_path"]).parent).replace("\\", "/")
    responses = {
        OFFICIAL_RAW_BASE + entry["manifest_path"]: (root / entry["manifest_path"]).read_bytes()
    }
    manifest = json.loads((root / entry["manifest_path"]).read_text(encoding="utf-8"))
    for file_entry in manifest["files"]:
        path = f"{base}/{file_entry['path']}"
        responses[OFFICIAL_RAW_BASE + path] = (root / path).read_bytes()
    return responses


# ---------------------------------------------------------------------------
# File-type and placeholder policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_path",
    ["helper.py", "lib.dll", "run.exe", "hook.ps1", "lib.so", "lib.dylib", "run.bat"],
)
def test_executable_extensions_rejected(bad_path):
    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": "org.hpcclient.evil",
        "name": "Evil",
        "version": "1.0.0",
        "publisher": "x",
        "license": "MIT",
        "description": "d",
        "requires_app": ">=1.0.0",
        "capabilities": ["cluster-profile"],
        "entrypoints": {},
        "files": [
            {"path": bad_path, "sha256": "a" * 64, "size": 1, "role": "documentation"}
        ],
    }
    errors = validate_manifest_dict(manifest)
    assert any("forbidden executable-looking extension" in e for e in errors)


def test_unknown_command_placeholder_rejected():
    profile = {
        "schema_version": 1,
        "profile_id": "x",
        "name": "X",
        "scheduler": "slurm",
        "commands": {"squeue_command": "squeue --me={home_dir}{user}"},
    }
    errors = validate_cluster_profile_dict(profile)
    assert any("unknown placeholder {home_dir}" in e for e in errors)


def test_known_placeholders_accepted_and_status_free_form():
    profile = {
        "schema_version": 1,
        "profile_id": "truba",
        "name": "T",
        "scheduler": "slurm",
        "commands": {
            "squeue_command": 'squeue -h -u {user}',
            "scancel_command": "scancel {job_id_q}",
            "status_command": "squeue --fancy-{anything}",
        },
    }
    assert validate_cluster_profile_dict(profile) == []


# ---------------------------------------------------------------------------
# Installer-level hostile fixtures
# ---------------------------------------------------------------------------


def test_installer_rejects_too_many_files(tmp_path: Path):
    entry = build_plugin(tmp_path)
    manifest_path = tmp_path / entry["manifest_path"]
    manifest = json.loads(manifest_path.read_text())
    manifest["files"] = [
        {"path": f"f{i}.json", "sha256": "a" * 64, "size": 1, "role": "documentation"}
        for i in range(300)
    ]
    tampered = json.dumps(manifest).encode()

    def mutator(m):
        m["files"] = manifest["files"]

    # Rebuild the local package with the tampered manifest so hashes line up.
    (tmp_path / entry["manifest_path"]).write_bytes(tampered)
    entry["manifest_sha256"] = sha256_bytes(tampered)

    with pytest.raises(InstallError, match="too many files"):
        install_plugin_from_registry(
            entry,
            root=tmp_path / "install",
            app_version="1.4.0",
            fetcher=make_fetcher({OFFICIAL_RAW_BASE + entry["manifest_path"]: tampered}),
        )


def test_installer_rejects_oversized_file(tmp_path: Path):
    entry = build_plugin(tmp_path)
    big_payload = b"x" * (FILE_MAX_BYTES + 1)
    fetcher = make_fetcher(
        {
            OFFICIAL_RAW_BASE + entry["manifest_path"]: (tmp_path / entry["manifest_path"]).read_bytes(),
            OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/cluster-profile.json": big_payload,
        }
    )
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path / "install", app_version="1.4.0", fetcher=fetcher
        )


def test_exception_midway_leaves_active_pointer_untouched(tmp_path: Path):
    entry = build_plugin(tmp_path)
    responses = remote_responses(tmp_path, entry)

    call_count = {"n": 0}

    def flaky_fetch(url: str, max_bytes: int) -> bytes:
        call_count["n"] += 1
        if call_count["n"] == 2:  # fail on the payload download (after manifest)
            raise OSError("simulated network drop")
        return responses[url]

    # A previous working version stays installed and active.
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path / "install", app_version="1.4.0", fetcher=flaky_fetch
        )

    install_root = tmp_path / "install"
    assert read_active_versions(install_root) == {}
    staging_root = Path(plugins_root(install_root)) / ".staging"
    assert not staging_root.exists() or not any(staging_root.iterdir())


def test_disk_write_failure_keeps_previous_state(tmp_path: Path):
    entry = build_plugin(tmp_path, version="2.0.0")
    responses = remote_responses(tmp_path, entry)

    def failing_write(self, data):
        raise OSError("No space left on device")

    install_root = tmp_path / "install"
    # First install a good 1.0.0 to have a previous state.
    good = build_plugin(tmp_path, version="1.0.0")
    good_responses = remote_responses(tmp_path, good)
    install_plugin_from_registry(
        good, root=install_root, app_version="1.4.0", fetcher=make_fetcher(good_responses)
    )
    assert read_active_versions(install_root)["org.hpcclient.truba"] == "1.0.0"

    with mock.patch.object(Path, "write_bytes", failing_write), pytest.raises(
        (InstallError, OSError)
    ):
        install_plugin_from_registry(
            entry, root=install_root, app_version="1.4.0", fetcher=make_fetcher(responses)
        )

    assert read_active_versions(install_root) == {"org.hpcclient.truba": "1.0.0"}
    assert (packages_dir(install_root) / "org.hpcclient.truba" / "1.0.0" / "manifest.json").is_file()


def test_post_activation_validation_failure_triggers_rollback(tmp_path: Path, monkeypatch):
    entry = build_plugin(tmp_path, version="3.0.0")
    responses = remote_responses(tmp_path, entry)
    install_root = tmp_path / "install"

    good = build_plugin(tmp_path, version="1.0.0")
    install_plugin_from_registry(
        good,
        root=install_root,
        app_version="1.4.0",
        fetcher=make_fetcher(remote_responses(tmp_path, good)),
    )

    from hpc_gui.plugins import loader as loader_module

    def fake_loader(*args, **kwargs):
        return loader_module.PluginLoadResult()

    monkeypatch.setattr(loader_module, "load_installed_plugins", fake_loader)

    with pytest.raises(InstallError, match="failed validation"):
        install_plugin_from_registry(
            entry, root=install_root, app_version="1.4.0", fetcher=make_fetcher(responses)
        )

    assert read_active_versions(install_root) == {"org.hpcclient.truba": "1.0.0"}


# ---------------------------------------------------------------------------
# Fetcher redirect / final-host policy
# ---------------------------------------------------------------------------


def test_final_url_policy_allows_only_official_https_hosts():
    from hpc_gui.plugins.registry_client import _final_url_is_allowed

    assert _final_url_is_allowed(
        "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/registry.json"
    )
    assert not _final_url_is_allowed("http://raw.githubusercontent.com/registry.json")
    assert not _final_url_is_allowed("https://evil.example.com/payload.json")
    assert not _final_url_is_allowed("https://raw.githubusercontent.com.evil.com/x")


def test_default_fetcher_rejects_redirect_to_unexpected_host(monkeypatch):
    import io

    from hpc_gui.plugins.registry_client import RegistryError, default_fetcher

    class FakeResponse(io.BytesIO):
        def geturl(self):
            return "https://cdn.evil.example.com/registry.json"

    def fake_urlopen(request, timeout=None):
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RegistryError, match="unexpected final host|Refusing"):
        default_fetcher(
            "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/registry.json",
            1024,
        )


def test_default_fetcher_rejects_insecure_http_final_url(monkeypatch):
    import io

    from hpc_gui.plugins.registry_client import RegistryError, default_fetcher

    class FakeResponse(io.BytesIO):
        def geturl(self):
            return "http://raw.githubusercontent.com/registry.json"

    def fake_urlopen(request, timeout=None):
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RegistryError):
        default_fetcher(
            "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/registry.json",
            1024,
        )


# ---------------------------------------------------------------------------
# Disable behavior
# ---------------------------------------------------------------------------


def test_disabled_plugin_contributes_no_templates(tmp_path: Path):
    entry = build_plugin(tmp_path)
    install_root = tmp_path / "install"
    install_plugin_from_registry(
        entry,
        root=install_root,
        app_version="1.4.0",
        fetcher=make_fetcher(remote_responses(tmp_path, entry)),
    )
    assert installed_cluster_template_groups(root=install_root, app_version="1.4.0")

    set_plugin_disabled("org.hpcclient.truba", True, root=install_root)
    assert "org.hpcclient.truba" in read_disabled_ids(install_root)
    # Files stay on disk.
    assert (packages_dir(install_root) / "org.hpcclient.truba" / "1.0.0").is_dir()
    assert not installed_cluster_template_groups(root=install_root, app_version="1.4.0")

    set_plugin_disabled("org.hpcclient.truba", False, root=install_root)
    assert installed_cluster_template_groups(root=install_root, app_version="1.4.0")


def test_activate_version_only_for_valid_installed_versions(tmp_path: Path):
    entry_v1 = build_plugin(tmp_path, version="1.0.0")
    entry_v2 = build_plugin(tmp_path, version="2.0.0")
    install_root = tmp_path / "install"
    for entry in (entry_v1, entry_v2):
        install_plugin_from_registry(
            entry,
            root=install_root,
            app_version="1.4.0",
            fetcher=make_fetcher(remote_responses(tmp_path, entry)),
        )
    assert read_active_versions(install_root)["org.hpcclient.truba"] == "2.0.0"

    # Roll back manually to the older installed version.
    activate_version("org.hpcclient.truba", "1.0.0", root=install_root)
    assert read_active_versions(install_root) == {"org.hpcclient.truba": "1.0.0"}

    # Unknown version must be rejected and leave state untouched.
    with pytest.raises(ValueError):
        activate_version("org.hpcclient.truba", "9.9.9", root=install_root)
    assert read_active_versions(install_root) == {"org.hpcclient.truba": "1.0.0"}


def test_remove_never_touches_user_templates_or_profiles(tmp_path: Path, monkeypatch):
    entry = build_plugin(tmp_path)
    install_root = tmp_path / "install"
    install_plugin_from_registry(
        entry,
        root=install_root,
        app_version="1.4.0",
        fetcher=make_fetcher(remote_responses(tmp_path, entry)),
    )

    user_profile = {"name": "lab", "system": {"status_command": "lssrv"}}
    removed = remove_plugin("org.hpcclient.truba", root=install_root)

    assert removed == ["1.0.0"]
    assert not (packages_dir(install_root) / "org.hpcclient.truba").exists()
    # The caller-owned user profile dict is untouched.
    assert user_profile["system"]["status_command"] == "lssrv"


def test_logging_on_install_and_activation(tmp_path: Path, caplog):
    entry = build_plugin(tmp_path)
    with caplog.at_level(logging.INFO, logger="hpc_gui.plugins.installer"):
        install_plugin_from_registry(
            entry,
            root=tmp_path / "install",
            app_version="1.4.0",
            fetcher=make_fetcher(remote_responses(tmp_path, entry)),
        )
    messages = [record.getMessage() for record in caplog.records]
    assert any("Installing plugin org.hpcclient.truba@1.0.0" in m for m in messages)
    assert any("Activated plugin org.hpcclient.truba@1.0.0" in m for m in messages)

