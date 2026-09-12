import pytest
from hpc_gui.plugins.models import ClusterProfileDefinition


@pytest.mark.unit
def test_storage_cards_keep_valid_paths_without_quota():
    profile = ClusterProfileDefinition(
        profile_id="truba",
        name="TRUBA",
        scheduler="slurm",
        storage=(
            {"id": "home", "label": "Home", "path_template": "/arf/home/{user}"},
            {"id": "scratch", "label": "Scratch", "path_template": "", "enabled": True},
            {"id": "project", "label": "Project", "path_template": "/project", "enabled": False},
        ),
    )
    assert [area["id"] for area in profile.visible_storage_areas()] == ["home"]


@pytest.mark.unit
def test_legacy_profile_has_no_structured_storage_cards():
    profile = ClusterProfileDefinition(profile_id="x", name="X", scheduler="slurm")
    assert profile.visible_storage_areas() == ()


@pytest.mark.unit
def test_remote_environment_storage_area_is_visible_without_literal_path():
    profile = ClusterProfileDefinition(
        profile_id="stampede3",
        name="Stampede3",
        scheduler="slurm",
        storage=(
            {"id": "scratch", "label": "Scratch", "resolver": {"type": "remote-environment", "variable": "SCRATCH"}},
        ),
    )
    assert [area["id"] for area in profile.visible_storage_areas()] == ["scratch"]
