"""Wave 12 end-to-end clean-user scenario for the plugin ecosystem.

Runs the full lifecycle programmatically against a temporary app-data
root with an injected fetcher (no network, no GUI blocking):

    no plugins -> browse -> install TRUBA -> System Templates ->
    saved snapshot survives removal -> Fluent lint -> atomic update ->
    failed update rolls back.

The SSH/SFTP/Slurm regression suite is the rest of this repository's
test suite, which must stay green alongside this file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.config.system_profile import builtin_system_template_groups
from hpc_gui.lint.engine import lint_text
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE
from hpc_gui.plugins.state import remove_plugin
from hpc_gui.plugins.storage import packages_dir, read_active_versions
from hpc_gui.plugins.templates import installed_cluster_template_groups


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


TRUBA_PROFILE = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {
        "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
        "status_command": "lssrv",
    },
}


def make_registry_and_responses(
    root: Path,
    *,
    truba_version: str = "1.0.0",
    fluent_version: str | None = "0.1.0",
):
    """Build a local registry world: TRUBA cluster profile + Fluent lint."""
    responses: dict[str, bytes] = {}
    plugins_entries = []

    def publish(plugin_id: str, name: str, version: str, kind: str, payload_builder):
        base = f"plugins/{plugin_id.split('.')[-1]}/{version}"
        pkg = root / base
        pkg.mkdir(parents=True, exist_ok=True)
        manifest, extra_files = payload_builder(pkg)
        manifest_bytes = json.dumps(manifest).encode()
        (pkg / "manifest.json").write_bytes(manifest_bytes)
        responses[f"{OFFICIAL_RAW_BASE}{base}/manifest.json"] = manifest_bytes
        for rel, data in extra_files.items():
            responses[f"{OFFICIAL_RAW_BASE}{base}/{rel}"] = data
        entry = {
            "id": plugin_id,
            "name": name,
            "version": version,
            "plugin_api": 1,
            "type": kind,
            "description": f"{name} plugin.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=1.4.0",
            "manifest_path": f"{base}/manifest.json",
            "manifest_sha256": sha256_bytes(manifest_bytes),
            "official": True,
        }
        plugins_entries.append(entry)

    def truba_payload(pkg: Path):
        profile_bytes = json.dumps(TRUBA_PROFILE).encode()
        (pkg / "cluster-profile.json").write_bytes(profile_bytes)
        manifest = {
            "schema_version": 1,
            "plugin_api": 1,
            "id": "org.hpcclient.truba",
            "name": "TRUBA",
            "version": truba_version,
            "publisher": "HPC Client GUI",
            "license": "MIT",
            "description": "TRUBA cluster profile.",
            "requires_app": ">=1.4.0",
            "capabilities": ["cluster-profile"],
            "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
            "files": [
                {
                    "path": "cluster-profile.json",
                    "sha256": sha256_bytes(profile_bytes),
                    "size": len(profile_bytes),
                    "role": "cluster-profile",
                }
            ],
        }
        return manifest, {"cluster-profile.json": profile_bytes}

    def fluent_payload(pkg: Path):
        rule_file = {
            "schema_version": 1,
            "tool": "fluent-journal",
            "rules": [
                {
                    "id": "FLUENT001",
                    "severity": "warning",
                    "message": "Journal does not declare a Fluent TUI version.",
                    "match": {
                        "kind": "required-keyword",
                        "value": "/file/set-tui-version",
                    },
                }
            ],
        }
        rule_bytes = json.dumps(rule_file).encode()
        (pkg / "rules.json").write_bytes(rule_bytes)
        index = {
            "schema_version": 1,
            "tool": "fluent-journal",
            "name": "ANSYS Fluent Journal",
            "file_patterns": ["*.jou"],
            "rules": [],
            "rule_files": [{"path": "rules.json", "sha256": sha256_bytes(rule_bytes)}],
        }
        index_bytes = json.dumps(index).encode()
        (pkg / "lint-index.json").write_bytes(index_bytes)
        manifest = {
            "schema_version": 1,
            "plugin_api": 1,
            "id": "org.hpcclient.fluent",
            "name": "Fluent Journal Lint",
            "version": fluent_version,
            "publisher": "HPC Client GUI",
            "license": "MIT",
            "description": "Fluent journal lint.",
            "requires_app": ">=1.4.0",
            "capabilities": ["lint-rules"],
            "entrypoints": {"lint_index": "lint-index.json"},
            "files": [
                {
                    "path": "rules.json",
                    "sha256": sha256_bytes(rule_bytes),
                    "size": len(rule_bytes),
                    "role": "lint-rules",
                },
                {
                    "path": "lint-index.json",
                    "sha256": sha256_bytes(index_bytes),
                    "size": len(index_bytes),
                    "role": "lint-index",
                },
            ],
        }
        return manifest, {"rules.json": rule_bytes, "lint-index.json": index_bytes}

    publish("org.hpcclient.truba", "TRUBA", truba_version, "cluster-profile", truba_payload)
    if fluent_version:
        publish(
            "org.hpcclient.fluent",
            "Fluent Journal Lint",
            fluent_version,
            "lint-rules",
            fluent_payload,
        )

    registry = {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": {
            "owner": "mskomek",
            "name": "hpc-client-gui-plugins",
            "raw_base": OFFICIAL_RAW_BASE,
        },
        "plugins": plugins_entries,
    }

    def fetch(url: str, max_bytes: int) -> bytes:
        assert url.startswith(OFFICIAL_RAW_BASE)
        return responses[url]

    return registry, fetch


def find_entry(registry: dict, plugin_id: str) -> dict:
    return next(p for p in registry["plugins"] if p["id"] == plugin_id)


def test_full_clean_user_lifecycle(tmp_path: Path, monkeypatch):
    app_root = tmp_path / "app-data"
    app_root.mkdir()

    # Steps 1-3: clean start with zero plugins; Generic Slurm built in.
    result = load_installed_plugins(root=app_root, app_version="1.4.0")
    assert result.plugins == []
    groups = builtin_system_template_groups()
    assert list(groups) == ["Generic Slurm"]

    # Steps 4-6: fetch a (local, injected) official registry and see TRUBA.
    registry, fetch = make_registry_and_responses(tmp_path / "registry-world")
    assert any(p["id"] == "org.hpcclient.truba" for p in registry["plugins"])

    # Step 7: install TRUBA through the exact-file installer.
    install_plugin_from_registry(
        find_entry(registry, "org.hpcclient.truba"),
        root=app_root,
        app_version="1.4.0",
        fetcher=fetch,
    )
    loaded = load_installed_plugins(root=app_root, app_version="1.4.0")
    assert [p.manifest.id for p in loaded.plugins] == ["org.hpcclient.truba"]

    # Steps 8-12: System Templates exposes TRUBA with exact site fields.
    real_loader = __import__(
        "hpc_gui.plugins.loader", fromlist=["load_installed_plugins"]
    ).load_installed_plugins
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(
            "hpc_gui.plugins.templates.load_installed_plugins",
            lambda *a, **k: real_loader(root=app_root, app_version="1.4.0"),
        )
        template_groups = installed_cluster_template_groups(app_version="1.4.0")
    assert "TRUBA" in template_groups
    settings = template_groups["TRUBA"][0].settings
    assert settings["home_dir"] == "/arf/home/{user}"
    assert settings["scratch_dir"] == "/arf/scratch/{user}"
    assert settings["status_command"] == "lssrv"

    # Steps 13-15: saving keeps a resolved snapshot that outlives the plugin.
    saved_profile = {
        "name": "lab",
        "system": dict(settings),
        "system_template_source": dict(template_groups["TRUBA"][0].provenance),
    }
    assert saved_profile["system"]["home_dir"] == "/arf/home/{user}"

    # Steps 16-17: remove the plugin; the saved profile stays intact.
    removed = remove_plugin("org.hpcclient.truba", root=app_root)
    assert removed == ["1.0.0"]
    assert read_active_versions(app_root) == {}
    assert saved_profile["system"]["scratch_dir"] == "/arf/scratch/{user}"
    reloaded = load_installed_plugins(root=app_root, app_version="1.4.0")
    assert reloaded.plugins == []

    # Steps 18-21: install Fluent lint and lint a journal missing the TUI version.
    install_plugin_from_registry(
        find_entry(registry, "org.hpcclient.fluent"),
        root=app_root,
        app_version="1.4.0",
        fetcher=fetch,
    )
    packs = (
        __import__("hpc_gui.lint.rulepack", fromlist=["load_lint_packs"]).load_lint_packs(
            root=app_root, app_version="1.4.0"
        )
    )
    assert packs and packs[0].matches("job.jou")
    diagnostics = lint_text(
        "/display set-lsd-bc\n", file_name="job.jou", rule_pack=packs[0]
    )
    assert any(d.rule_id == "FLUENT001" for d in diagnostics)

    # Steps 22-23: updating publishes a new immutable version and activates it;
    # the old version directory remains for rollback.
    registry_v2, fetch_v2 = make_registry_and_responses(
        tmp_path / "registry-world-v2", fluent_version="0.2.0"
    )
    install_plugin_from_registry(
        find_entry(registry_v2, "org.hpcclient.fluent"),
        root=app_root,
        app_version="1.4.0",
        fetcher=fetch_v2,
    )
    assert read_active_versions(app_root)["org.hpcclient.fluent"] == "0.2.0"
    assert (packages_dir(app_root) / "org.hpcclient.fluent" / "0.1.0").is_dir()

    # Steps 24-25: a corrupted update fails verification; previous version
    # remains active (rollback guarantee).
    broken_world_root = tmp_path / "registry-world-broken"
    broken_registry, _ = make_registry_and_responses(
        broken_world_root, fluent_version="0.3.0"
    )
    entry = find_entry(broken_registry, "org.hpcclient.fluent")
    original_sha = entry["manifest_sha256"]
    entry["manifest_sha256"] = sha256_bytes(b"tampered")
    assert original_sha != entry["manifest_sha256"]
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=app_root, app_version="1.4.0", fetcher=fetch_v2
        )
    assert read_active_versions(app_root)["org.hpcclient.fluent"] == "0.2.0"

    # Step 26: the broader SSH/SFTP/Slurm regression suite is the remainder of
    # this repository's tests and must pass in the same run.
