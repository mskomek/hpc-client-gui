"""FTP session leaf for the file-manager FTP widget.

Owns ``FtpSessionMixin``: provider storage panels, session application, sync
settings reader, titles/labels, settings apply, transfer-mode accessors, cache
clearing, and the default-location menu. Panel construction and signal wiring
in ``__init__`` stay in the facade; everything here is reached via ``self``.

Imports Qt plus lower-level config/services/i18n only — never local-panel
internals, FTP internals of other leaves (beyond the documented menu-guard
import), controllers, or other branches. The shiboken menu guard is imported
from the sibling ``_ftp_activity_menus`` module: same FTP branch,
one-directional edge, no cycle.
"""

from __future__ import annotations

from hpc_gui.config.storage import get_ftp_transfer_type

import os

from PySide6.QtWidgets import QMenu

from hpc_gui.config.file_manager_profile import normalize_file_manager_settings
from hpc_gui.config.system_profile import (
    ProviderContext,
    normalize_system_settings,
    resolve_provider_path,
)
from hpc_gui.core.i18n import t
from hpc_gui.services.provider_path_resolver import ProviderPathResolver, RemotePathResult
from hpc_gui.services.transfer_mode import ASCII, AUTO, BINARY, resolve_transfer_mode
from hpc_gui.ui.widgets._ftp_activity_menus import _exec_temporary_menu
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel


class FtpSessionMixin:
    """Session/host ownership (mixed into ``FtpWidget``)."""

    session: object

    def _add_provider_storage_panels(self, session, context: ProviderContext) -> None:
        for key in tuple(self.remote_panels):
            if key in {"scratch", "home"}:
                continue
            panel = self.remote_panels.pop(key)
            self.accordion.remove_section(key)
            panel.shutdown()
        cfg = session.get("cfg") or {}
        provider = getattr(cfg, "provider_template", {}) or {}
        remote_resolver = ProviderPathResolver(session.get("ssh")) if session.get("ssh") is not None else None
        for area in provider.get("storage", []) if isinstance(provider, dict) else []:
            if not isinstance(area, dict) or area.get("enabled") is False:
                continue
            key = str(area.get("id") or "").strip()
            if not key or key in self.remote_panels:
                continue
            template = str(area.get("path_template") or "")
            result = resolve_provider_path(template, context)
            resolver = area.get("resolver")
            if not template and isinstance(resolver, dict) and resolver.get("type") == "remote-environment":
                variable = str(resolver.get("variable") or "")
                result = remote_resolver.resolve(variable) if remote_resolver is not None else RemotePathResult("unavailable", reason="not connected")
            panel = RemoteDirPanel()
            panel.set_session(session)
            panel.set_transfer_mode_provider(self.current_transfer_mode)
            panel.set_transfer_dialog_visible(False)
            panel.open_file.connect(self.openFileRequested)
            panel.file_activated.connect(self._download_remote_path)
            panel.download_requested.connect(lambda paths, panel=panel: self._download_remote_paths(panel, paths))
            panel.save_as_requested.connect(lambda paths, panel=panel: self._save_remote_paths_as(panel, paths))
            panel.submit_requested.connect(self.submitRequested)
            panel.batch_submit_requested.connect(self.batchSubmitRequested)
            panel.batch_shell_requested.connect(self.batchShellRequested)
            panel.run_shell_requested.connect(self.runShellRequested)
            if result.state == "resolved":
                panel.title = result.path
                panel.lbl.setText(result.path)
                panel.set_dir(result.path)
            else:
                panel.title = str(area.get("label") or key)
                reason = "Path unavailable in the current remote environment" if result.state in {"unavailable", "invalid"} else "Provider context required"
                panel.lbl.setText(panel.title + " — " + reason)
            self.remote_panels[key] = panel
            self.accordion.add_section(key, panel.title, panel)

    def current_transfer_mode(self, _path: str = "") -> str:
        return str(self.mode_combo.currentData() or AUTO)

    def _refresh_local_transfer_target(self, target_dir: str) -> None:
        """Refresh the visible local folder after a successful remote transfer."""
        try:
            if os.path.abspath(target_dir) == os.path.abspath(self.local_panel.current_dir):
                self.local_panel.refresh()
        except (OSError, RuntimeError):
            pass

    def active_remote_panel(self) -> RemoteDirPanel:
        return self.remote_panels.get(self.accordion.active_key, self.panel_scratch)

    def _update_effective_label(self) -> None:
        requested = self.current_transfer_mode()
        paths = self.local_panel.selected_paths()
        sample_path = paths[0] if len(paths) == 1 else ""
        try:
            effective = resolve_transfer_mode(sample_path, requested)
        except ValueError:
            effective = BINARY
        label = {
            AUTO: t("ftp.mode_auto"),
            BINARY: t("ftp.mode_binary"),
            ASCII: t("ftp.mode_ascii"),
        }.get(effective, effective)
        self.effective_label.setText(t("ftp.effective_type").format(mode=label))

    def apply_settings(self) -> None:
        mode = get_ftp_transfer_type()
        index = self.mode_combo.findData(mode)
        self.mode_combo.setCurrentIndex(max(0, index))
        if hasattr(self, "effective_label"):
            self._update_effective_label()

    def clear_remote_directory_caches(self) -> None:
        RemoteDirPanel.clear_all_directory_caches()

    def _update_remote_titles(self) -> None:
        scratch_title = t("ftp.scratch")
        home_title = t("ftp.home")
        if self._scratch_path:
            scratch_title += f" — {self._scratch_path}"
        if self._home_path:
            home_title += f" — {self._home_path}"
        self.accordion.set_title("scratch", scratch_title)
        self.accordion.set_title("home", home_title)

    def _show_default_menu(self, key: str, panel: RemoteDirPanel, pos) -> None:
        if not self.session or not self.session.get("profile_name"):
            return
        menu = QMenu(self)  # type: ignore[arg-type]
        action = menu.addAction(
            t("ftp.set_scratch_default")
            if key == "scratch"
            else t("ftp.set_home_default")
        )
        chosen = _exec_temporary_menu(self, menu, panel.mapToGlobal(pos))  # type: ignore[arg-type]
        if chosen != action or not panel.current_dir:
            return
        self.set_current_as_default(key)

    def set_current_as_default(self, key: str) -> bool:
        panel = self.panel_scratch if key == "scratch" else self.panel_home
        if (
            key not in {"scratch", "home"}
            or not self.session
            or not self.session.get("profile_name")
            or not panel.current_dir
        ):
            return False
        scratch = panel.current_dir if key == "scratch" else self._scratch_path
        home = panel.current_dir if key == "home" else self._home_path
        self.defaultPathsRequested.emit(scratch, home)
        return True

    def set_session(self, session) -> None:
        self.session = session
        self.panel_scratch.set_session(session)
        self.panel_home.set_session(session)
        if not session or not session.get("connected"):
            self._apply_synchronized_state()
            return
        cfg = session.get("cfg")
        user = getattr(cfg, "username", "") or "user"
        system = normalize_system_settings(getattr(cfg, "system_settings", None))
        context = ProviderContext(user=user, project=getattr(cfg, "project", ""), account=getattr(cfg, "account", ""))
        self._add_provider_storage_panels(session, context)
        scratch_result = resolve_provider_path(system["scratch_dir"], context)
        home_result = resolve_provider_path(system["home_dir"], context)
        scratch = scratch_result.path if scratch_result.state == "resolved" else ""
        home = home_result.path if home_result.state == "resolved" else ""
        self._scratch_path = scratch
        self._home_path = home
        self.panel_scratch.title = scratch
        self.panel_scratch.lbl.setText(scratch)
        self.panel_home.title = home
        self.panel_home.lbl.setText(home)
        self._update_remote_titles()
        self.panel_scratch.set_dir(scratch)
        self.panel_home.set_dir(home)
        file_manager = normalize_file_manager_settings(
            getattr(cfg, "file_manager_settings", None)
        )
        local_start_dir = file_manager["local_start_dir"]
        if local_start_dir and os.path.isdir(local_start_dir):
            self.local_panel.set_dir(local_start_dir)
        self._apply_synchronized_state()


__all__ = [
    "FtpSessionMixin",
]
