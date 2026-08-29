"""Local integrity re-validation tests (installed.json trust anchors).

Covers: clean restart, modified payload, modified manifest, missing file,
unexpected extra file, legacy-record TOFU migration, atomic-write failure,
healthy-plugin isolation, and rollback from a corrupt newest version.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.integrity import (
    IntegrityError,
    ensure_trusted_hash,
    migrate_legacy_records,
    verify_installed_version,
)
from hpc_gui.plugins.installer import install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.state import activate_version, read_active_versions, read_installed_state
from hpc_gui.plugins.storage import (
    INSTALLED_INDEX_NAME,
    packages_dir,
    plugin_package_dir,
    plugins_root,
    write_active_versions,
)
from test_plugin_installer import make_fetcher, make_plugin_files, make_registry_entry


def install(tmp_path: Path, plugin_id: str = "org.hpcclient.truba", version: str = "1.0.0"):
    """Install one synthetic plugin into tmp_path through the real installer."""
    manifest, manifest_bytes, profile_bytes = make_plugin_files(
        plugin_id=plugin_id, version=version
    )
    entry = make_registry_entry(manifest, manifest_bytes)
    base = f"plugins/{plugin_id.split('.')[-1]}/{version}"
    raw_base = "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/"
    responses = {
        raw_base + entry["manifest_path"]: manifest_bytes,
        raw_base + base + "/cluster-profile.json": profile_bytes,
    }
    install_plugin_from_registry(entry, root=tmp_path, app_version="1.4.1", fetcher=make_fetcher(responses))


def test_clean_restart_records_trusted_hash_and_loads(tmp_path: Path):
    install(tmp_path)
    state = read_installed_state(tmp_path)
    record = state["org.hpcclient.truba"]
    assert hashlib.sha256(
        (packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0" / "manifest.json").read_bytes()
    ).hexdigest() == record["manifest_hashes"]["1.0.0"]

    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert not loaded.problems
    assert [p.manifest.version for p in loaded.plugins] == ["1.0.0"]


def test_modified_payload_skips_plugin_with_reinstall_hint(tmp_path: Path):
    install(tmp_path)
    payload = plugin_package_dir("org.hpcclient.truba", "1.0.0", tmp_path) / "cluster-profile.json"
    data = json.loads(payload.read_text(encoding="utf-8"))
    data["commands"]["status_command"] = "tampered"
    payload.write_text(json.dumps(data), encoding="utf-8")

    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert loaded.plugins == []
    assert len(loaded.problems) == 1
    problem = loaded.problems[0]
    assert problem.plugin_id == "org.hpcclient.truba"
    assert "integrity check failed" in problem.reason
    assert "reinstall" in problem.reason


def test_modified_manifest_detected_against_trusted_hash(tmp_path: Path):
    install(tmp_path)
    manifest_path = plugin_package_dir("org.hpcclient.truba", "1.0.0", tmp_path) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["description"] = "Tampered description"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = verify_installed_version("org.hpcclient.truba", "1.0.0", root=tmp_path)
    assert any("hash mismatch" in error for error in errors)

    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert loaded.plugins == []
    assert loaded.problems and "integrity check failed" in loaded.problems[0].reason


def test_missing_payload_file_detected(tmp_path: Path):
    install(tmp_path)
    (plugin_package_dir("org.hpcclient.truba", "1.0.0", tmp_path) / "cluster-profile.json").unlink()
    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert loaded.plugins == []
    assert "missing payload file" in loaded.problems[0].reason


def test_unexpected_extra_file_rejected(tmp_path: Path):
    install(tmp_path)
    extra = plugin_package_dir("org.hpcclient.truba", "1.0.0", tmp_path) / "extra.txt"
    extra.write_text("undeclared", encoding="utf-8")
    errors = verify_installed_version("org.hpcclient.truba", "1.0.0", root=tmp_path)
    assert any("unexpected extra file" in error for error in errors)


def test_legacy_record_tofu_migration_is_atomic_and_marked(tmp_path: Path):
    install(tmp_path)
    # Downgrade the record to the legacy v1 layout (no hashes, no flags).
    state = read_installed_state(tmp_path)
    legacy = {
        "schema_version": 1,
        "plugins": {
            pid: {"versions": rec["versions"], "installed_at": rec["installed_at"]}
            for pid, rec in state.items()
        },
    }
    index = plugins_root(tmp_path) / INSTALLED_INDEX_NAME
    index.write_text(json.dumps(legacy), encoding="utf-8")
    assert read_installed_state(tmp_path)["org.hpcclient.truba"]["manifest_hashes"] == {}

    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert not loaded.problems
    assert [p.manifest.version for p in loaded.plugins] == ["1.0.0"]

    migrated_state = read_installed_state(tmp_path)
    record = migrated_state["org.hpcclient.truba"]
    assert record["migrated"] == ["1.0.0"]
    assert len(record["manifest_hashes"]["1.0.0"]) == 64

    # Migration also works standalone without loading.
    other = tmp_path / "other-root"
    other.mkdir()
    install(other)
    fresh = read_installed_state(root=other)
    legacy_other = {
        "schema_version": 1,
        "plugins": {
            pid: {"versions": rec["versions"], "installed_at": rec["installed_at"]}
            for pid, rec in fresh.items()
        },
    }
    (plugins_root(other) / INSTALLED_INDEX_NAME).write_text(
        json.dumps(legacy_other), encoding="utf-8"
    )
    migrated = migrate_legacy_records(root=other)
    assert ("org.hpcclient.truba", "1.0.0") in migrated


def test_tofu_migration_refuses_tampered_legacy_files(tmp_path: Path):
    install(tmp_path)
    state = read_installed_state(tmp_path)
    legacy = {
        "schema_version": 1,
        "plugins": {
            pid: {"versions": rec["versions"], "installed_at": rec["installed_at"]}
            for pid, rec in state.items()
        },
    }
    (plugins_root(tmp_path) / INSTALLED_INDEX_NAME).write_text(json.dumps(legacy), encoding="utf-8")
    payload = plugin_package_dir("org.hpcclient.truba", "1.0.0", tmp_path) / "cluster-profile.json"
    payload.write_text("{}\n", encoding="utf-8")

    with pytest.raises(IntegrityError):
        ensure_trusted_hash("org.hpcclient.truba", "1.0.0", root=tmp_path)
    # Nothing was trusted or written.
    assert read_installed_state(tmp_path)["org.hpcclient.truba"]["manifest_hashes"] == {}


def test_atomic_write_failure_keeps_previous_state(tmp_path: Path, monkeypatch):
    install(tmp_path)
    # Downgrade to a legacy record so loading triggers a TOFU write.
    state = read_installed_state(tmp_path)
    legacy = {
        "schema_version": 1,
        "plugins": {
            pid: {"versions": rec["versions"], "installed_at": rec["installed_at"]}
            for pid, rec in state.items()
        },
    }
    index = plugins_root(tmp_path) / INSTALLED_INDEX_NAME
    index.write_text(json.dumps(legacy), encoding="utf-8")

    from hpc_gui.plugins import state as state_module

    monkeypatch.setattr(
        state_module,
        "_atomic_write_json",
        lambda path, payload: (_ for _ in ()).throw(OSError("disk full")),
    )

    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    # The write failure must not crash loading nor corrupt the old index.
    assert [p.manifest.version for p in loaded.plugins] == ["1.0.0"]
    on_disk = json.loads((plugins_root(tmp_path) / INSTALLED_INDEX_NAME).read_text(encoding="utf-8"))
    assert "manifest_hashes" not in on_disk["plugins"]["org.hpcclient.truba"]


def test_broken_plugin_skipped_while_healthy_plugin_loads(tmp_path: Path):
    install(tmp_path, plugin_id="org.hpcclient.healthy", version="1.0.0")
    install(tmp_path, plugin_id="org.hpcclient.broken", version="2.0.0")
    broken_payload = (
        plugin_package_dir("org.hpcclient.broken", "2.0.0", tmp_path) / "cluster-profile.json"
    )
    broken_payload.write_text("{}", encoding="utf-8")
    # Both are installed; only healthy stays active.
    write_active_versions({"org.hpcclient.broken": "2.0.0"}, root=tmp_path)

    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert [p.manifest.id for p in loaded.plugins] == []
    assert {p.plugin_id for p in loaded.problems} == {"org.hpcclient.broken"}

    write_active_versions(
        {"org.hpcclient.broken": "2.0.0", "org.hpcclient.healthy": "1.0.0"}, root=tmp_path
    )
    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert [p.manifest.id for p in loaded.plugins] == ["org.hpcclient.healthy"]
    assert [p.plugin_id for p in loaded.problems] == ["org.hpcclient.broken"]
    # Broken plugin was never deleted.
    assert (broken_payload.parent / "manifest.json").is_file()


def test_rollback_from_corrupt_newest_to_intact_older_version(tmp_path: Path):
    install(tmp_path, version="1.9.0")
    install(tmp_path, version="1.10.0")  # newest, now active
    assert read_active_versions(tmp_path)["org.hpcclient.truba"] == "1.10.0"

    newest_payload = (
        plugin_package_dir("org.hpcclient.truba", "1.10.0", tmp_path) / "cluster-profile.json"
    )
    newest_payload.write_text("corrupted", encoding="utf-8")

    # Loading skips the corrupt active version...
    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert loaded.plugins == []

    # ...but manual rollback to the intact older version succeeds.
    activate_version("org.hpcclient.truba", "1.9.0", root=tmp_path)
    assert read_active_versions(tmp_path)["org.hpcclient.truba"] == "1.9.0"
    loaded = load_installed_plugins(root=tmp_path, app_version="1.4.1")
    assert [p.manifest.version for p in loaded.plugins] == ["1.9.0"]
    # The corrupt newer version is still installed, never auto-deleted.
    assert "1.10.0" in read_installed_state(tmp_path)["org.hpcclient.truba"]["versions"]
