from hpc_gui.plugins.models import ClusterProfileDefinition


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


def test_legacy_profile_has_no_structured_storage_cards():
    profile = ClusterProfileDefinition(profile_id="x", name="X", scheduler="slurm")
    assert profile.visible_storage_areas() == ()
