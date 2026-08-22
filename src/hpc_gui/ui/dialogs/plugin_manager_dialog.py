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

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
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
from hpc_gui.plugins.state import remove_plugin
from hpc_gui.plugins.storage import read_active_versions
from hpc_gui.ui.async_call import AsyncCall

logger = logging.getLogger(__name__)


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

    def refresh_registry(self) -> None:
        """Fetch the official registry off the GUI thread."""
        self.refresh_button.setEnabled(False)
        self.status_label.setText(t("plugins.status_refreshing"))
        token = ("registry-refresh", id(self))
        worker = AsyncCall(token, lambda: fetch_registry_with_cache(fetcher=self._fetcher))
        self._refresh_worker = worker

        def finished(_token, result) -> None:
            if self._refresh_worker is worker:
                self._refresh_worker = None
            self._on_registry_loaded(result.registry, result.source)

        def failed(_token, exc) -> None:
            if self._refresh_worker is worker:
                self._refresh_worker = None
            logger.warning("Plugin registry refresh failed", exc_info=exc)
            self._on_registry_unavailable()

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
        self._set_status("plugins.status_offline")
        if cached is not None and not self._registry:
            self._registry = cached
            self._registry_source = "cache"
        elif not self._registry:
            self._registry = {"schema_version": 1, "plugin_api": 1, "plugins": []}
            self._registry_source = None
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

    def _populate_discover(self, active: dict[str, str]) -> None:
        inner = self._clear_list(self.discover_list)
        entries = self._entries()
        if not entries:
            inner.addWidget(
                self._empty_label(
                    "plugins.registry_unavailable"
                    if not self._registry_source
                    else "plugins.no_plugins"
                )
            )
            return
        for entry in entries:
            inner.addWidget(self._discover_card(entry, active))

    def _discover_card(self, entry: dict, active: dict[str, str]) -> QFrame:
        card = QFrame()
        card.setObjectName("pluginCard")
        grid = QGridLayout(card)

        name = f"{entry.get('name', '')} v{entry.get('version', '')}"
        title = QLabel(name)
        title.setStyleSheet("font-weight: 600;")
        grid.addWidget(title, 0, 0)

        meta_bits = [
            f"{t('plugins.publisher')}: {entry.get('publisher', '')}",
            entry.get("type", ""),
            f"{t('plugins.requires_app_label')} {entry.get('requires_app', '')}",
        ]
        meta = QLabel(" · ".join(bit for bit in meta_bits if bit))
        meta.setStyleSheet("color: #666;")
        grid.addWidget(meta, 1, 0)

        description = QLabel(entry.get("description", ""))
        description.setWordWrap(True)
        grid.addWidget(description, 2, 0)

        compatible = is_app_compatible(
            str(entry.get("requires_app", "")), self._app_version
        )
        buttons = QHBoxLayout()

        details_button = QToolButton(card)
        details_button.setText(t("plugins.details"))
        details_button.clicked.connect(lambda _=False, e=entry: self.show_details(e))
        buttons.addWidget(details_button)
        buttons.addStretch(1)

        if self._is_installed(entry, active):
            badge = QLabel(t("plugins.installed_badge"))
            badge.setStyleSheet("color: #2e7d32; font-weight: 600; padding-right: 8px;")
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

        grid.addLayout(buttons, 3, 0)
        card.setProperty("searchText", self._search_text_for(entry).lower())
        return card

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

        rows = []
        for installed in self._installed_versions.plugins:
            versions = state_records.get(installed.manifest.id, {}).get(
                "versions", [installed.manifest.version]
            )
            rows.append((installed.manifest.name, installed.manifest.id, versions))
        for plugin_id, version in sorted(active.items()):
            if plugin_id not in installed_by_id:
                rows.append((plugin_id, plugin_id, [version]))

        if not rows:
            inner.addWidget(self._empty_label("plugins.no_installed"))
            return

        for name, plugin_id, versions in rows:
            inner.addWidget(self._installed_card(name, plugin_id, versions))

    def _installed_card(
        self, name: str, plugin_id: str, versions: list[str]
    ) -> QFrame:
        card = QFrame()
        grid = QGridLayout(card)

        title = QLabel(f"{name} — {t('plugins.version')}: {versions[-1] if versions else ''}")
        title.setStyleSheet("font-weight: 600;")
        grid.addWidget(title, 0, 0)
        other = ", ".join(versions[:-1])
        if other:
            others_label = QLabel(f"{t('plugins.other_versions')}: {other}")
            others_label.setStyleSheet("color: #666;")
            grid.addWidget(others_label, 1, 0)

        row = QHBoxLayout()
        row.addStretch(1)
        remove_button = QPushButton(t("plugins.remove"))
        remove_button.clicked.connect(
            lambda _=False, pid=plugin_id, pname=name: self.remove_plugin(pid, pname)
        )
        row.addWidget(remove_button)
        grid.addLayout(row, 2, 0)
        return card

    def _populate_updates(self, active: dict[str, str]) -> None:
        inner = self._clear_list(self.updates_list)
        updates = []
        for entry in self._entries():
            current = active.get(entry.get("id", ""))
            if not current or current == entry.get("version"):
                continue
            if not is_app_compatible(str(entry.get("requires_app", "")), self._app_version):
                continue
            if self._version_greater(str(entry.get("version", "")), current):
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
    def _version_greater(candidate: str, current: str) -> bool:
        def parts(value: str) -> tuple[int, ...]:
            core = value.split("+", 1)[0].split("-", 1)[0]
            numbers = [int(p) for p in core.split(".") if p.isdigit()]
            while len(numbers) < 3:
                numbers.append(0)
            return tuple(numbers)

        return parts(candidate) > parts(current)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def show_details(self, entry: dict) -> None:
        lines = [
            f"ID: {entry.get('id', '')}",
            f"{t('plugins.publisher')}: {entry.get('publisher', '')}",
            f"{t('plugins.version')}: {entry.get('version', '')}",
            f"{t('plugins.license')}: {entry.get('license', '—')}",
            f"{t('plugins.capabilities')}: {entry.get('type', '')}",
            f"{t('plugins.requires_app_label')}: {entry.get('requires_app', '')}",
            "",
            str(entry.get("description", "")),
        ]
        capabilities = {entry.get("type", "")}
        manifest_caps = entry.get("capabilities")
        if isinstance(manifest_caps, list):
            capabilities.update(str(capability) for capability in manifest_caps)
        if "cluster-profile" in capabilities:
            lines += ["", t("plugins.cluster_commands_warning")]
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            f"{entry.get('name', '')} — {t('plugins.details')}",
            "\n".join(lines),
        )

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

        def finished(_token, _result) -> None:
            if self._install_worker is worker:
                self._install_worker = None
            self._on_install_finished(success=True, entry=entry)

        def failed(_token, exc) -> None:
            logger.warning("Plugin install failed", exc_info=exc)
            if self._install_worker is worker:
                self._install_worker = None
            self._on_install_finished(success=False, entry=entry, error=exc)

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
        super().reject()
