"""Wave 03 tests: generic system defaults, legacy profile compatibility,
and the local declarative plugin loader."""

from __future__ import annotations

import json
import unittest.mock as mock
from pathlib import Path

import pytest

from hpc_gui.config.system_profile import (
    GENERIC_SLURM_DEFAULTS,
    builtin_system_template_groups,
    format_remote_path,
    load_user_system_templates,
    normalize_system_settings,
    plugin_system_template_groups,
)
from hpc_gui.plugins.compatibility import is_app_compatible, validate_requires_app
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import ClusterProfileDefinition, PLUGIN_API_VERSION
from hpc_gui.plugins.storage import (
    packages_dir,
    plugins_root,
    read_active_versions,
    write_active_versions,
)
from hpc_gui.services.slurm_ssh import SSHSlurmBackend


# ---------------------------------------------------------------------------
# Generic defaults
# ---------------------------------------------------------------------------


def test_generic_defaults_contain_no_truba_paths():
    joined = json.dumps(GENERIC_SLURM_DEFAULTS)
    assert "/arf" not in joined


def test_generic_defaults_have_no_site_status_command():
    assert GENERIC_SLURM_DEFAULTS["status_command"] == ""
    assert "lssrv" not in json.dumps(GENERIC_SLURM_DEFAULTS)


def test_generic_defaults_keep_standard_slurm_commands():
    assert 'squeue -h -u {user} -o "%i' in GENERIC_SLURM_DEFAULTS["squeue_command"]
    assert "{script_dir_q}" in GENERIC_SLURM_DEFAULTS["sbatch_command"]
    assert GENERIC_SLURM_DEFAULTS["scancel_command"] == "scancel {job_id_q}"
    assert GENERIC_SLURM_DEFAULTS["scontrol_command"] == "scontrol show job {job_id_q}"
    assert "sacct" in GENERIC_SLURM_DEFAULTS["job_state_command"]


def test_builtin_group_is_generic_slurm_only():
    groups = builtin_system_template_groups()
    assert list(groups) == ["Generic Slurm"]
    assert groups["Generic Slurm"][0] == dict(GENERIC_SLURM_DEFAULTS)


class _FakeSSH:
    def __init__(self):
        self.commands = []

    def run(self, command, **kwargs):
        self.commands.append(command)
        return 0, "", ""


def test_missing_site_status_does_not_crash_backend():
    backend = SSHSlurmBackend(_FakeSSH(), system_settings=None)
    with pytest.raises(RuntimeError, match="No site status command"):
        backend.lssrv()


# ---------------------------------------------------------------------------
# Saved-profile compatibility
# ---------------------------------------------------------------------------


def test_full_saved_system_dict_is_preserved_verbatim():
    saved = {
        "name": "TRUBA",
        "scratch_dir": "/arf/scratch/{user}",
        "home_dir": "/arf/home/{user}",
        "status_command": "lssrv",
    }
    normalized = normalize_system_settings(saved)
    assert normalized["scratch_dir"] == "/arf/scratch/{user}"
    assert normalized["home_dir"] == "/arf/home/{user}"
    assert normalized["status_command"] == "lssrv"


def test_partial_old_dict_is_normalized_safely():
    normalized = normalize_system_settings({"name": "Old", "scratch_dir": "/old/scratch"})
    assert normalized["name"] == "Old"
    assert normalized["scratch_dir"] == "/old/scratch"
    assert normalized["home_dir"] == ""
    assert normalized["squeue_command"] == GENERIC_SLURM_DEFAULTS["squeue_command"]


def test_truba_like_saved_profile_stays_truba_like():
    truba_like = {
        "system": {
            "name": "HPC",
            "scratch_dir": "/arf/scratch/alice",
            "home_dir": "/arf/home/alice",
            "status_command": "lssrv",
        }
    }
    normalized = normalize_system_settings(truba_like.get("system"))
    assert normalized == {
        **GENERIC_SLURM_DEFAULTS,
        **truba_like["system"],
    }


def test_user_templates_are_unaffected_by_default_changes():
    stored = {"system_templates": [{"name": "Mine", "scratch_dir": "/data/{user}", "status_command": ""}]}
    with mock.patch(
        "hpc_gui.config.system_profile.load_settings", return_value=stored
    ):
        templates = load_user_system_templates()
    assert len(templates) == 1
    assert templates[0]["name"] == "Mine"
    assert templates[0]["scratch_dir"] == "/data/{user}"


def test_format_remote_path_handles_empty_template():
    assert format_remote_path("", "alice") == ""
    assert format_remote_path("/arf/home/{user}", "alice") == "/arf/home/alice"
    assert format_remote_path("/bad/{unknown}", "alice") == "/bad/{unknown}"


# ---------------------------------------------------------------------------
# Compatibility parser
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("requires_app", "app_version", "expected"),
    [
        (">=1.4.0", "1.4.0", True),
        (">=1.4.0", "1.3.0", False),
        ("<=2.0.0", "1.9.9", True),
        ("<=2.0.0", "2.0.0", True),
        ("<=2.0.0", "2.0.1", False),
        ("==1.4.0", "1.4.0", True),
        ("==1.4.*", "1.4.7", True),
        ("==1.4.*", "1.5.0", False),
        ("~=1.4.0", "1.4.9", True),
        ("~=1.4.0", "1.5.0", False),
        (">=1.4.0,<2.0.0", "1.6.2", True),
        (">=1.4.0,<=2.0.0", "2.1.0", False),
        (">=1.4", "1.4.0", True),  # partial versions pad to x.y.0
    ],
)
def test_compatibility_matrix(requires_app, app_version, expected):
    assert is_app_compatible(requires_app, app_version) is expected


@pytest.mark.parametrize(
    "bad",
    ["", "=1.4.0", ">=banana", "==*", ">=1.4.*,<=2", "1.4.0 !", ",,"],
)
def test_unknown_requires_app_syntax_fails_closed(bad):
    assert validate_requires_app(bad), f"'{bad}' should be rejected"
    assert not is_app_compatible(bad, "9.9.9")


# ---------------------------------------------------------------------------
# Local plugin storage helpers
# ---------------------------------------------------------------------------


def test_plugins_root_override(tmp_path: Path):
    assert plugins_root(tmp_path) == Path(tmp_path)
    assert packages_dir(tmp_path) == Path(tmp_path) / "packages"


def test_active_index_round_trip(tmp_path: Path):
    assert read_active_versions(tmp_path) == {}
    write_active_versions({"org.hpcclient.truba": "1.0.0"}, root=tmp_path)
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    # Legacy flat layout is also readable.
    (Path(tmp_path) / "active.json").write_text(
        json.dumps({"org.hpcclient.legacy": "0.1.0"}), encoding="utf-8"
    )
    assert read_active_versions(tmp_path)["org.hpcclient.legacy"] == "0.1.0"


# ---------------------------------------------------------------------------
# Loader fixtures
# ---------------------------------------------------------------------------

VALID_MANIFEST = {
    "schema_version": 1,
    "plugin_api": PLUGIN_API_VERSION,
    "id": "org.hpcclient.truba",
    "name": "TRUBA",
    "version": "1.0.0",
    "publisher": "HPC Client GUI",
    "license": "MIT",
    "description": "TRUBA cluster profile.",
    "requires_app": ">=1.3.0",
    "capabilities": ["cluster-profile"],
    "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
    "files": [],
}

VALID_PROFILE = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {"status_command": "lssrv"},
}


def install_plugin(root: Path, manifest: dict, profile: dict | None) -> None:
    import hashlib

    pkg = root / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    files = []
    if profile is not None:
        entrypoints = manifest.get("entrypoints") or {}
        rel_list = entrypoints.get("cluster_profiles") or []
        for rel in rel_list:
            payload = json.dumps(profile).encode("utf-8")
            (pkg / rel).write_bytes(payload)
            files.append(
                {
                    "path": rel,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "role": "cluster-profile",
                }
            )
    manifest = {**manifest, "files": files or manifest.get("files") or []}
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_active_versions({manifest["id"]: manifest["version"]}, root=root)


def test_valid_local_plugin_loads(tmp_path: Path):
    install_plugin(tmp_path, VALID_MANIFEST, VALID_PROFILE)
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert result.problems == []
    assert len(result.plugins) == 1
    installed = result.plugins[0]
    assert installed.manifest.id == "org.hpcclient.truba"
    assert installed.cluster_profiles[0].profile_id == "truba"

    settings = installed.cluster_profiles[0].to_system_settings()
    assert settings["name"] == "TRUBA"
    assert settings["home_dir"] == "/arf/home/{user}"
    assert settings["scratch_dir"] == "/arf/scratch/{user}"
    assert settings["status_command"] == "lssrv"


def test_unsupported_plugin_api_rejected(tmp_path: Path):
    manifest = {**VALID_MANIFEST, "plugin_api": 2}
    install_plugin(tmp_path, manifest, VALID_PROFILE)
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert result.plugins == []
    assert any("plugin_api must be 1" in problem.reason for problem in result.problems)


def test_incompatible_app_rejected(tmp_path: Path):
    manifest = {**VALID_MANIFEST, "requires_app": ">=99.0.0"}
    install_plugin(tmp_path, manifest, VALID_PROFILE)
    result = load_installed_plugins(root=tmp_path, app_version="1.3.0")
    assert result.plugins == []
    assert any("incompatible" in problem.reason for problem in result.problems)


def test_missing_entrypoint_file_rejected(tmp_path: Path):
    install_plugin(tmp_path, VALID_MANIFEST, VALID_PROFILE)
    pkg = tmp_path / "packages" / VALID_MANIFEST["id"] / VALID_MANIFEST["version"]
    (pkg / "cluster-profile.json").unlink()
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert result.plugins == []
    # The local integrity re-check catches the missing declared file before
    # the entrypoint loader would; either way the plugin is skipped.
    assert any(
        "missing payload file" in problem.reason or "file not found" in problem.reason
        for problem in result.problems
    )


def test_malformed_plugin_json_is_isolated(tmp_path: Path):
    broken_pkg = tmp_path / "packages" / "org.hpcclient.broken" / "1.0.0"
    broken_pkg.mkdir(parents=True)
    (broken_pkg / "manifest.json").write_text("{not json", encoding="utf-8")

    install_plugin(tmp_path, VALID_MANIFEST, VALID_PROFILE)
    write_active_versions(
        {
            VALID_MANIFEST["id"]: VALID_MANIFEST["version"],
            "org.hpcclient.broken": "1.0.0",
        },
        root=tmp_path,
    )

    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert any(p.plugin_id == "org.hpcclient.broken" for p in result.problems)


def test_invalid_profile_shape_isolated(tmp_path: Path):
    install_plugin(tmp_path, VALID_MANIFEST, {"schema_version": 1})
    result = load_installed_plugins(root=tmp_path, app_version="1.4.0")
    assert result.plugins == []
    assert any("invalid cluster profile" in problem.reason for problem in result.problems)


def test_loader_never_executes_payload(tmp_path: Path):
    """No import/execution mechanism may exist in the declarative loader."""
    import inspect

    import hpc_gui.plugins.loader as loader_module

    source = inspect.getsource(loader_module)
    for forbidden in ("importlib", "__import__", "exec(", "eval(", "subprocess"):
        assert forbidden not in source, f"loader must not use {forbidden}"


def test_zero_installed_plugins_loads_empty():
    result = load_installed_plugins(root=Path("/nonexistent-plugins-root"), app_version="1.4.0")
    assert result.plugins == []
    assert result.problems == []


def test_plugin_system_template_groups_conversion():
    install_dir = Path(".")
    from hpc_gui.plugins.models import InstalledPlugin, PluginFile, PluginManifest

    manifest = PluginManifest(
        schema_version=1,
        plugin_api=1,
        id="org.hpcclient.truba",
        name="TRUBA",
        version="1.0.0",
        publisher="x",
        license="MIT",
        description="d",
        requires_app=">=1.4.0",
        capabilities=("cluster-profile",),
        entrypoints={},
        files=(PluginFile(path="a.json", sha256="0" * 64, size=1, role="cluster-profile"),),
    )
    profile = ClusterProfileDefinition(
        profile_id="truba",
        name="TRUBA",
        scheduler="slurm",
        paths={"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
        commands={"status_command": "lssrv"},
    )
    installed = InstalledPlugin(
        manifest=manifest, directory=install_dir, cluster_profiles=(profile,)
    )
    groups = plugin_system_template_groups([installed])
    assert list(groups) == ["TRUBA"]
    template = groups["TRUBA"][0]
    assert template["home_dir"] == "/arf/home/{user}"
    assert template["scratch_dir"] == "/arf/scratch/{user}"
    assert template["status_command"] == "lssrv"
    assert plugin_system_template_groups(None) == {}
