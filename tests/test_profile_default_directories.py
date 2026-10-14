from hpc_gui.config.system_profile import (
    profile_remote_directories,
    profile_system_settings,
)


def test_plugin_storage_paths_become_home_and_scratch_defaults():
    profile = {
        "username": "alice",
        "project": "proj-42",
        "account": "acct-7",
        "provider_template": {
            "storage": [
                {
                    "id": "home",
                    "kind": "home",
                    "path_template": "/home/{user}",
                },
                {
                    "id": "scratch",
                    "kind": "scratch",
                    "path_template": "/scratch/{project}/{user}",
                },
            ]
        },
    }

    normalized = profile_system_settings(profile)
    assert normalized["home_dir"] == "/home/{user}"
    assert normalized["scratch_dir"] == "/scratch/{project}/{user}"
    assert profile_remote_directories(profile) == {
        "scratch_dir": "/scratch/proj-42/alice",
        "home_dir": "/home/alice",
    }


def test_explicit_profile_paths_override_plugin_storage_metadata():
    profile = {
        "username": "alice",
        "system": {"home_dir": "/custom/home/{user}"},
        "provider_template": {
            "storage": [
                {"id": "home", "kind": "home", "path_template": "/home/{user}"}
            ]
        },
    }

    assert profile_remote_directories(profile)["home_dir"] == "/custom/home/alice"
