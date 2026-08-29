"""Plugin Manager dialog (Wave 05).

Browse the official declarative plugin registry, install plugins through
the exact-file installer, inspect installed plugins, and remove them.

All registry/installer work runs on the thread pool via ``AsyncCall``; the
GUI thread only builds widgets from completed results. The dialog emits
``plugins_changed`` after a successful install or removal so future waves
can refresh dependent surfaces without an app restart.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from packaging.version import InvalidVersion, Version
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.installer import install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.registry_client import (
    RegistryError,
    fetch_registry_with_cache,
)
from hpc_gui.plugins.state import remove_plugin, set_plugin_disabled
from hpc_gui.plugins.storage import read_active_versions, read_disabled_ids
from hpc_gui.ui.async_call import AsyncCall

logger = logging.getLogger(__name__)

# Dedicated plugin-request issue form in the official plugin registry repo.
# This is the only destination the "Request a plugin" action may open; it is
# a fixed constant and is never built from registry-controlled fields.
PLUGIN_REQUEST_URL = (
    "https://github.com/mskomek/hpc-client-gui-plugins/issues/new"
    "?template=plugin-request.yml"
)

# Human-readable labels for Plugin API v1/v2 capability identifiers. Raw
# identifiers must never appear as primary UI text.
_CAPABILITY_LABEL_KEYS = {
    "cluster-profile": "plugins.capability_cluster_profile",
    "lint-rules": "plugins.capability_lint_rules",
    "job-template": "plugins.capability_job_templates",
    "application-tools": "plugins.capability_application_tools",
    "linter-tool": "plugins.capability_linter_tool",
}


def capability_label(capability: str) -> str:
    """Translated, user-facing label for a capability identifier."""
    key = _CAPABILITY_LABEL_KEYS.get(str(capability or "").strip())
    return t(key) if key else str(capability or "")


class PluginManagerDialog(QDialog):
    plugins_changed = Signal()

    def __init__(self, parent=None, *, fetcher=None):
        super().__init__(parent)
        self._fetcher = fetcher
        self._app_version = __version__
        self._registry: dict | None = None
        self._registry_source: str | None = None
        self._install_worker: AsyncCall | None = None
        self._refresh_worker: AsyncCall | None = None
        self._version_worker: AsyncCall | None = None
        self._auto_refresh_started = False
        self._last_install_result = None

        self.setWindowTitle(t("plugins.dialog_title"))
        self.resize(950, 620)
        self.setMinimumWidth(850)

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel(t("plugins.dialog_title"))
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        header.addWidget(title)
        header.addStretch(1)

        self.status_label = QLabel("")
        header.addWidget(self.status_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(t("plugins.search_placeholder"))
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._apply_search_filter)
        header.addWidget(self.search_box, 1)

        self.request_button = QPushButton(t("plugins.request_plugin"))
        self.request_button.setToolTip(t("plugins.request_plugin_tip"))
        self.request_button.clicked.connect(self.open_plugin_requests)
        header.addWidget(self.request_button)

        self.refresh_button = QPushButton(t("plugins.refresh"))
        self.refresh_button.clicked.connect(self.refresh_registry)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.discover_list = self._make_scroll_list()
        self.tabs.addTab(self.discover_list, t("plugins.tab_discover"))
        self.installed_list = self._make_scroll_list()
        self.tabs.addTab(self.installed_list, t("plugins.tab_installed"))
        self.updates_list = self._make_scroll_list()
        self.tabs.addTab(self.updates_list, t("plugins.tab_updates"))

        self._installed_versions = load_installed_plugins(app_version=self._app_version)

    # ------------------------------------------------------------------
    # Widget helpers
    # ------------------------------------------------------------------

    def _make_scroll_list(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container.setLayout(QVBoxLayout())
        container.layout().setAlignment(Qt.AlignTop)
        scroll.setWidget(container)
        return scroll

    def _clear_list(self, scroll: QScrollArea) -> QVBoxLayout:
        container = scroll.widget()
        inner = container.layout()
        while inner.count():
            item = inner.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        return inner

    def _empty_label(self, key: str) -> QLabel:
        label = QLabel(t(key))
        label.setStyleSheet("color: #666; padding: 12px;")
        return label

    # ------------------------------------------------------------------
    # Registry refresh
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        # First open automatically starts exactly one registry load so users
        # never face empty tabs; re-showing the same dialog never duplicates
        # the request.
        super().showEvent(event)
        if not self._auto_refresh_started:
            self._auto_refresh_started = True
            if self._refresh_worker is None and self._registry is None:
                self.refresh_registry()

    def open_plugin_requests(self) -> bool:
        """Open the dedicated plugin-request issue form.

        The destination is the fixed PLUGIN_REQUEST_URL constant (HTTPS,
        official GitHub host, plugin repository only). Returns True when the
        browser was opened; a visible error is shown otherwise.
        """
        expected = PLUGIN_REQUEST_URL
        opened = False
        if self._is_allowed_plugin_request_url(expected):
            try:
                opened = QDesktopServices.openUrl(QUrl(expected))
            except Exception:
                logger.exception("Opening the plugin request URL failed")
                opened = False
        if not opened:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                t("plugins.dialog_title"),
                t("plugins.request_plugin_failed"),
            )
        return opened

    @staticmethod
    def _is_allowed_plugin_request_url(url: str) -> bool:
        return url == PLUGIN_REQUEST_URL

    def refresh_registry(self) -> None:
        """Fetch the official registry off the GUI thread."""
        if self._refresh_worker is not None:
            return  # one in-flight refresh at a time
        self.refresh_button.setEnabled(False)
        self.status_label.setText(t("plugins.status_loading"))
        token = ("registry-refresh", id(self))
        worker = AsyncCall(token, lambda: fetch_registry_with_cache(fetcher=self._fetcher))
        self._refresh_worker = worker

        def finished(_token, result) -> None:
            if self._refresh_worker is worker:
                self._refresh_worker = None
            try:
                self._on_registry_loaded(result.registry, result.source)
            except RuntimeError:
                logger.debug("Registry load finished after dialog was closed")

        def failed(_token, exc) -> None:
            if self._refresh_worker is worker:
                self._refresh_worker = None
            logger.warning("Plugin registry refresh failed", exc_info=exc)
            try:
                self._on_registry_unavailable()
            except RuntimeError:
                logger.debug("Registry failure handled after dialog was closed")

        worker.signals.finished.connect(finished)
        worker.signals.failed.connect(failed)
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().start(worker)

    def _set_status(self, key: str) -> None:
        self.status_label.setText(t(key))

    def _on_registry_loaded(self, registry: dict, source: str) -> None:
        self._registry = registry
        self._registry_source = source
        self.refresh_button.setEnabled(True)
        self._set_status(
            "plugins.status_online" if source == "network" else "plugins.status_cached"
        )
        self.rebuild_tabs()

    def _on_registry_unavailable(self) -> None:
        cached = None
        try:
            from hpc_gui.plugins.registry_client import read_cached_registry

            cached = read_cached_registry()
        except Exception:  # pragma: no cover - defensive
            cached = None
        self.refresh_button.setEnabled(True)
        if cached is not None and not self._registry:
            self._registry = cached
            self._registry_source = "cache"
            self._set_status("plugins.status_cached")
        elif not self._registry:
            self._registry = {"schema_version": 1, "plugin_api": 1, "plugins": []}
            self._registry_source = None
            self._set_status("plugins.status_offline")
        self.rebuild_tabs()

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def rebuild_tabs(self) -> None:
        self._installed_versions = load_installed_plugins(app_version=self._app_version)
        active = read_active_versions()
        self._populate_discover(active)
        self._populate_installed(active)
        self._populate_updates(active)

    @staticmethod
    def _entry_sort_key(entry: dict):
        return str(entry.get("name") or entry.get("id") or "")

    def _entries(self) -> list[dict]:
        if not self._registry:
            return []
        return sorted(
            [e for e in self._registry.get("plugins", []) if isinstance(e, dict)],
            key=self._entry_sort_key,
        )

    def _is_installed(self, entry: dict, active: dict[str, str]) -> bool:
        return (
            entry.get("id") in active and active[entry["id"]] == entry.get("version")
        )

    @staticmethod
    def _parse_version(value: object) -> Version | None:
        try:
            return Version(str(value or ""))
        except (InvalidVersion, TypeError):
            return None

    def _grouped_latest(self) -> list[tuple[dict, list[str]]]:
        """Group registry entries by plugin id.

        Returns one ``(entry, other_versions)`` pair per plugin: the latest
        app-compatible version is the primary card; when no version is
        compatible, the highest version is shown as an incompatible card.
        Registry order never decides which version is latest. Older
        versions stay reachable through the details view.
        """
        groups: dict[str, list[dict]] = {}
        for entry in self._entries():
            groups.setdefault(str(entry.get("id", "")), []).append(entry)
        grouped: list[tuple[dict, list[str]]] = []
        for entries in groups.values():
            parsed: list[tuple[Version | None, dict]] = [
                (self._parse_version(entry.get("version")), entry) for entry in entries
            ]
            with_versions = [item for item in parsed if item[0] is not None]
            pool = (
                [item for item in with_versions
                 if is_app_compatible(str(item[1].get("requires_app", "")), self._app_version)]
                or with_versions
                or parsed
            )
            best_version, best = max(
                pool,
                key=lambda item: item[0] if item[0] is not None else Version("0"),
            )
            others = sorted(
                (str(entry.get("version")) for _, entry in parsed
                 if entry is not best and entry.get("version") != best.get("version")),
                key=lambda value: Version(value),
                reverse=True,
            )
            grouped.append((best, others))
        grouped.sort(key=lambda item: self._entry_sort_key(item[0]))
        return grouped

    def _populate_discover(self, active: dict[str, str]) -> None:
        inner = self._clear_list(self.discover_list)
        grouped = self._grouped_latest()
        if not grouped:
            inner.addWidget(
                self._empty_label(
                    "plugins.registry_unavailable"
                    if not self._registry_source
                    else "plugins.no_plugins"
                )
            )
            return
        disabled_ids = read_disabled_ids()
        for entry, others in grouped:
            inner.addWidget(self._discover_card(entry, active, disabled_ids, others))

    def _discover_card(
        self,
        entry: dict,
        active: dict[str, str],
        disabled_ids: set[str] | None = None,
        other_versions: list[str] | None = None,
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

        compatible = is_app_compatible(
            str(entry.get("requires_app", "")), self._app_version
        )
        meta_bits = [
            f"{t('plugins.publisher')}: {entry.get('publisher', '')}",
            f"{t('plugins.requires_app_label')} {entry.get('requires_app', '')}",
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

        # Capability badges (translated; raw identifiers never shown).
        caps_row = QHBoxLayout()
        caps_row.setContentsMargins(0, 2, 0, 2)
        for capability in self._entry_capabilities(entry):
            badge = QLabel(capability_label(capability))
            badge.setProperty("capabilityBadge", True)
            badge.setStyleSheet(
                "color: #455a64; background: #eceff1; border-radius: 4px;"
                "padding: 1px 6px; font-size: 11px;"
            )
            caps_row.addWidget(badge)
        caps_row.addStretch(1)
        grid.addLayout(caps_row, 3, 0)

        if other_versions:
            others = QLabel(
                f"{t('plugins.other_versions_catalog')}: {', '.join(other_versions)}"
            )
            others.setStyleSheet("color: #666;")
            grid.addWidget(others, 4, 0)

        installed_here = self._is_installed(entry, active)
        active_version = active.get(plugin_id)
        update_available = bool(
            compatible
            and active_version
            and not installed_here
            and self._is_newer_version(version, active_version)
        )
        buttons = QHBoxLayout()

        details_button = QToolButton(card)
        details_button.setText(t("plugins.details"))
        details_button.clicked.connect(
            lambda _=False, e=entry, o=other_versions or []: self.show_details(e, o)
        )
        buttons.addWidget(details_button)
        buttons.addStretch(1)

        row = 5
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
                lambda _=False, e=entry, b=update_button: self.install_plugin(e, b)
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
                    lambda _=False, e=entry, b=install_button: self.install_plugin(e, b)
                )
            buttons.addWidget(install_button)

        grid.addLayout(buttons, row, 0)
        search_versions = " ".join([version, *(other_versions or [])])
        card.setProperty(
            "searchText",
            (self._search_text_for(entry) + " " + search_versions).lower(),
        )
        return card

    @staticmethod
    def _entry_capabilities(entry: dict) -> list[str]:
        """Capabilities for display: the authoritative array when present,
        otherwise the legacy single ``type`` field."""
        capabilities = entry.get("capabilities")
        if isinstance(capabilities, list) and capabilities:
            return [str(item) for item in capabilities if str(item)]
        legacy = str(entry.get("type", "") or "")
        return [legacy] if legacy else []

    @staticmethod
    def _search_text_for(entry: dict) -> str:
        return " ".join(
            str(entry.get(key, "") or "")
            for key in ("name", "id", "description", "publisher", "type")
        )

    def _populate_installed(self, active: dict[str, str]) -> None:
        inner = self._clear_list(self.installed_list)
        installed_by_id = {
            installed.manifest.id: installed
            for installed in self._installed_versions.plugins
        }
        state_records = {}
        try:
            from hpc_gui.plugins.state import read_installed_state

            state_records = read_installed_state()
        except Exception:  # pragma: no cover - defensive
            state_records = {}
        disabled = read_disabled_ids()

        rows = []
        for installed in self._installed_versions.plugins:
            versions = state_records.get(installed.manifest.id, {}).get(
                "versions", [installed.manifest.version]
            )
            rows.append((installed.manifest.name, installed.manifest.id, versions))
        for plugin_id, version in sorted(active.items()):
            if plugin_id not in installed_by_id:
                rows.append((plugin_id, plugin_id, [version]))

        for problem in getattr(self._installed_versions, "problems", ()):
            label = QLabel(t("plugins.corrupt_plugin").format(name=problem.plugin_id))
            label.setWordWrap(True)
            label.setStyleSheet("color: #b00020; padding: 8px;")
            inner.addWidget(label)

        if not rows:
            if not getattr(self._installed_versions, "problems", ()):
                inner.addWidget(self._empty_label("plugins.no_installed"))
            return

        for name, plugin_id, versions in rows:
            versions = sorted(
                set(versions) | ({active[plugin_id]} if plugin_id in active else set()),
                key=lambda value: self._parse_version(value) or Version("0"),
                reverse=True,
            )
            installed = installed_by_id.get(plugin_id)
            has_tool = bool(
                installed is not None
                and "linter-tool" in getattr(installed.manifest, "capabilities", ())
                and getattr(installed, "linter_engine", None)
            )
            inner.addWidget(
                self._installed_card(
                    name, plugin_id, versions, active.get(plugin_id), plugin_id in disabled,
                    has_tool=has_tool,
                )
            )

    def _installed_card(
        self,
        name: str,
        plugin_id: str,
        versions: list[str],
        active_version: str | None = None,
        is_disabled: bool = False,
        has_tool: bool = False,
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
                if self._is_newer_version(selected, active_version)
                else t("plugins.rollback")
            )
            version_button.setEnabled(True)

        version_combo.currentTextChanged.connect(update_version_action)
        version_button.clicked.connect(
            lambda _=False: self.change_plugin_version(
                plugin_id, name, version_combo.currentText(), active_version
            )
        )
        update_version_action(version_combo.currentText())

        row = QHBoxLayout()
        row.addStretch(1)
        if has_tool and not is_disabled:
            open_tool_button = QPushButton(t("plugins.open_tool"))
            open_tool_button.clicked.connect(
                lambda _=False, pid=plugin_id: self.open_linter_tool(pid)
            )
            row.addWidget(open_tool_button)
        toggle_button = QPushButton(
            t("plugins.enable") if is_disabled else t("plugins.disable")
        )
        toggle_button.clicked.connect(
            lambda _=False, pid=plugin_id, disabled=is_disabled: self.toggle_plugin_disabled(
                pid, disabled
            )
        )
        row.addWidget(toggle_button)
        remove_button = QPushButton(t("plugins.remove"))
        remove_button.clicked.connect(
            lambda _=False, pid=plugin_id, pname=name: self.remove_plugin(pid, pname)
        )
        row.addWidget(remove_button)
        grid.addLayout(row, 4, 0)
        return card

    def change_plugin_version(
        self, plugin_id: str, name: str, version: str, current_version: str
    ) -> None:
        if self._version_worker is not None or version == current_version:
            return
        rollback = not self._is_newer_version(version, current_version)
        from PySide6.QtWidgets import QMessageBox

        key = (
            "plugins.version_rollback_confirm_text"
            if rollback
            else "plugins.version_activate_confirm_text"
        )
        if QMessageBox.question(
            self,
            t("plugins.version_switch_confirm_title"),
            t(key).format(name=name, version=version, current=current_version),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        from hpc_gui.plugins.state import activate_version

        self._set_status("plugins.activating")
        worker = AsyncCall(
            ("plugin-version", plugin_id, version),
            lambda: activate_version(plugin_id, version),
        )
        self._version_worker = worker

        def finished(_token, _result) -> None:
            if self._version_worker is worker:
                self._version_worker = None
            QMessageBox.information(
                self,
                t("plugins.version_switch_confirm_title"),
                t("plugins.version_switch_success").format(name=name, version=version),
            )
            self.plugins_changed.emit()
            self.rebuild_tabs()

        def failed(_token, _error) -> None:
            if self._version_worker is worker:
                self._version_worker = None
            QMessageBox.warning(
                self,
                t("plugins.version_switch_confirm_title"),
                t("plugins.version_switch_failed").format(name=name, version=version),
            )
            self.rebuild_tabs()

        worker.signals.finished.connect(finished)
        worker.signals.failed.connect(failed)
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().start(worker)

    def toggle_plugin_disabled(self, plugin_id: str, currently_disabled: bool) -> None:
        try:
            set_plugin_disabled(plugin_id, not currently_disabled)
        except Exception as exc:
            logger.warning("Could not toggle plugin %s", plugin_id, exc_info=exc)
            return
        self.rebuild_tabs()

    def open_linter_tool(self, plugin_id: str) -> None:
        """Open a Plugin API v2 linter tool hosted in a modal dialog."""
        from PySide6.QtWidgets import QMessageBox

        installed = next(
            (
                item
                for item in self._installed_versions.plugins
                if item.manifest.id == plugin_id
            ),
            None,
        )
        if installed is None:
            QMessageBox.warning(
                self,
                t("plugins.tool_open_failed"),
                f"{plugin_id}: {t('plugins.tool_not_installed')}",
            )
            return
        try:
            from hpc_gui.plugins.linter_tools import load_tool_for_plugin

            tool = load_tool_for_plugin(installed)
        except Exception as exc:
            logger.warning("Could not load linter tool %s", plugin_id, exc_info=exc)
            QMessageBox.warning(
                self,
                t("plugins.tool_open_failed"),
                str(exc),
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{tool.title} — {plugin_id}@{tool.version}")
        dialog.resize(980, 680)
        layout = QVBoxLayout(dialog)
        try:
            page = tool.page_factory(parent=dialog)
        except Exception as exc:
            logger.warning("Linter tool page creation failed for %s", plugin_id, exc_info=exc)
            QMessageBox.warning(
                self,
                t("plugins.tool_open_failed"),
                str(exc),
            )
            return
        layout.addWidget(page)
        dialog.exec()

    def _populate_updates(self, active: dict[str, str]) -> None:
        inner = self._clear_list(self.updates_list)
        updates = []
        for entry, _others in self._grouped_latest():
            plugin_id = str(entry.get("id", ""))
            current = active.get(plugin_id)
            if not current or current == entry.get("version"):
                continue
            if not is_app_compatible(str(entry.get("requires_app", "")), self._app_version):
                continue
            if self._is_newer_version(str(entry.get("version", "")), current):
                updates.append(entry)
        if not updates:
            inner.addWidget(self._empty_label("plugins.no_updates"))
            return
        for entry in updates:
            card = QFrame()
            grid = QGridLayout(card)
            label = QLabel(
                f"{entry.get('name', '')}: {active.get(entry['id'])} → v{entry.get('version')}"
            )
            grid.addWidget(label, 0, 0)
            update_row = QHBoxLayout()
            update_row.addStretch(1)
            update_button = QPushButton(t("plugins.update"))
            update_button.clicked.connect(
                lambda _=False, e=entry, b=update_button: self.install_plugin(e, b)
            )
            update_row.addWidget(update_button)
            grid.addLayout(update_row, 1, 0)
            inner.addWidget(card)

    @staticmethod
    def _is_newer_version(candidate: str, current: str) -> bool:
        """PEP 440 comparison; unparseable versions never count as updates."""
        try:
            return Version(candidate) > Version(current)
        except InvalidVersion:
            return False

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def show_details(self, entry: dict, other_versions: list[str] | None = None) -> None:
        installed_state = self._details_installed_state(entry)
        lines = [
            f"ID: {entry.get('id', '')}",
            f"{t('plugins.publisher')}: {entry.get('publisher', '')}",
            f"{t('plugins.version')}: {entry.get('version', '')}",
            f"{t('plugins.license')}: {entry.get('license', '—')}",
            f"{t('plugins.requires_app_label')}: {entry.get('requires_app', '')}",
            (
                f"{t('plugins.capabilities')}: "
                + ", ".join(
                    capability_label(capability)
                    for capability in self._entry_capabilities(entry)
                )
            ),
            f"{t('plugins.source_label')}: {t('plugins.source_official_registry')}",
            f"{t('plugins.installed_state')}: {installed_state}",
        ]
        if other_versions:
            lines.append(
                f"{t('plugins.other_versions_catalog')}: {', '.join(other_versions)}"
            )
        lines += [
            "",
            str(entry.get("description", "")),
        ]
        if "cluster-profile" in set(self._entry_capabilities(entry)):
            lines += ["", t("plugins.cluster_commands_warning")]
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            f"{entry.get('name', '')} — {t('plugins.details')}",
            "\n".join(lines),
        )

    def _details_installed_state(self, entry: dict) -> str:
        active = read_active_versions()
        disabled_ids = read_disabled_ids()
        plugin_id = str(entry.get("id", ""))
        if self._is_installed(entry, active):
            return (
                t("plugins.installed_disabled")
                if plugin_id in disabled_ids
                else t("plugins.installed_active")
            )
        return t("plugins.installed_not_installed")

    def install_plugin(self, entry: dict, button: QPushButton) -> None:
        """Install one registry entry off the GUI thread."""
        if self._install_worker is not None:
            return
        button.setEnabled(False)
        button.setText(t("plugins.installing"))
        self._set_status("plugins.installing")
        token = ("plugin-install", id(entry))
        worker = AsyncCall(
            token,
            lambda: install_plugin_from_registry(
                entry, fetcher=self._fetcher, app_version=self._app_version
            ),
        )
        self._install_worker = worker

        def finished(_token, result) -> None:
            if self._install_worker is worker:
                self._install_worker = None
            self._last_install_result = result
            try:
                self._on_install_finished(success=True, entry=entry)
            except RuntimeError:
                logger.debug("Install finished after dialog was closed")

        def failed(_token, exc) -> None:
            logger.warning("Plugin install failed", exc_info=exc)
            if self._install_worker is worker:
                self._install_worker = None
            try:
                self._on_install_finished(success=False, entry=entry, error=exc)
            except RuntimeError:
                logger.debug("Install failure handled after dialog was closed")

        worker.signals.finished.connect(finished)
        worker.signals.failed.connect(failed)
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().start(worker)

    def _on_install_finished(
        self, *, success: bool, entry: dict, error: Exception | None = None
    ) -> None:
        self._set_status(
            "plugins.status_online" if self._registry_source == "network" else "plugins.status_cached"
        )
        if success:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                t("plugins.dialog_title"),
                self._install_summary_text(entry),
            )
            self.plugins_changed.emit()
        else:
            message = self._error_text(error)
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                t("plugins.dialog_title"),
                message.format(name=entry.get("name", "")),
            )
        self.rebuild_tabs()

    def _install_summary_text(self, entry: dict) -> str:
        """Human-readable install/update summary from loader data.

        Counts come only from the freshly loaded installed plugin; when the
        detailed counts are unavailable a correct generic message is shown.
        """
        result = self._last_install_result
        installed = getattr(result, "installed", None) if result else None
        manifest = getattr(installed, "manifest", None)
        name = (
            getattr(manifest, "name", None)
            or str(entry.get("name", ""))
            or t("plugins.action")
        )
        counts = self._capability_counts(installed)
        if not counts or not any(counts.values()):
            return t("plugins.install_generic").format(name=name)
        parts = [
            t("plugins.summary_cluster_profiles").format(count=counts["cluster"]),
            t("plugins.summary_job_templates").format(count=counts["templates"]),
            t("plugins.summary_lint_rule_packs").format(count=counts["lint"]),
        ]
        details = ", ".join(parts[:-1])
        if len(parts) > 1:
            details += f" {t('common.and')} " + parts[-1]
        else:
            details = parts[0]
        return t("plugins.install_summary").format(name=name, details=details)

    @staticmethod
    def _capability_counts(installed) -> dict[str, int]:
        cluster = len(tuple(getattr(installed, "cluster_profiles", ()) or ()))
        lint_index = getattr(installed, "lint_index", None)
        lint = 1 if isinstance(lint_index, dict) and lint_index.get("rules") is not None else 0
        templates_index = getattr(installed, "job_templates_index", None)
        templates = 0
        if isinstance(templates_index, dict):
            raw_templates = templates_index.get("templates")
            if isinstance(raw_templates, list):
                templates = len(raw_templates)
        return {"cluster": cluster, "lint": lint, "templates": templates}

    def remove_plugin(self, plugin_id: str, display_name: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        answer = QMessageBox.question(
            self,
            t("plugins.remove_confirm_title"),
            t("plugins.remove_confirm_text").format(name=display_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            remove_plugin(plugin_id)
        except Exception as exc:
            logger.warning("Plugin removal failed for %s", plugin_id, exc_info=exc)
            QMessageBox.warning(
                self, t("plugins.dialog_title"), t("plugins.invalid_plugin")
            )
            return
        self.plugins_changed.emit()
        self.rebuild_tabs()

    # ------------------------------------------------------------------
    # Errors / filtering
    # ------------------------------------------------------------------

    def _error_text(self, error: Exception | None) -> str:
        text = str(error or "")
        lowered = text.lower()
        if isinstance(error, RegistryError) or "registry" in lowered:
            return t("plugins.registry_unavailable")
        if "sha-256" in lowered or "sha256" in lowered or "size" in lowered:
            return t("plugins.verification_failed").format(name="")
        if "requires app" in lowered or "incompatible" in lowered:
            return t("plugins.incompatible")
        if "plugin api" in lowered or "plugin_api" in lowered:
            return t("plugins.unsupported_api")
        if "identity" in lowered or "invalid" in lowered:
            return t("plugins.invalid_plugin")
        return t("plugins.install_failed").format(name="")

    def _apply_search_filter(self, text: str) -> None:
        needle = text.strip().lower()
        container = self.discover_list.widget()
        if container is None:
            return
        for card in container.findChildren(QFrame):
            search_value = card.property("searchText")
            if isinstance(search_value, str):
                card.setVisible(not needle or needle in search_value)

    def reject(self) -> None:  # safe shutdown even with a worker in flight
        self._refresh_worker = None
        self._install_worker = None
        self._version_worker = None
        super().reject()
