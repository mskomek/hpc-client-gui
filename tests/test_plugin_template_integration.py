"""Wave 06 tests: installed cluster plugins as System Templates."""

from __future__ import annotations

import hashlib
import json
import os
import unittest.mock as mock
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hpc_gui.core.i18n import load_language, t
from hpc_gui.plugins.state import write_active_versions
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


TRUBA_PROFILE_V1 = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {
        "home_dir": "/arf/home/{user}",
        "scratch_dir": "/arf/scratch/{user}",
    },
    "commands": {
        "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
        "sbatch_command": "cd -- {script_dir_q} && sbatch -- {script_name_q}",
        "scancel_command": "scancel {job_id_q}",
        "sacct_command": (
            "sacct -u {user} --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES"
        ),
        "scontrol_command": "scontrol show job {job_id_q}",
        "status_command": "lssrv",
        "active_job_ids_command": 'squeue -h -u {user} -o "%A"',
        "job_state_command": "sacct -n -X -j {job_id_q} -o State -P",
    },
}


def install_profile_fixture(
    root: Path,
    *,
    plugin_id: str = "org.hpcclient.truba",
    name: str = "TRUBA",
    version: str = "1.0.0",
    profile: dict | None = None,
    broken: bool = False,
) -> None:
    """Create a locally installed plugin package (manifest + payload)."""
    pkg = root / "packages" / plugin_id / version
    pkg.mkdir(parents=True, exist_ok=True)
    if broken:
        (pkg / "cluster-profile.json").write_text("{broken", encoding="utf-8")
    else:
        (pkg / "cluster-profile.json").write_text(
            json.dumps(profile or TRUBA_PROFILE_V1), encoding="utf-8"
        )
    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": plugin_id,
        "name": name,
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": f"{name} cluster profile.",
        "requires_app": ">=1.3.0",
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [],
    }
    if not broken:
        payload = (pkg / "cluster-profile.json").read_bytes()
        manifest["files"] = [
            {
                "path": "cluster-profile.json",
                "sha256": sha256_bytes(payload),
                "size": len(payload),
                "role": "cluster-profile",
            }
        ]
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    active = {}
    index_path = root / "active.json"
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        active = data.get("active", data)
    active[plugin_id] = version
    write_active_versions(active, root=root)


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    load_language("en")
    yield app
    load_language("en")


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


def test_adapter_returns_truba_group_with_provenance(tmp_path: Path):
    install_profile_fixture(tmp_path)
    groups = installed_cluster_template_groups(root=tmp_path, app_version="1.4.0")
    assert list(groups) == ["TRUBA"]
    template = groups["TRUBA"][0]
    assert template.settings["name"] == "TRUBA"
    assert template.settings["scratch_dir"] == "/arf/scratch/{user}"
    assert template.settings["home_dir"] == "/arf/home/{user}"
    assert template.settings["status_command"] == "lssrv"
    assert template.provenance == {
        "kind": "plugin",
        "plugin_id": "org.hpcclient.truba",
        "plugin_version": "1.0.0",
        "profile_id": "truba",
    }


def test_adapter_skips_broken_plugins(tmp_path: Path):
    install_profile_fixture(tmp_path, broken=True)
    groups = installed_cluster_template_groups(root=tmp_path, app_version="1.4.0")
    assert groups == {}


def test_multiple_plugins_group_separately(tmp_path: Path):
    install_profile_fixture(tmp_path)
    install_profile_fixture(
        tmp_path,
        plugin_id="org.hpcclient.other",
        name="Other Cluster",
        profile={
            **TRUBA_PROFILE_V1,
            "profile_id": "other",
            "name": "Other Cluster",
        },
    )
    groups = installed_cluster_template_groups(root=tmp_path, app_version="1.4.0")
    assert sorted(groups) == ["Other Cluster", "TRUBA"]


# ---------------------------------------------------------------------------
# Connection dialog menu
# ---------------------------------------------------------------------------


def _menu_texts(menu) -> list[str]:
    return [action.text() for action in menu.actions()]


def test_menu_without_plugins_has_builtin_user_and_more(qapp):
    dialog = ConnectionDialog()
    try:
        texts = _menu_texts(dialog.btn_system_templates.menu())
        assert "Generic Slurm" in texts
        assert t("connection.plugin_templates") not in texts
        assert t("connection.get_more_plugins") in texts
    finally:
        dialog.deleteLater()


def test_menu_lists_installed_truba(qapp, tmp_path: Path):
    install_profile_fixture(tmp_path)
    with mock.patch(
        "hpc_gui.plugins.templates.load_installed_plugins",
        return_value=__import__(
            "hpc_gui.plugins.loader", fromlist=["load_installed_plugins"]
        ).load_installed_plugins(root=tmp_path, app_version="1.4.0"),
    ):
        dialog = ConnectionDialog()
        try:
            texts = _menu_texts(dialog.btn_system_templates.menu())
            assert t("connection.plugin_templates") in texts
            plugin_menu = next(
                action.menu()
                for action in dialog.btn_system_templates.menu().actions()
                if action.text() == t("connection.plugin_templates")
            )
            assert "TRUBA" in _menu_texts(plugin_menu)

            # Apply the TRUBA action and check exact fields.
            truba_action = next(
                a for a in plugin_menu.actions() if a.text() == "TRUBA"
            )
            truba_action.trigger()
            assert dialog.system_name.text() == "TRUBA"
            assert dialog.scratch_dir.text() == "/arf/scratch/{user}"
            assert dialog.home_dir.text() == "/arf/home/{user}"
            assert dialog.status_command.text() == "lssrv"
            assert dialog.squeue_command.text().startswith("squeue -h -u {user}")
            assert dialog.username.text() == ""  # never auto-filled
        finally:
            dialog.deleteLater()


def test_apply_then_edit_then_save_persists_edited_values_and_provenance(qapp, tmp_path: Path):
    install_profile_fixture(tmp_path)
    loader_mod = __import__("hpc_gui.plugins.loader", fromlist=["load_installed_plugins"])
    with mock.patch(
        "hpc_gui.plugins.templates.load_installed_plugins",
        return_value=loader_mod.load_installed_plugins(root=tmp_path, app_version="1.4.0"),
    ):
        saved = []
        dialog = ConnectionDialog(on_save=lambda profile: saved.append(profile) or True)
        try:
            plugin_menu = next(
                action.menu()
                for action in dialog.btn_system_templates.menu().actions()
                if action.text() == t("connection.plugin_templates")
            )
            next(a for a in plugin_menu.actions() if a.text() == "TRUBA").trigger()
            # User edits after applying.
            dialog.home_dir.setText("/custom/home/{user}")
            dialog.profile_name.setText("lab")
            dialog._save_clicked()
        finally:
            dialog.deleteLater()

    assert len(saved) == 1
    profile = saved[0]
    assert profile["system"]["home_dir"] == "/custom/home/{user}"
    assert profile["system"]["status_command"] == "lssrv"
    assert profile["system_template_source"]["kind"] == "plugin"
    assert profile["system_template_source"]["plugin_id"] == "org.hpcclient.truba"


def test_saved_profile_survives_plugin_removal(qapp):
    """Saved values are a snapshot: no plugin needed to reload them."""
    saved_profile = {
        "name": "lab",
        "system": {
            "name": "TRUBA",
            "scratch_dir": "/arf/scratch/{user}",
            "home_dir": "/arf/home/{user}",
            "status_command": "lssrv",
        },
        "system_template_source": {
            "kind": "plugin",
            "plugin_id": "org.hpcclient.truba",
            "plugin_version": "1.0.0",
            "profile_id": "truba",
        },
    }
    with mock.patch(
        "hpc_gui.plugins.templates.installed_cluster_template_groups",
        return_value={},
    ):
        dialog = ConnectionDialog(initial_profile=saved_profile)
        try:
            assert dialog.system_name.text() == "TRUBA"
            assert dialog.home_dir.text() == "/arf/home/{user}"
            collected = dialog._collect_profile()
        finally:
            dialog.deleteLater()

    assert collected is not None
    assert collected["system"]["home_dir"] == "/arf/home/{user}"
    assert collected["system"]["status_command"] == "lssrv"
    assert collected["system_template_source"]["plugin_id"] == "org.hpcclient.truba"


def test_plugin_update_keeps_old_snapshot_new_uses_new_version(qapp, tmp_path: Path):
    install_profile_fixture(tmp_path, version="1.0.0")
    loader_mod = __import__("hpc_gui.plugins.loader", fromlist=["load_installed_plugins"])

    with mock.patch(
        "hpc_gui.plugins.templates.load_installed_plugins",
        return_value=loader_mod.load_installed_plugins(root=tmp_path, app_version="1.4.0"),
    ):
        dialog = ConnectionDialog()
        try:
            plugin_menu = next(
                action.menu()
                for action in dialog.btn_system_templates.menu().actions()
                if action.text() == t("connection.plugin_templates")
            )
            next(a for a in plugin_menu.actions() if a.text() == "TRUBA").trigger()
            old_status = dialog.status_command.text()
        finally:
            dialog.deleteLater()

    # Activate 1.1.0 with a changed status command.
    profile_v11 = {
        **TRUBA_PROFILE_V1,
        "commands": {**TRUBA_PROFILE_V1["commands"], "status_command": "lssrv-v2"},
    }
    install_profile_fixture(tmp_path, version="1.1.0", profile=profile_v11)

    with mock.patch(
        "hpc_gui.plugins.templates.load_installed_plugins",
        return_value=loader_mod.load_installed_plugins(root=tmp_path, app_version="1.4.0"),
    ):
        dialog2 = ConnectionDialog()
        try:
            plugin_menu = next(
                action.menu()
                for action in dialog2.btn_system_templates.menu().actions()
                if action.text() == t("connection.plugin_templates")
            )
            next(a for a in plugin_menu.actions() if a.text() == "TRUBA").trigger()
            new_status = dialog2.status_command.text()
            new_source = dialog2._collect_profile()["system_template_source"]
        finally:
            dialog2.deleteLater()

    assert old_status == "lssrv"  # old snapshot unchanged by the update
    assert new_status == "lssrv-v2"  # fresh templates use the new version
    assert new_source["plugin_version"] == "1.1.0"


def test_get_more_plugins_opens_manager(qapp):
    opened = []

    class FakeSignal:
        def connect(self, *args, **kwargs):
            pass

    class FakeManager:
        plugins_changed = FakeSignal()

        def __init__(self, parent=None):
            pass

        def exec(self):
            opened.append(True)

    import sys

    fake_module = __import__("types").ModuleType("fake_pm")
    fake_module.PluginManagerDialog = FakeManager
    with mock.patch.dict(sys.modules, {"hpc_gui.ui.dialogs.plugin_manager_dialog": fake_module}):
        dialog = ConnectionDialog()
        try:
            menu = dialog.btn_system_templates.menu()
            more_action = next(
                a
                for a in menu.actions()
                if a.text() == t("connection.get_more_plugins")
            )
            more_action.trigger()
        finally:
            dialog.deleteLater()

    assert opened == [True]
