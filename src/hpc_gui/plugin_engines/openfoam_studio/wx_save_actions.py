"""Save and post-reconnect recovery actions for the Case Studio page."""
from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import t

from .models import SaveReport
from .recovery_store import recovery_profile_id, recovery_store_for_backend


class WxCaseSaveActions:
    def __init__(self, page):
        self.page = page
        self.pending_root: str | None = None
        self.pending_paths: tuple[str, ...] = ()
        self.pending_profile_id = ""
        self.pending_files_identity: int | None = None

    def workspace_changed(self, workspace):
        if not workspace.remote:
            self.pending_root = None
            self.pending_paths = ()
            self.pending_profile_id = ""
            self.pending_files_identity = None
        else:
            profile_id = recovery_profile_id(workspace.files)
            same_identity = (
                self.pending_profile_id == profile_id
                if self.pending_profile_id or profile_id
                else self.pending_files_identity == id(workspace.files)
            )
            if self.pending_root != workspace.root or not same_identity:
                self.pending_root = workspace.root
                self.pending_paths = ()
                self.pending_profile_id = profile_id
                self.pending_files_identity = id(workspace.files)
                store = recovery_store_for_backend(workspace.files)
                if store is not None:
                    try:
                        self.pending_paths = store.get(workspace.root)
                    except Exception:
                        self.pending_paths = ()
        self.page.recover_button.Enable(
            bool(workspace.remote and workspace.root == self.pending_root and self.pending_paths)
        )

    def _remember_recovery(self, root, files, paths) -> bool:
        self.pending_root = root
        self.pending_paths = tuple(paths)
        self.pending_profile_id = recovery_profile_id(files)
        self.pending_files_identity = id(files)
        if not self.pending_paths:
            return True
        store = recovery_store_for_backend(files)
        if store is None:
            return False
        try:
            store.save(root, self.pending_paths)
            return True
        except Exception:
            return False

    def _clear_recovery(self, files, root):
        store = recovery_store_for_backend(files)
        if store is not None:
            try:
                store.remove(root)
            except Exception:
                pass
        self.pending_root = None
        self.pending_paths = ()
        self.pending_profile_id = ""
        self.pending_files_identity = None

    def save(self, _event=None):
        page = self.page
        workspace = page.workspace
        if workspace is None:
            page.status.SetLabel(t("openfoam.no_case"))
            return
        try:
            report = workspace.save()
        except Exception as exc:
            report = SaveReport(False, False, (), errors=(str(exc),))
        page._refresh_diff()
        page._refresh_preview()
        page._refresh_problems()
        recovery_persisted = True
        if workspace.remote and report.recovery_paths:
            recovery_persisted = self._remember_recovery(
                workspace.root, workspace.files, report.recovery_paths
            )
            page.recover_button.Enable(True)
        if report.success:
            if report.errors or report.recovery_paths:
                paths = ", ".join(report.recovery_paths) or "; ".join(report.errors)
                detail = t("openfoam.save_recovery").format(paths=paths)
                if report.recovery_paths and not recovery_persisted:
                    detail += " " + t("openfoam.recovery_not_persisted")
                page._show_error(detail)
            else:
                page.status.SetLabel(t("openfoam.save_success").format(count=len(report.saved)))
            return
        details = "; ".join((*report.conflicts, *report.errors, *report.recovery_paths))
        if report.recovery_paths and not recovery_persisted:
            details += "; " + t("openfoam.recovery_not_persisted")
        page._show_error(t("openfoam.save_failed").format(details=details))

    def recover(self, _event=None):
        page = self.page
        workspace = page.workspace
        if (
            workspace is None or not workspace.remote
            or workspace.root != self.pending_root or not self.pending_paths
        ):
            page.recover_button.Disable()
            return
        session = page.session_state.get("session") or {}
        files = session.get("files") if isinstance(session, dict) else None
        if files is None:
            page._show_error(t("openfoam.remote_unavailable"))
            return
        root, paths = workspace.root, self.pending_paths
        current_profile = recovery_profile_id(files)
        if self.pending_profile_id and current_profile != self.pending_profile_id:
            page._show_error(t("openfoam.recovery_wrong_profile"))
            return
        workspace.files = files
        page.recover_button.Disable()
        page.status.SetLabel(t("openfoam.recovery_running"))

        def worker():
            try:
                report = workspace.recover_save(paths)
            except Exception as exc:
                report = SaveReport(False, False, (), errors=(str(exc),), recovery_paths=paths)
            page.wx.CallAfter(self._recovery_finished, root, files, paths, report)

        Thread(target=worker, daemon=True).start()

    def _recovery_finished(self, root, files, original_paths, report):
        page = self.page
        workspace = page.workspace
        current_workspace = bool(
            workspace is not None and workspace.remote and workspace.root == root
        )
        if current_workspace:
            workspace.files = files
        if report.success and not report.errors and not report.conflicts:
            self._clear_recovery(files, root)
            if current_workspace:
                page.recover_button.Disable()
                page.status.SetLabel(t("openfoam.save_recovered").format(count=len(report.saved)))
            return
        self._remember_recovery(root, files, report.recovery_paths or original_paths)
        if current_workspace:
            page.recover_button.Enable(True)
            details = "; ".join((*report.conflicts, *report.errors, *self.pending_paths))
            page._show_error(t("openfoam.save_failed").format(details=details))
