"""Plugin Manager dialog (Wave 05).

Browse the official declarative plugin registry, install plugins through
the exact-file installer, inspect installed plugins, and remove them.

All registry/installer work runs on the thread pool via ``AsyncCall``; the
GUI thread only builds widgets from completed results. The dialog emits
``plugins_changed`` after a successful install or removal so future waves
can refresh dependent surfaces without an app restart.

Wave M01: pure rules live in ``plugin_manager_state`` (Qt-free) and card
widgets in ``plugin_manager_cards``; this module keeps dialog composition,
service orchestration and the public API.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.plugins.installer import install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.registry_client import (
    fetch_registry_with_cache,
)
from hpc_gui.plugins.state import remove_plugin, set_plugin_disabled
from hpc_gui.plugins.storage import read_active_versions, read_disabled_ids
from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
from hpc_gui.ui.async_call import AsyncCall
from hpc_gui.ui.dialogs import plugin_manager_cards as plugin_cards
from hpc_gui.ui.dialogs import plugin_manager_state as plugin_state
from hpc_gui.ui.dialogs.plugin_manager_state import capability_label

__all__ = [
    "PLUGIN_REQUEST_URL",
    "PluginManagerDialog",
    "capability_label",
]

logger = logging.getLogger(__name__)


_INITIAL_TAB_MAP = {"discover": 0, "installed": 1, "updates": 2}


class PluginManagerDialog(QDialog):
    plugins_changed = Signal()

    def __init__(self, parent=None, *, fetcher=None, initial_tab: str = "discover"):
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
        self.status_label.setFixedWidth(110)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666;")
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

        self.discover_list = plugin_cards.make_scroll_list()
        self.tabs.addTab(self.discover_list, t("plugins.tab_discover"))
        self.installed_list = plugin_cards.make_scroll_list()
        self.tabs.addTab(self.installed_list, t("plugins.tab_installed"))
        self.updates_list = plugin_cards.make_scroll_list()
        self.tabs.addTab(self.updates_list, t("plugins.tab_updates"))

        self._installed_versions = load_installed_plugins(app_version=self._app_version)
        # Semantic initial tab selection with safe fallback to discover
        tab_index = _INITIAL_TAB_MAP.get(str(initial_tab).strip().lower(), 0)
        self.tabs.setCurrentIndex(tab_index)
        self._initial_tab = str(initial_tab).strip().lower() if str(initial_tab).strip().lower() in _INITIAL_TAB_MAP else "discover"

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

    def _is_installed(self, entry: dict, active: dict[str, str]) -> bool:
        return plugin_state.is_installed(entry, active)

    def _populate_discover(self, active: dict[str, str]) -> None:
        plugin_cards.populate_discover(
            self.discover_list,
            registry=self._registry,
            registry_source=self._registry_source,
            active=active,
            disabled_ids=read_disabled_ids(),
            app_version=self._app_version,
            on_details=self.show_details,
            on_install=self.install_plugin,
        )

    def _discover_card(
        self,
        entry: dict,
        active: dict[str, str],
        disabled_ids: set[str] | None = None,
        other_versions: list[str] | None = None,
    ) -> QFrame:
        return plugin_cards.build_discover_card(
            entry,
            active,
            disabled_ids,
            other_versions,
            app_version=self._app_version,
            on_details=self.show_details,
            on_install=self.install_plugin,
        )

    def _populate_installed(self, active: dict[str, str]) -> None:
        plugin_cards.populate_installed(
            self.installed_list,
            installed_versions=self._installed_versions,
            active=active,
            disabled_ids=read_disabled_ids(),
            on_version_change=self.change_plugin_version,
            on_toggle=self.toggle_plugin_disabled,
            on_remove=self.remove_plugin,
            on_open_tool=self.open_linter_tool,
        )

    def change_plugin_version(
        self, plugin_id: str, name: str, version: str, current_version: str
    ) -> None:
        if self._version_worker is not None or version == current_version:
            return
        rollback = not plugin_state.is_newer_version(version, current_version)
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
        self.plugins_changed.emit()
        self.rebuild_tabs()

    def open_linter_tool(self, plugin_id: str) -> None:
        """Open the approved Trusted Tool hosted in a modal dialog."""
        plugin_cards.open_linter_tool(self, self._installed_versions, plugin_id)

    def _populate_updates(self, active: dict[str, str]) -> None:
        plugin_cards.populate_updates(
            self.updates_list,
            registry=self._registry,
            active=active,
            app_version=self._app_version,
            on_install=self.install_plugin,
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def show_details(self, entry: dict, other_versions: list[str] | None = None) -> None:
        installed_state = self._details_installed_state(entry)
        lines = plugin_state.details_lines(entry, installed_state, other_versions)
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            f"{entry.get('name', '')} — {t('plugins.details')}",
            "\n".join(lines),
        )

    def _details_installed_state(self, entry: dict) -> str:
        return plugin_cards.details_installed_state(
            entry, read_active_versions(), read_disabled_ids()
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
        return plugin_state.install_summary_text(entry, self._last_install_result)

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
        return plugin_state.install_error_message(error)

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
