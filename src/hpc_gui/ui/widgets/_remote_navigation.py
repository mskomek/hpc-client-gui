"""Remote navigation leaf for the file-manager remote panel.

Owns ``RemoteNavigationMixin``: directory tabs, the path field, session
handling, per-profile favorites/history, parent navigation, and navigation
control states. Listing rendering and refresh entry points live in the
listing/tree-view leaves and are reached via ``self``.

Imports Qt widgets and lower-level core/config/services only — never the local
panel, FTP widget, controllers, or another branch's private implementation.
"""

from __future__ import annotations

from hpc_gui.config.storage import get_profile_id
from hpc_gui.core.i18n import t
from hpc_gui.services.remote_navigation_store import navigation_store_for_profile


class RemoteNavigationMixin:
    """Directory navigation + session ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    current_dir: str
    _category_dir: str
    _pending_select_name: str

    @staticmethod
    def _directory_tab_label(remote_dir: str) -> str:
        cleaned = (remote_dir or "/").rstrip("/") or "/"
        return cleaned.rsplit("/", 1)[-1] or cleaned

    def _on_directory_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        remote_dir = str(self.directory_tabs.tabData(index) or "")  # type: ignore[attr-defined]
        if not remote_dir:
            return
        previous = self.current_dir
        self.current_dir = remote_dir
        self._category_dir = remote_dir
        self.path.setText(remote_dir)  # type: ignore[attr-defined]
        if remote_dir != previous:
            self.directoryChanged.emit(remote_dir)  # type: ignore[attr-defined]
        self._refresh_from_ui()  # type: ignore[attr-defined]

    def _close_directory_tab(self, index: int) -> None:
        """Close only additional directory tabs; keep one working tab open."""
        if self.directory_tabs.count() <= 1 or index < 0:  # type: ignore[attr-defined]
            return
        self.directory_tabs.removeTab(index)  # type: ignore[attr-defined]

    def open_directory_in_new_tab(self, remote_dir: str) -> bool:
        if not self.session or not self.session.get("files"):
            return False
        target = (remote_dir or "").rstrip("/") or "/"
        if not target:
            return False
        index = self._find_directory_tab(target)
        if index < 0:
            index = self.directory_tabs.addTab(self._directory_tab_label(target))  # type: ignore[attr-defined]
            self.directory_tabs.setTabData(index, target)  # type: ignore[attr-defined]
        changed = self.directory_tabs.currentIndex() != index  # type: ignore[attr-defined]
        self.directory_tabs.setCurrentIndex(index)  # type: ignore[attr-defined]
        previous = self.current_dir
        self.current_dir = target
        self._category_dir = target
        self.path.setText(target)  # type: ignore[attr-defined]
        if not changed:
            self._refresh_from_ui()  # type: ignore[attr-defined]
        if self.current_dir != previous:
            self.directoryChanged.emit(self.current_dir)  # type: ignore[attr-defined]
        self._update_navigation_controls()  # type: ignore[attr-defined]
        return True

    def _find_directory_tab(self, remote_dir: str) -> int:
        target = (remote_dir or "").rstrip("/") or "/"
        for index in range(self.directory_tabs.count()):  # type: ignore[attr-defined]
            if self.directory_tabs.tabData(index) == target:  # type: ignore[attr-defined]
                return index
        return -1

    def _open_path_field(self) -> None:
        self.set_dir(self.path.text())  # type: ignore[attr-defined]

    def set_session(self, session):
        self.session = session
        self._directory_cache.clear()  # type: ignore[attr-defined]
        self._navigation_store = None  # type: ignore[attr-defined]
        self._update_navigation_controls()

    # ---- favorites and history -----------------------------------------
    def _navigation(self):
        """The active profile's favorites/history store, or None."""
        store = getattr(self, "_navigation_store", None)
        if store is not None:
            return store
        profile_name = str((self.session or {}).get("profile_name", "")).strip()
        if not profile_name:
            return None
        store = navigation_store_for_profile(get_profile_id(profile_name) or "")
        self._navigation_store = store  # type: ignore[attr-defined]
        return store

    def _record_navigation_visit(self, remote_dir: str) -> None:
        """Remember a directory that actually opened."""
        store = self._navigation()
        if store is not None and remote_dir:
            store.record_visit(remote_dir)

    def _navigate_to_favorite(self, path: str, kind: str) -> None:
        # A favorite means "take me there", not "open it": a file favorite
        # lands in its parent directory with the file selected.
        if kind == "file":
            self.set_dir(self._parent_remote_dir(path))  # type: ignore[attr-defined]
            self._pending_select_name = self._basename(path)
        else:
            self.set_dir(path)

    @staticmethod
    def _basename(path: str) -> str:
        clean = (path or "/").rstrip("/") or "/"
        return clean.rsplit("/", 1)[-1] or clean

    def _populate_favorites_menu(self) -> None:
        menu = self.btn_favorites.menu()
        menu.clear()
        store = self._navigation()
        if store is None:
            menu.addAction(
                t("dirs.favorites_unavailable")          ).setEnabled(False)
            return
        favorites = store.favorites()
        for item in favorites:
            path = str(item.get("path", ""))
            kind = str(item.get("kind", "directory"))
            action = menu.addAction(f"{item.get('label') or self._basename(path)}\t{path}")
            action.triggered.connect(
                lambda _checked=False, p=path, k=kind: self._navigate_to_favorite(p, k)
            )
        if favorites:
            menu.addSeparator()
        current = self._category_dir or self.current_dir
        if store.is_favorite(current):
            label = (
                t("dirs.favorite_remove")            )
            menu.addAction(label).triggered.connect(
                lambda _checked=False, p=current: store.remove_favorite(p)
            )
        else:
            label = (
                t("dirs.favorite_add")
            )
            menu.addAction(label).triggered.connect(
                lambda _checked=False, p=current: store.add_favorite(p, "directory")
            )

    def _populate_history_menu(self) -> None:
        menu = self.btn_history.menu()
        menu.clear()
        store = self._navigation()
        if store is None:
            menu.addAction(
                t("dirs.history_unavailable")        ).setEnabled(False)
            return
        entries = store.history()
        for item in entries:
            path = str(item.get("path", ""))
            action = menu.addAction(f"{self._basename(path)}\t{path}")
            action.triggered.connect(lambda _checked=False, p=path: self.set_dir(p))
        if entries:
            menu.addSeparator()
        label = (
            t("dirs.history_clear")       )
        menu.addAction(label).triggered.connect(lambda _checked=False: store.clear_history())

    def set_dir(self, remote_dir: str):
        target = (remote_dir or "").rstrip("/") or "/"
        previous = self.current_dir
        self.current_dir = target
        self._category_dir = target
        signals_were_blocked = self.directory_tabs.blockSignals(True)  # type: ignore[attr-defined]
        if self.directory_tabs.count() == 0:  # type: ignore[attr-defined]
            index = self.directory_tabs.addTab(self._directory_tab_label(target))  # type: ignore[attr-defined]
            self.directory_tabs.setTabData(index, target)  # type: ignore[attr-defined]
            self.directory_tabs.setCurrentIndex(index)  # type: ignore[attr-defined]
        else:
            index = max(0, self.directory_tabs.currentIndex())  # type: ignore[attr-defined]
            self.directory_tabs.setTabText(index, self._directory_tab_label(target))  # type: ignore[attr-defined]
            self.directory_tabs.setTabData(index, target)  # type: ignore[attr-defined]
        self.directory_tabs.blockSignals(signals_were_blocked)  # type: ignore[attr-defined]
        self.path.setText(target)  # type: ignore[attr-defined]
        if target != previous:
            self.directoryChanged.emit(target)  # type: ignore[attr-defined]
        self._update_navigation_controls()
        if bool(getattr(self.session.get("files"), "supports_progressive_listing", False)):
            self.refresh_async()  # type: ignore[attr-defined]
        else:
            self.refresh()  # type: ignore[attr-defined]

    def _remote_parent_dir(self, remote_dir: str) -> str:
        cleaned = (remote_dir or "").rstrip("/")
        if not cleaned or cleaned == "/":
            return ""
        parent = cleaned.rsplit("/", 1)[0]
        return parent or "/"

    def _update_navigation_controls(self) -> None:
        has_session = bool(self.session and self.session.get("connected"))
        has_parent = bool(self._remote_parent_dir(self.current_dir)) if has_session else False
        if hasattr(self, "btn_parent"):
            self.btn_parent.setEnabled(has_parent)  # type: ignore[attr-defined]
        if hasattr(self, "btn_new_folder"):
            self.btn_new_folder.setEnabled(bool(has_session and self.current_dir))  # type: ignore[attr-defined]
        if hasattr(self, "btn_new_file"):
            self.btn_new_file.setEnabled(bool(has_session and self.current_dir))  # type: ignore[attr-defined]
        if hasattr(self, "btn_template_upload"):
            self.btn_template_upload.setEnabled(bool(has_session and self.current_dir))  # type: ignore[attr-defined]

    def go_parent(self):
        parent = self._remote_parent_dir(self.current_dir)
        if not parent:
            return
        self.set_dir(parent)


__all__ = [
    "RemoteNavigationMixin",
]
