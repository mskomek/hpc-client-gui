"""Case open/create and save/recovery actions for the Qt Case Studio page.

Reuses the host-owned :class:`CaseWorkspace` save path and the encrypted
remote recovery store; no parser, save, or SFTP logic is duplicated here.
Remote state always comes from the live application session
(``session_state["session"]["files"]``) and is never invented: when no
authenticated files service is present the page reports an explicit
unavailable state instead.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from hpc_gui.core.i18n import t

from .models import SaveReport
from .recovery_store import recovery_profile_id, recovery_store_for_backend
from .wx_case_manager_actions import valid_case_folder_name


def _case_root_for_selection(candidate: Path) -> Path:
    """Resolve a selected dictionary or case subfolder to its case root."""
    selected = candidate.resolve(strict=False)
    if selected.is_file():
        selected = selected.parent
    for parent in (selected, *selected.parents):
        if any((parent / name).is_dir() for name in ("system", "constant", "0")):
            return parent
    return selected


def _session_files(session_state) -> object | None:
    session = (session_state or {}).get("session") or {}
    if not isinstance(session, dict):
        return None
    return session.get("files")


class QtCaseManagerActions:
    def __init__(self, page):
        self.page = page
        self.hits = ()

    def bind(self):
        page = self.page
        page.case_search.textChanged.connect(self._search)
        page.case_search_results.itemClicked.connect(self._open_hit)
        page.new_button.clicked.connect(self._new_case)
        page.open_button.clicked.connect(self._open_case)
        page.snapshot_button.clicked.connect(self._open_snapshot)

    def refresh_search(self):
        self._set_hits(self.page.case_search.text())

    def _search(self, _text=""):
        self._set_hits(self.page.case_search.text())

    def _set_hits(self, query):
        workspace = self.page.workspace
        self.hits = () if workspace is None else workspace.search(query or "")
        self.page.case_search_results.clear()
        self.page.case_search_results.addItems(
            [f"{hit.relative_path}:{hit.line}:{hit.column}  {hit.text.strip()}" for hit in self.hits]
        )

    def _open_hit(self, _item=None):
        page = self.page
        index = page.case_search_results.currentRow()
        if not 0 <= index < len(self.hits):
            return
        hit = self.hits[index]
        page._open_document(hit.relative_path)
        editor = page._editors.get(hit.relative_path)
        if editor is not None:
            editor.setFocus()

    def _new_case(self, _checked=False):
        parent = QFileDialog.getExistingDirectory(
            self.page, t("openfoam.choose_parent"), "", QFileDialog.ShowDirsOnly
        )
        if parent:
            self.create_new_case_at(parent)

    def create_new_case_at(self, parent) -> bool:
        """Create a starter case skeleton, then open it. Returns True on success."""
        page = self.page
        name, accepted = QInputDialog.getText(
            page,
            t("openfoam.new_case"),
            t("openfoam.case_name_prompt"),
            text="OpenFOAMCase",
        )
        if not accepted:
            return False
        if not valid_case_folder_name(name.strip()):
            page._show_error(t("openfoam.invalid_case_name"))
            return False
        target = Path(str(parent)).expanduser() / name.strip()
        try:
            target.parent.resolve(strict=True)
            target.mkdir()
            for folder in ("system", "constant", "0"):
                (target / folder).mkdir()
            (target / "README-openfoam-starter.txt").write_text(
                f"OpenFOAM Case Studio starter case (OpenFOAM.com {page.target_release}).\n", encoding="utf-8"
            )
            page.open_target(str(target))
            return True
        except FileExistsError:
            page._show_error(t("openfoam.case_exists"))
        except OSError as exc:
            page._show_error(t("openfoam.case_create_failed").format(error=exc))
        return False

    def _open_case(self, _checked=False):
        page = self.page
        choices = [t("openfoam.local")]
        if _session_files(page.session_state) is not None:
            choices.append(t("openfoam.remote"))
        if len(choices) > 1:
            mode, accepted = QInputDialog.getItem(
                page,
                t("openfoam.open_case"),
                t("openfoam.choose_case_mode"),
                choices,
                0,
                False,
            )
            if not accepted:
                return
            remote = mode == t("openfoam.remote")
        else:
            remote = False
        if remote:
            path, accepted = QInputDialog.getText(
                page,
                t("openfoam.open_case"),
                t("openfoam.remote_case_path"),
                text="/",
            )
            if accepted and path.strip():
                page.open_target(path.strip(), remote=True)
            return
        selected = QFileDialog.getExistingDirectory(
            page, t("openfoam.open_case"), "", QFileDialog.ShowDirsOnly
        )
        if selected:
            page.open_target(selected)

    def _open_snapshot(self, _checked=False):
        page = self.page
        choices = [t("openfoam.local")]
        if _session_files(page.session_state) is not None:
            choices.append(t("openfoam.remote"))
        if len(choices) > 1:
            mode, accepted = QInputDialog.getItem(
                page,
                t("openfoam.open_snapshot"),
                t("openfoam.snapshot_mode"),
                choices,
                0,
                False,
            )
            if not accepted:
                return
            remote = mode == t("openfoam.remote")
        else:
            remote = False
        if remote:
            path, accepted = QInputDialog.getText(
                page,
                t("openfoam.open_snapshot"),
                t("openfoam.remote_snapshot_path"),
                text="/",
            )
            if accepted and path.strip():
                page.open_target(path.strip(), remote=True, read_only=True)
            return
        selected = QFileDialog.getExistingDirectory(
            page, t("openfoam.open_snapshot"), "", QFileDialog.ShowDirsOnly
        )
        if selected:
            page.open_target(selected, read_only=True)


class QtCaseSaveActions:
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
        self.page.recover_button.setEnabled(
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

    def save(self, _checked=False):
        page = self.page
        workspace = page.workspace
        if workspace is None:
            page.status.setText(t("openfoam.no_case"))
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
            page.recover_button.setEnabled(True)
        if report.success:
            if report.errors or report.recovery_paths:
                paths = ", ".join(report.recovery_paths) or "; ".join(report.errors)
                detail = t("openfoam.save_recovery").format(paths=paths)
                if report.recovery_paths and not recovery_persisted:
                    detail += " " + t("openfoam.recovery_index_unavailable")
                page._show_error(detail)
            else:
                page.status.setText(t("openfoam.save_success").format(count=len(report.saved)))
            return
        details = "; ".join((*report.conflicts, *report.errors, *report.recovery_paths))
        if report.recovery_paths and not recovery_persisted:
            details += "; " + t("openfoam.recovery_index_unavailable")
        page._show_error(
            t("openfoam.save_failed").format(details=details)
            if details
            else t("openfoam.save_failed_simple")
        )

    def recover(self, _checked=False):
        page = self.page
        workspace = page.workspace
        if (
            workspace is None
            or not workspace.remote
            or workspace.root != self.pending_root
            or not self.pending_paths
        ):
            page.recover_button.setEnabled(False)
            return
        files = _session_files(page.session_state)
        if files is None:
            page._show_error(t("openfoam.recovery_remote_unavailable"))
            return
        root, paths = workspace.root, self.pending_paths
        current_profile = recovery_profile_id(files)
        if self.pending_profile_id and current_profile != self.pending_profile_id:
            page._show_error(t("openfoam.recovery_wrong_profile"))
            return
        workspace.files = files
        page.recover_button.setEnabled(False)
        page.status.setText(t("openfoam.recovery_running"))
        try:
            report = workspace.recover_save(paths)
        except Exception as exc:
            report = SaveReport(False, False, (), errors=(str(exc),), recovery_paths=paths)
        self._recovery_finished(root, files, paths, report)

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
                page.recover_button.setEnabled(False)
                page.status.setText(t("openfoam.save_recovered").format(count=len(report.saved)))
            return
        self._remember_recovery(root, files, report.recovery_paths or original_paths)
        if current_workspace:
            page.recover_button.setEnabled(True)
            details = "; ".join((*report.conflicts, *report.errors, *self.pending_paths))
            page._show_error(
                t("openfoam.recovery_failed").format(details=details)
                if details
                else t("openfoam.recovery_failed_simple")
            )

    def confirm_discard(self, title: str, message: str) -> bool:
        answer = QMessageBox.question(
            self.page, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return answer == QMessageBox.Yes
