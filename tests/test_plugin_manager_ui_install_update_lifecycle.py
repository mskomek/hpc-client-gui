"""Wave 05 tests: Plugins button and Plugin Manager dialog states.

All registry/installer interactions use injected fetchers and patched
service functions; nothing touches the network.
"""

from __future__ import annotations

pytest_plugins = ('support.test_plugin_manager_ui_shared',)
from support.test_plugin_manager_ui_shared import (
    PluginManagerDialog,
    SimpleNamespace,
    VALID_REGISTRY,
    _installed_card_widgets,
    _make_installed_dialog,
    json,
    mock,
    pytest,
    registry_fetcher,
    t,
)

@pytest.mark.unit
def test_install_summary_reports_capability_counts(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    entry = VALID_REGISTRY["plugins"][0]
    result = SimpleNamespace(
        installed=SimpleNamespace(
            manifest=SimpleNamespace(id=entry["id"], name="TRUBA"),
            cluster_profiles=(SimpleNamespace(),),
            lint_index=None,
            job_templates_index={"templates": [{}, {}, {}, {}]},
        ),
        activated=True,
    )
    dialog._last_install_result = result
    text = dialog._install_summary_text(entry)
    assert "TRUBA" in text
    assert "1" in text and "4" in text

    # Without detailed counts the generic message is used.
    dialog._last_install_result = SimpleNamespace(installed=None, activated=True)
    generic = dialog._install_summary_text(entry)
    assert generic == t("plugins.install_generic").format(name="TRUBA")

@pytest.mark.unit
def test_details_show_source_and_installed_state(qapp):
    shown = []

    class FakeBox:
        @staticmethod
        def information(*args, **kwargs):
            shown.append(args)

    dialog = PluginManagerDialog()
    try:
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
            return_value={"org.hpcclient.truba": "1.0.0"},
        ), mock.patch(
            "PySide6.QtWidgets.QMessageBox", FakeBox
        ):
            dialog.show_details(VALID_REGISTRY["plugins"][0], ["0.9.0"])
        text = shown[0][2]
        assert t("plugins.source_official_registry") in text
        assert t("plugins.installed_active") in text
        assert "0.9.0" in text
        assert "org.hpcclient.truba" in text
    finally:
        dialog.deleteLater()

@pytest.mark.gui
def test_successful_install_updates_state_and_emits_signal(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    emitted = []
    summaries = []
    dialog.plugins_changed.connect(lambda: emitted.append(True))
    entry = VALID_REGISTRY["plugins"][0]

    def fake_install(registry_entry, **kwargs):
        return SimpleNamespace(installed=SimpleNamespace(manifest=SimpleNamespace(id=entry["id"])), activated=True)

    class FakeBox:
        Warning = 3

        @staticmethod
        def information(*args, **kwargs):
            summaries.append(args)

        @staticmethod
        def warning(*args, **kwargs):
            pass

    with mock.patch(
        "hpc_gui.plugins.loader.read_active_versions",
        return_value={entry["id"]: entry["version"]},
    ), mock.patch(
        "hpc_gui.plugins.state.read_active_versions", return_value={}
    ), mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        return_value={},
    ), mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.install_plugin_from_registry",
        side_effect=fake_install,
    ), mock.patch(
        "PySide6.QtWidgets.QMessageBox", FakeBox
    ):
        loader.return_value = SimpleNamespace(plugins=[])
        dialog.refresh_registry()
        # Run the worker synchronously for deterministic tests; run() emits
        # its own finished/failed signals.
        worker = dialog._refresh_worker
        assert worker is not None
        worker.run()

        card_container = dialog.discover_list.widget()
        install_buttons = [
            b
            for b in card_container.findChildren(
                __import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton
            )
            if b.text() == t("plugins.install")
        ]
        assert len(install_buttons) == 1
        button = install_buttons[0]
        dialog.install_plugin(entry, button)

        install_worker = dialog._install_worker
        assert install_worker is not None
        install_worker.run()

        assert emitted == [True]
        # A completion summary is shown for the successful install.
        assert len(summaries) == 1
        # After success the button text/labels were rebuilt without error.
        assert dialog._install_worker is None

@pytest.mark.gui
def test_failed_install_restores_state_and_shows_error(qapp, frozen_thread_pool, monkeypatch):
    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        lambda: {},
    )
    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_disabled_ids",
        lambda: set(),
    )
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    entry = VALID_REGISTRY["plugins"][0]
    shown = []

    class FakeBox:
        Warning = 3

        @staticmethod
        def warning(*args, **kwargs):
            shown.append(args)

    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.install_plugin_from_registry",
        side_effect=RuntimeError("Manifest SHA-256 mismatch"),
    ), mock.patch(
        "PySide6.QtWidgets.QMessageBox", FakeBox
    ):
        loader.return_value = SimpleNamespace(plugins=[])
        dialog._on_registry_loaded(json.loads(json.dumps(VALID_REGISTRY)), "network")

        card_container = dialog.discover_list.widget()
        from PySide6.QtWidgets import QPushButton

        button = next(
            b for b in card_container.findChildren(QPushButton)
            if b.text() == t("plugins.install")
        )
        dialog.install_plugin(entry, button)
        worker = dialog._install_worker
        worker.run()

        assert dialog._install_worker is None
        assert len(shown) == 1
        assert t("plugins.verification_failed").format(name="") in str(shown[0])

@pytest.mark.gui
def test_removal_confirmation_path(qapp):
    dialog = PluginManagerDialog()
    emitted = []
    dialog.plugins_changed.connect(lambda: emitted.append(True))

    installed_plugin = SimpleNamespace(
        manifest=SimpleNamespace(id="org.hpcclient.truba", name="TRUBA", version="1.0.0")
    )
    removed = []
    answered = []

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            answered.append(args)
            return FakeBox.Yes if kwargs.get("answer_yes") else FakeBox.Yes

        @staticmethod
        def warning(*args, **kwargs):
            pass

    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.remove_plugin",
        side_effect=lambda pid: removed.append(pid) or ["1.0.0"],
    ), mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        loader.return_value = SimpleNamespace(plugins=[installed_plugin])
        dialog.rebuild_tabs()

        dialog.remove_plugin("org.hpcclient.truba", "TRUBA")

    assert removed == ["org.hpcclient.truba"]
    assert len(answered) == 1
    assert "TRUBA" in answered[0][2]
    assert emitted == [True]

@pytest.mark.gui
def test_removal_cancelled_does_not_remove(qapp):
    dialog = PluginManagerDialog()
    removed = []

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            return FakeBox.No

    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.remove_plugin",
        side_effect=lambda pid: removed.append(pid),
    ), mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        loader.return_value = SimpleNamespace(plugins=[])
        dialog.rebuild_tabs()
        dialog.remove_plugin("org.hpcclient.truba", "TRUBA")

    assert removed == []

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
