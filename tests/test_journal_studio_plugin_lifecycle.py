from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest


def _entry(package: Path, version: str):
    manifest_bytes = (package / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    return {
        "id": manifest["id"],
        "name": manifest["name"],
        "version": version,
        "plugin_api": manifest["plugin_api"],
        "type": "application-tools",
        "description": manifest["description"],
        "publisher": manifest["publisher"],
        "requires_app": manifest["requires_app"],
        "manifest_path": f"plugins/ansys-journal-studio/{version}/manifest.json",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "official": False,
        "capabilities": manifest["capabilities"],
        "keywords": ["ANSYS", "Fluent", "journal"],
    }, manifest_bytes


def test_real_installer_update_rollback_disable_enable_and_remove(tmp_path):
    package_value = os.environ.get("HPC_JOURNAL_STUDIO_PACKAGE")
    if not package_value:
        pytest.skip("VM acceptance supplies HPC_JOURNAL_STUDIO_PACKAGE")
    package_v1 = Path(package_value).resolve()
    assert (package_v1 / "manifest.json").is_file()
    package_v2 = tmp_path / "package-v2"
    shutil.copytree(package_v1, package_v2)
    manifest = json.loads((package_v2 / "manifest.json").read_text(encoding="utf-8"))
    manifest["version"] = "0.1.1"
    (package_v2 / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    packages = {"0.1.0": package_v1, "0.1.1": package_v2}
    metadata = {version: _entry(package, version) for version, package in packages.items()}

    def fetcher(url, max_bytes):
        for version, (entry, manifest_bytes) in metadata.items():
            base = f"plugins/ansys-journal-studio/{version}/"
            if base not in url:
                continue
            relative = url.split(base, 1)[1]
            if relative == "manifest.json":
                payload = manifest_bytes
            else:
                payload = (packages[version] / relative).read_bytes()
            assert len(payload) <= max_bytes
            return payload
        raise AssertionError(f"unexpected installer URL: {url}")

    from hpc_gui.plugins.installer import install_plugin_from_registry
    from hpc_gui.plugins.loader import load_installed_plugins
    from hpc_gui.plugins.state import activate_version, read_installed_state, remove_plugin, set_plugin_disabled
    from hpc_gui.plugins.storage import read_active_versions

    root = tmp_path / "isolated-plugin-root"
    plugin_id = "org.hpcclient.ansysjournalstudio"
    for version in ("0.1.0", "0.1.1"):
        entry, _manifest_bytes = metadata[version]
        result = install_plugin_from_registry(entry, root=root, fetcher=fetcher)
        assert result.activated
        assert result.installed.manifest.id == plugin_id
        assert result.installed.directory.joinpath("data/command_registry.json").is_file()
    assert read_active_versions(root)[plugin_id] == "0.1.1"
    assert set(read_installed_state(root)[plugin_id]["versions"]) == {"0.1.0", "0.1.1"}

    activate_version(plugin_id, "0.1.0", root=root)
    assert read_active_versions(root)[plugin_id] == "0.1.0"
    set_plugin_disabled(plugin_id, True, root=root)
    assert all(item.manifest.id != plugin_id for item in load_installed_plugins(root=root).plugins)
    set_plugin_disabled(plugin_id, False, root=root)
    active = next(item for item in load_installed_plugins(root=root).plugins if item.manifest.id == plugin_id)
    assert active.manifest.version == "0.1.0"
    assert active.plugin_menu_contribution is not None

    assert set(remove_plugin(plugin_id, root=root)) == {"0.1.0", "0.1.1"}
    assert plugin_id not in read_active_versions(root)
    assert plugin_id not in read_installed_state(root)
