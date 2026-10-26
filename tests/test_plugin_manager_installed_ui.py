"""Plugin Manager installed-version selection and rollback UI tests."""

from __future__ import annotations

import unittest.mock as mock
from types import SimpleNamespace

import pytest

pytest_plugins = ("support.plugin_manager_ui_fixtures",)

from hpc_gui.core.i18n import t
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

def _make_installed_dialog(qapp, versions, active_version="1.9.0"):
    dialog = PluginManagerDialog()
    dialog._installed_versions = SimpleNamespace(
        plugins=[
            SimpleNamespace(
                manifest=SimpleNamespace(
                    id="org.hpcclient.multi",
                    name="Multi",
                    version=active_version,
                )
            )
        ],
        problems=[],
    )
    active_patch = mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        return_value={"org.hpcclient.multi": active_version},
    )
    state_patch = mock.patch(
        "hpc_gui.plugins.state.read_installed_state",
        return_value={
            "org.hpcclient.multi": {
                "versions": list(versions),
                "installed_at": "",
                "manifest_hashes": {},
                "migrated": [],
            }
        },
    )
    with active_patch, state_patch:
        dialog._populate_installed({"org.hpcclient.multi": active_version})
    return dialog


def _installed_card_widgets(dialog):
    from PySide6.QtWidgets import QComboBox, QPushButton

    container = dialog.installed_list.widget()
    combos = container.findChildren(QComboBox)
    buttons = container.findChildren(QPushButton)
    return combos, buttons


@pytest.mark.gui
def test_installed_tab_shows_active_version_and_sorted_versions(qapp):
    dialog = PluginManagerDialog()
    dialog._installed_versions = SimpleNamespace(
        plugins=[
            SimpleNamespace(
                manifest=SimpleNamespace(
                    id="org.hpcclient.multi", name="Multi", version="1.10.0"
                )
            )
        ],
        problems=[],
    )
    with mock.patch(
        "hpc_gui.plugins.state.read_installed_state",
        return_value={
            "org.hpcclient.multi": {
                "versions": ["1.9.0", "1.10.0", "1.2.0"],
                "installed_at": "",
                "manifest_hashes": {},
                "migrated": [],
            }
        },
    ):
        dialog._populate_installed({"org.hpcclient.multi": "1.10.0"})

    container = dialog.installed_list.widget()
    labels = "\n".join(label.text() for label in container.findChildren(type(dialog.status_label)))
    assert "1.10.0" in labels  # active version is the headline version

    combos, _buttons = _installed_card_widgets(dialog)
    assert len(combos) == 1
    items = [combos[0].itemText(i) for i in range(combos[0].count())]
    assert items == ["1.10.0", "1.9.0", "1.2.0"]


@pytest.mark.gui
def test_rollback_button_label_depends_on_pep440_order(qapp):
    dialog = _make_installed_dialog(qapp, ["1.9.0", "1.10.0"], active_version="1.10.0")
    _combos, buttons = _installed_card_widgets(dialog)
    rollback_buttons = [b for b in buttons if b.text() == t("plugins.rollback")]
    assert len(rollback_buttons) == 1

    combo = _combos[0]
    combo.setCurrentText("1.9.0")
    assert rollback_buttons[0].text() == t("plugins.rollback")
    assert rollback_buttons[0].isEnabled()
    combo.setCurrentText("1.10.0")  # equals active: action disabled
    assert not rollback_buttons[0].isEnabled()


@pytest.mark.gui
def test_activate_label_for_newer_selected_version(qapp):
    dialog = _make_installed_dialog(qapp, ["1.9.0", "1.10.0"], active_version="1.9.0")
    combo, buttons = _installed_card_widgets(dialog)
    combo[0].setCurrentText("1.10.0")
    activate_buttons = [b for b in buttons if b.text() == t("plugins.activate")]
    assert len(activate_buttons) == 1


@pytest.mark.gui
def test_rollback_requires_confirmation_and_runs_off_gui_thread(qapp, frozen_thread_pool):
    dialog = _make_installed_dialog(qapp, ["1.9.0", "1.10.0"], active_version="1.10.0")
    emitted = []
    dialog.plugins_changed.connect(lambda: emitted.append(True))
    confirmed = []
    activated = []

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            confirmed.append(args)
            return FakeBox.Yes

        @staticmethod
        def information(*args, **kwargs):
            pass

    def fake_activate(plugin_id, version):
        activated.append((plugin_id, version))

    with mock.patch(
        "hpc_gui.plugins.state.activate_version",
        side_effect=fake_activate,
    ), mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        dialog.change_plugin_version(
            "org.hpcclient.multi", "Multi", "1.9.0", "1.10.0"
        )
        worker = dialog._version_worker
        assert worker is not None
        worker.run()

    assert activated == [("org.hpcclient.multi", "1.9.0")]
    assert len(confirmed) == 1
    assert emitted == [True]
    assert dialog._version_worker is None


@pytest.mark.gui
def test_rollback_cancelled_keeps_current_version(qapp):
    dialog = _make_installed_dialog(qapp, ["1.9.0", "1.10.0"], active_version="1.10.0")

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            return FakeBox.No

    with mock.patch(
        "hpc_gui.plugins.state.activate_version"
    ) as activate, mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        dialog.change_plugin_version("org.hpcclient.multi", "Multi", "1.9.0", "1.10.0")

    assert activate.call_count == 0
    assert dialog._version_worker is None


@pytest.mark.gui
def test_failed_activation_preserves_previous_version_message(qapp, frozen_thread_pool):
    dialog = _make_installed_dialog(qapp, ["1.9.0", "1.10.0"], active_version="1.10.0")
    shown = []

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            return FakeBox.Yes

        @staticmethod
        def warning(*args, **kwargs):
            shown.append(args)

    with mock.patch(
        "hpc_gui.plugins.state.activate_version",
        side_effect=ValueError("validation failed"),
    ), mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        dialog.change_plugin_version("org.hpcclient.multi", "Multi", "1.9.0", "1.10.0")
        worker = dialog._version_worker
        worker.run()

    assert len(shown) == 1
    expected = t("plugins.version_switch_failed").format(name="Multi", version="1.9.0")
    assert expected in str(shown[0])


@pytest.mark.gui
def test_corrupt_plugin_problem_shows_actionable_message(qapp):
    dialog = PluginManagerDialog()
    dialog._installed_versions = SimpleNamespace(
        plugins=[],
        problems=[
            SimpleNamespace(
                plugin_id="org.hpcclient.broken",
                version="2.0.0",
                reason="integrity check failed (reinstall this plugin)",
            )
        ],
    )
    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        return_value={},
    ):
        dialog._populate_installed({})
    text = "\n".join(
        label.text() for label in dialog.installed_list.widget().findChildren(type(dialog.status_label))
    )
    assert t("plugins.corrupt_plugin").format(name="org.hpcclient.broken") in text
