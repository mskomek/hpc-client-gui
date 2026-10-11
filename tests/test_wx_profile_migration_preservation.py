from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hpc_gui.config import storage
from hpc_gui.wx_connection_dialog_profile import ConnectionDialogProfileMixin
from hpc_gui.wx_connection_dialog_storage import ConnectionDialogStorageMixin


class _TextControl:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def GetValue(self) -> str:
        return self.value

    def SetValue(self, value: str) -> None:
        self.value = value


def _profile_dialog() -> SimpleNamespace:
    dialog = SimpleNamespace()
    dialog.home_dir_ctrl = _TextControl("/custom/home/vmmig")
    dialog.scratch_dir_ctrl = _TextControl("/custom/scratch/vmmig")
    dialog._initial_profile = {"system": {}}
    dialog._legacy_storage_snapshot = {
        "home_dir": "/custom/home/vmmig",
        "scratch_dir": "/custom/scratch/vmmig",
    }
    dialog.storage_rows = [
        {
            "id": "home",
            "label": "Home",
            "kind": "home",
            "enabled": True,
            "path_template": "/arf/home/{user}",
            "access_context": "shared",
            "policy": {},
        },
        {
            "id": "scratch",
            "label": "Scratch",
            "kind": "scratch",
            "enabled": True,
            "path_template": "/arf/scratch/{user}",
            "access_context": "shared",
            "policy": {},
        },
    ]
    dialog._provider_template = {"storage": dialog.storage_rows}
    dialog._quota_source_declared = False
    dialog._wx = SimpleNamespace(NOT_FOUND=-1)
    dialog.quota_backend_choice = SimpleNamespace(GetSelection=lambda: -1)
    for name in (
        "system_name_ctrl",
        "squeue_ctrl",
        "sbatch_ctrl",
        "scancel_ctrl",
        "sacct_ctrl",
        "scontrol_ctrl",
        "status_cmd_ctrl",
        "active_job_ids_ctrl",
        "job_state_ctrl",
    ):
        setattr(dialog, name, _TextControl())
    dialog._sync_legacy_storage_paths = lambda: ConnectionDialogProfileMixin._sync_legacy_storage_paths(dialog)
    dialog._sync_structured_editor = lambda: ConnectionDialogProfileMixin._sync_structured_editor(dialog)
    return dialog


def test_saving_migrated_template_preserves_legacy_storage_overrides() -> None:
    dialog = _profile_dialog()

    system = ConnectionDialogProfileMixin._system_form_values(dialog)

    assert system["home_dir"] == "/custom/home/vmmig"
    assert system["scratch_dir"] == "/custom/scratch/vmmig"
    assert dialog.storage_rows[0]["path_template"] == "/custom/home/vmmig"
    assert dialog.storage_rows[1]["path_template"] == "/custom/scratch/vmmig"


def test_editing_structured_home_area_updates_legacy_field() -> None:
    dialog = _profile_dialog()
    dialog.storage_list = SimpleNamespace(GetSelection=lambda: 0)
    dialog._wx = SimpleNamespace(NOT_FOUND=-1)
    dialog._open_storage_area_editor = lambda current: {
        **current,
        "path_template": "/operator/selected/home",
    }
    dialog._sync_structured_editor = lambda: None
    dialog._sync_legacy_storage_control = (
        lambda area: ConnectionDialogStorageMixin._sync_legacy_storage_control(dialog, area)
    )
    dialog._refresh_storage_list = lambda: None

    ConnectionDialogStorageMixin._edit_storage_area(dialog)

    assert dialog.home_dir_ctrl.GetValue() == "/operator/selected/home"


def test_migrated_storage_override_survives_config_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    dialog = _profile_dialog()
    system = ConnectionDialogProfileMixin._system_form_values(dialog)
    profile = {
        "id": "profile-vmmig",
        "name": "Migration profile",
        "host": "cluster.example.org",
        "port": 22,
        "username": "vmmig",
        "system": system,
        "provider_template": system["provider_template"],
    }

    storage.upsert_profile(profile)
    saved = storage.load_profiles()[0]

    assert saved["system"]["home_dir"] == "/custom/home/vmmig"
    assert saved["system"]["scratch_dir"] == "/custom/scratch/vmmig"
    assert saved["provider_template"]["storage"][0]["path_template"] == "/custom/home/vmmig"
    assert saved["provider_template"]["storage"][1]["path_template"] == "/custom/scratch/vmmig"
