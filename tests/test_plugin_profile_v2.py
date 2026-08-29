"""Cluster profile payload v2 stays typed while v1 remains compatible."""

from hpc_gui.plugins.loader import _build_profile
from hpc_gui.plugins.validator import validate_cluster_profile_dict


def test_v2_profile_retains_structured_sections_and_legacy_settings():
    raw = {
        "schema_version": 2,
        "profile_id": "truba",
        "name": "TRUBA",
        "scheduler": "slurm",
        "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
        "commands": {"status_command": "lssrv"},
        "site": {"region": "Türkiye"},
        "storage": [{"id": "home", "label": "Home", "kind": "home"}],
        "quota_sources": [{"id": "home-quota", "enabled": False}],
    }

    assert validate_cluster_profile_dict(raw) == []
    profile, error = _build_profile(raw)

    assert error is None
    assert profile is not None
    assert profile.schema_version == 2
    assert profile.site["region"] == "Türkiye"
    assert profile.storage[0]["id"] == "home"
    assert profile.quota_sources[0]["enabled"] is False
    assert profile.to_system_settings()["home_dir"] == "/arf/home/{user}"


def test_v2_profile_rejects_unknown_top_level_keys():
    raw = {
        "schema_version": 2,
        "profile_id": "truba",
        "name": "TRUBA",
        "scheduler": "slurm",
        "secret_command": "rm -rf /",
    }

    assert any("unknown key 'secret_command'" in error for error in validate_cluster_profile_dict(raw))


def test_v1_profile_still_validates():
    raw = {"schema_version": 1, "profile_id": "x", "name": "X", "scheduler": "slurm"}
    assert validate_cluster_profile_dict(raw) == []
    profile, error = _build_profile(raw)
    assert error is None
    assert profile.schema_version == 1
