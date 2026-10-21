"""Plugin Manager card builders (Wave M01).

Qt ownership of the Plugin Manager dialog's card widgets: discover,
installed and updates cards plus scroll-list helpers. Builders take plain
data and explicit callbacks — they never touch the registry, installer or
plugin state services, so service mocks keep working through the dialog.
Pure rules live in ``plugin_manager_state``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.core.i18n import t
from hpc_gui.plugins.compatibility import (
    effective_requires_app,
    entry_is_app_compatible,
)
from hpc_gui.ui.dialogs import plugin_manager_state as state


def make_scroll_list() -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    container = QWidget()
    container.setLayout(QVBoxLayout())
    container.layout().setAlignment(Qt.AlignTop)
    scroll.setWidget(container)
    return scroll


def clear_list(scroll: QScrollArea) -> QVBoxLayout:
    container = scroll.widget()
    inner = container.layout()
    while inner.count():
        item = inner.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
    return inner


def empty_label(key: str) -> QLabel:
    label = QLabel(t(key))
    label.setStyleSheet("color: #666; padding: 12px;")
    return label


def populate_discover(
    scroll: QScrollArea,
    *,
    registry: dict | None,
    registry_source: str | None,
    active: dict[str, str],
    disabled_ids,
    app_version: str,
    on_details,
    on_install,
) -> None:
    inner = clear_list(scroll)
    grouped = state.grouped_latest(registry, app_version)
    if not grouped:
        inner.addWidget(
            empty_label(
                "plugins.registry_unavailable"
                if not registry_source
                else "plugins.no_plugins"
            )
        )
        return
    for entry, others in grouped:
        inner.addWidget(
            build_discover_card(
                entry,
                active,
                disabled_ids,
                others,
                app_version=app_version,
                on_details=on_details,
                on_install=on_install,
            )
        )


def build_discover_card(
    entry: dict,
    active: dict[str, str],
    disabled_ids=None,
    other_versions: list[str] | None = None,
    *,
    app_version: str,
    on_details,
    on_install,
) -> QFrame:
    card = QFrame()
    card.setObjectName("pluginCard")
    grid = QGridLayout(card)
    disabled_ids = disabled_ids or set()
    plugin_id = str(entry.get("id", ""))
    version = str(entry.get("version", ""))

    name = f"{entry.get('name', '')} v{version}"
    title = QLabel(name)
    title.setStyleSheet("font-weight: 600;")
    grid.addWidget(title, 0, 0)

    compatible = entry_is_app_compatible(entry, app_version)
    meta_bits = [
        f"{t('plugins.publisher')}: {entry.get('publisher', '')}",
        f"{t('plugins.requires_app_label')} "
        f"{effective_requires_app(entry) or entry.get('requires_app', '')}",
        (
            t("plugins.compatible_with_running")
            if compatible
            else t("plugins.incompatible_with_running")
        ),
    ]
    meta = QLabel(" · ".join(bit for bit in meta_bits if bit))
    meta.setStyleSheet("color: #666;")
    grid.addWidget(meta, 1, 0)

    description = QLabel(entry.get("description", ""))
    description.setWordWrap(True)
    grid.addWidget(description, 2, 0)

    capabilities = state.entry_capabilities(entry)
    trusted = "linter-tool" in capabilities
    if trusted:
        disclosure = QLabel(t("plugins.trusted_tool_disclosure_short"))
        disclosure.setWordWrap(True)
        disclosure.setStyleSheet("color: #8a4b00; padding: 2px 0;")
        grid.addWidget(disclosure, 3, 0)

    # Capability badges (translated; raw identifiers never shown).
    caps_row = QHBoxLayout()
    caps_row.setContentsMargins(0, 2, 0, 2)
    for capability in capabilities:
        badge = QLabel(state.capability_label(capability))
        badge.setProperty("capabilityBadge", True)
        badge.setStyleSheet(
            "color: #455a64; background: #eceff1; border-radius: 4px;"
            "padding: 1px 6px; font-size: 11px;"
        )
        caps_row.addWidget(badge)
    caps_row.addStretch(1)
    grid.addLayout(caps_row, 4 if trusted else 3, 0)

    if other_versions:
        others = QLabel(
            f"{t('plugins.other_versions_catalog')}: {', '.join(other_versions)}"
        )
        others.setStyleSheet("color: #666;")
        grid.addWidget(others, 5 if trusted else 4, 0)

    installed_here = state.is_installed(entry, active)
    active_version = active.get(plugin_id)
    update_available = bool(
        compatible
        and active_version
        and not installed_here
        and state.is_newer_version(version, active_version)
    )
    buttons = QHBoxLayout()

    details_button = QToolButton(card)
    details_button.setText(t("plugins.details"))
    details_button.clicked.connect(
        lambda _=False, e=entry, o=other_versions or []: on_details(e, o)
    )
    buttons.addWidget(details_button)
    buttons.addStretch(1)

    row = 6 if trusted else 5
    if installed_here and plugin_id not in disabled_ids:
        badge = QLabel(t("plugins.installed_badge"))
        badge.setStyleSheet("color: #2e7d32; font-weight: 600; padding-right: 8px;")
        buttons.addWidget(badge)
    elif update_available:
        badge = QLabel(t("plugins.update_available"))
        badge.setStyleSheet("color: #b26a00; font-weight: 600; padding-right: 8px;")
        buttons.addWidget(badge)
        update_button = QPushButton(t("plugins.update"))
        update_button.clicked.connect(
            lambda _=False, e=entry, b=update_button: on_install(e, b)
        )
        buttons.addWidget(update_button)
    elif plugin_id in disabled_ids:
        badge = QLabel(t("plugins.disabled_label"))
        badge.setStyleSheet("color: #b26a00; font-weight: 600; padding-right: 8px;")
        buttons.addWidget(badge)
    else:
        install_button = QPushButton(t("plugins.install"))
        if not compatible:
            install_button.setEnabled(False)
            install_button.setToolTip(t("plugins.incompatible"))
            install_button.setText(t("plugins.incompatible"))
        else:
            install_button.clicked.connect(
                lambda _=False, e=entry, b=install_button: on_install(e, b)
            )
        buttons.addWidget(install_button)

    grid.addLayout(buttons, row, 0)
    search_versions = " ".join([version, *(other_versions or [])])
    card.setProperty(
        "searchText",
        (state.search_text_for(entry) + " " + search_versions).lower(),
    )
    return card


def populate_installed(
    scroll: QScrollArea,
    *,
    installed_versions,
    active: dict[str, str],
    disabled_ids,
    on_version_change,
    on_toggle,
    on_remove,
    on_open_tool,
) -> None:
    from hpc_gui.plugins import state as plugin_state

    inner = clear_list(scroll)
    # W33 (HPC-W08-LIFE-005): the installed surface must state the real
    # enable/disable behavior — a toggle that only flips persisted state
    # without explanation is misleading.
    effect_note = QLabel(t("plugins.lifecycle_effect_note"))
    effect_note.setWordWrap(True)
    effect_note.setStyleSheet("color: #666; padding: 4px 8px;")
    effect_note.setObjectName("pluginLifecycleNote")
    inner.addWidget(effect_note)
    try:
        state_records = plugin_state.read_installed_state()
    except Exception:  # pragma: no cover - defensive
        state_records = {}

    rows = state.installed_card_rows(
        installed_versions.plugins, active, state_records
    )

    for problem in getattr(installed_versions, "problems", ()):
        label = QLabel(t("plugins.corrupt_plugin").format(name=problem.plugin_id))
        label.setWordWrap(True)
        label.setStyleSheet("color: #b00020; padding: 8px;")
        inner.addWidget(label)

    if not rows:
        if not getattr(installed_versions, "problems", ()):
            inner.addWidget(empty_label("plugins.no_installed"))
        return

    for name, plugin_id, versions, active_version, has_tool in rows:
        inner.addWidget(
            build_installed_card(
                name,
                plugin_id,
                versions,
                active_version,
                plugin_id in disabled_ids,
                has_tool,
                on_version_change=on_version_change,
                on_toggle=on_toggle,
                on_remove=on_remove,
                on_open_tool=on_open_tool,
            )
        )


def build_installed_card(
    name: str,
    plugin_id: str,
    versions: list[str],
    active_version: str | None = None,
    is_disabled: bool = False,
    has_tool: bool = False,
    *,
    on_version_change,
    on_toggle,
    on_remove,
    on_open_tool,
) -> QFrame:
    card = QFrame()
    grid = QGridLayout(card)

    active_version = active_version or (versions[0] if versions else None)
    title_text = f"{name} — {t('plugins.version')}: {active_version or ''}"
    title = QLabel(title_text)
    title.setStyleSheet("font-weight: 600;")
    grid.addWidget(title, 0, 0)
    other = ", ".join(version for version in versions if version != active_version)
    if other:
        others_label = QLabel(f"{t('plugins.other_versions')}: {other}")
        others_label.setStyleSheet("color: #666;")
        grid.addWidget(others_label, 1, 0)
    if is_disabled:
        state_label = QLabel(t("plugins.disabled_label"))
        state_label.setStyleSheet("color: #b26a00;")
        grid.addWidget(state_label, 2, 0)
    if has_tool:
        tool_label = QLabel(t("plugins.trusted_tool_label"))
        tool_label.setStyleSheet("color: #245a9a;")
        grid.addWidget(tool_label, 2, 0)

    version_row = QHBoxLayout()
    version_row.addWidget(QLabel(t("plugins.switch_version_label")))
    version_combo = QComboBox()
    version_combo.addItems(versions)
    if active_version:
        version_combo.setCurrentText(active_version)
    version_row.addWidget(version_combo)
    version_button = QPushButton()
    version_row.addWidget(version_button)
    grid.addLayout(version_row, 3, 0)

    def update_version_action(selected: str) -> None:
        if not active_version or selected == active_version:
            version_button.setText(t("plugins.rollback"))
            version_button.setEnabled(False)
            return
        version_button.setText(
            t("plugins.activate")
            if state.is_newer_version(selected, active_version)
            else t("plugins.rollback")
        )
        version_button.setEnabled(True)

    version_combo.currentTextChanged.connect(update_version_action)
    version_button.clicked.connect(
        lambda _=False: on_version_change(
            plugin_id, name, version_combo.currentText(), active_version
        )
    )
    update_version_action(version_combo.currentText())

    row = QHBoxLayout()
    row.addStretch(1)
    if has_tool and not is_disabled:
        open_tool_button = QPushButton(t("plugins.open_tool"))
        open_tool_button.clicked.connect(
            lambda _=False, pid=plugin_id: on_open_tool(pid)
        )
        row.addWidget(open_tool_button)
    toggle_button = QPushButton(
        t("plugins.enable") if is_disabled else t("plugins.disable")
    )
    toggle_button.clicked.connect(
        lambda _=False, pid=plugin_id, disabled=is_disabled: on_toggle(pid, disabled)
    )
    row.addWidget(toggle_button)
    remove_button = QPushButton(t("plugins.remove"))
    remove_button.clicked.connect(
        lambda _=False, pid=plugin_id, pname=name: on_remove(pid, pname)
    )
    grid.addLayout(row, 4, 0)
    return card


def details_installed_state(entry: dict, active: dict[str, str], disabled_ids) -> str:
    from hpc_gui.core.i18n import t as _t

    plugin_id = str(entry.get("id", ""))
    if state.is_installed(entry, active):
        return (
            _t("plugins.installed_disabled")
            if plugin_id in disabled_ids
            else _t("plugins.installed_active")
        )
    return _t("plugins.installed_not_installed")


def open_linter_tool(dialog: QDialog, installed_versions, plugin_id: str) -> None:
    """Open the approved Trusted Tool hosted in a modal dialog."""
    import logging as _logging

    from PySide6.QtWidgets import QMessageBox as _MessageBox

    _logger = _logging.getLogger("hpc_gui.ui.dialogs.plugin_manager_dialog")
    installed = next(
        (
            item
            for item in installed_versions.plugins
            if item.manifest.id == plugin_id
        ),
        None,
    )
    if installed is None:
        _MessageBox.warning(
            dialog,
            t("plugins.tool_open_failed"),
            f"{plugin_id}: {t('plugins.tool_not_installed')}",
        )
        return
    try:
        from hpc_gui.plugins.linter_tools import load_tool_for_plugin

        tool = load_tool_for_plugin(installed)
    except Exception as exc:
        _logger.warning("Could not load linter tool %s", plugin_id, exc_info=exc)
        _MessageBox.warning(
            dialog,
            t("plugins.tool_open_failed"),
            str(exc),
        )
        return

    tool_dialog = QDialog(dialog)
    tool_dialog.setWindowTitle(f"{tool.title} — {plugin_id}@{tool.version}")
    tool_dialog.resize(980, 680)
    layout = QVBoxLayout(tool_dialog)
    try:
        page = tool.page_factory(parent=tool_dialog)
    except Exception as exc:
        _logger.warning("Linter tool page creation failed for %s", plugin_id, exc_info=exc)
        _MessageBox.warning(
            dialog,
            t("plugins.tool_open_failed"),
            str(exc),
        )
        return
    layout.addWidget(page)
    tool_dialog.exec()


def populate_updates(
    scroll: QScrollArea,
    *,
    registry: dict | None,
    active: dict[str, str],
    app_version: str,
    on_install,
) -> None:
    inner = clear_list(scroll)
    updates = state.updates_for(registry, active, app_version)
    if not updates:
        inner.addWidget(empty_label("plugins.no_updates"))
        return
    for entry in updates:
        inner.addWidget(build_update_card(entry, active.get(entry["id"]), on_install))


def build_update_card(entry: dict, active_version: str | None, on_install) -> QFrame:
    card = QFrame()
    grid = QGridLayout(card)
    label = QLabel(
        f"{entry.get('name', '')}: {active_version} → v{entry.get('version')}"
    )
    grid.addWidget(label, 0, 0)
    update_row = QHBoxLayout()
    update_row.addStretch(1)
    update_button = QPushButton(t("plugins.update"))
    update_button.clicked.connect(
        lambda _=False, e=entry, b=update_button: on_install(e, b)
    )
    update_row.addWidget(update_button)
    grid.addLayout(update_row, 1, 0)
    return card
