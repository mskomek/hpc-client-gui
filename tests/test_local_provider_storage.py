from __future__ import annotations

from unittest.mock import patch

import pytest

from hpc_gui.config.system_profile import save_user_system_template
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_new_connection_lazily_persists_local_structured_storage(qapp):
    dialog = ConnectionDialog()
    try:
        dialog.system_name.setText("Custom HPC")
        dialog.storage_rows = [{
            "id": "scratch",
            "label": "Scratch",
            "kind": "scratch",
            "enabled": True,
            "path_template": "/scratch/{user}",
            "access_context": "login-node",
            "policy": {"backup": None, "retention_days": None},
        }]
        saved = dialog._collect_profile()
    finally:
        dialog.deleteLater()

    provider = saved["provider_template"]
    assert provider["profile_id"] == "local"
    assert provider["storage"][0]["label"] == "Scratch"
    assert "system_template_source" not in saved


def test_local_quota_never_persists_user_command(qapp):
    dialog = ConnectionDialog()
    try:
        dialog.quota_enabled.setChecked(True)
        dialog.quota_command.setText("touch /tmp/pwned")
        saved = dialog._collect_profile()
    finally:
        dialog.deleteLater()

    source = saved["provider_template"]["quota_sources"][0]
    assert source["backend_id"] == ""
    assert source["command_template"] == ""


def test_local_structured_provider_survives_user_template_round_trip(qapp):
    dialog = ConnectionDialog()
    try:
        dialog.storage_rows = [{
            "id": "scratch", "label": "Scratch", "kind": "scratch",
            "path_template": "/scratch/{user}", "access_context": "login-node",
            "policy": {"backup": False, "retention_days": 30, "cleanup_note": "Monthly cleanup"},
        }]
        settings = dialog._system_form_values()
    finally:
        dialog.deleteLater()

    with (
        patch("hpc_gui.config.system_profile.load_settings", return_value={"system_templates": []}),
        patch("hpc_gui.config.system_profile.update_settings"),
    ):
        template = save_user_system_template("My University HPC", settings)

    restored = ConnectionDialog()
    try:
        restored._apply_system_template(template)
        assert restored._provider_origin == "local"
        assert restored.storage_rows[0]["path_template"] == "/scratch/{user}"
        assert restored.storage_rows[0]["policy"]["retention_days"] == 30
    finally:
        restored.deleteLater()
