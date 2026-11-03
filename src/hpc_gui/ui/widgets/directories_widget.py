from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPoint, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QMessageBox,
    QDialog, QPushButton, QFileDialog, QInputDialog
)

from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.core.history import append_event
from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel
from hpc_gui.ui.async_call import AsyncCall
from hpc_gui.ui.widgets.directories_submission import (
    DirectoriesSubmissionMixin,
    _BatchSubmitWorker,
    _ShellRunWorker,
    _SubmitWorker,
)


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value




class DirectoriesWidget(DirectoriesSubmissionMixin, QWidget):
    open_in_editor = Signal(str, str)  # path, content
    open_in_editor_new_window = Signal(str, str)  # path, content
    script_submitted = Signal(str, str)  # job_id, script_path

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.session = None
        self._submit_workers: set[_SubmitWorker] = set()
        self._batch_submit_workers: set[_BatchSubmitWorker] = set()
        self._shell_run_workers: set[_ShellRunWorker] = set()
        self._read_workers: set[AsyncCall] = set()

        self.panel_scratch = RemoteDirPanel(title="/arf/scratch")
        self.panel_home = RemoteDirPanel(title="/arf/home")

        self.panel_scratch.open_file.connect(self.on_open_file)
        self.panel_home.open_file.connect(self.on_open_file)
        self.panel_scratch.submit_requested.connect(self.submit_script)
        self.panel_home.submit_requested.connect(self.submit_script)
        self.panel_scratch.batch_submit_requested.connect(self.submit_scripts_batch)
        self.panel_home.batch_submit_requested.connect(self.submit_scripts_batch)
        self.panel_scratch.run_shell_requested.connect(self.run_shell_script)
        self.panel_home.run_shell_requested.connect(self.run_shell_script)

        self.splitter = QSplitter()
        self.splitter.addWidget(self.panel_scratch)
        self.splitter.addWidget(self.panel_home)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.btn_new_slurm = QPushButton(
            t("dirs.new_slurm_edit")
        )
        self.btn_new_slurm.clicked.connect(self.create_slurm_from_template)

        top = QHBoxLayout()
        top.addWidget(self.btn_new_slurm)
        top.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.splitter)

    @staticmethod
    def _local_paths_from_drop(event) -> list[str]:
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            return []
        return [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]

    def _panel_at_widget_pos(self, pos: QPoint) -> RemoteDirPanel:
        for panel in (self.panel_scratch, self.panel_home):
            top_left = panel.mapTo(self, QPoint(0, 0))
            rect = panel.rect().translated(top_left)
            if rect.contains(pos):
                return panel
        return self.panel_scratch

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._local_paths_from_drop(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._local_paths_from_drop(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        paths = self._local_paths_from_drop(event)
        if not paths:
            super().dropEvent(event)
            return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        panel = self._panel_at_widget_pos(pos)
        target_dir = panel.current_dir
        event.acceptProposedAction()
        QTimer.singleShot(
            0,
            lambda dropped_paths=list(paths), target_panel=panel, target=target_dir: (
                target_panel._apply_local_upload(dropped_paths, target)
            ),
        )

    def set_session(self, session):
        self.session = session
        self.panel_scratch.set_session(session)
        self.panel_home.set_session(session)

        if not session or not session.get("connected"):
            return
        user = session["cfg"].username or "user"
        system = normalize_system_settings(
            getattr(session["cfg"], "system_settings", None)
        )
        scratch_dir = format_remote_path(system["scratch_dir"], user)
        home_dir = format_remote_path(system["home_dir"], user)
        self.panel_scratch.title = scratch_dir
        self.panel_scratch.lbl.setText(scratch_dir)
        self.panel_home.title = home_dir
        self.panel_home.lbl.setText(home_dir)
        self.panel_scratch.set_dir(scratch_dir)
        self.panel_home.set_dir(home_dir)

    def retranslate_ui(self):
        self.btn_new_slurm.setText(
            t("dirs.new_slurm_edit")
        )
        self.panel_scratch.retranslate_ui()
        self.panel_home.retranslate_ui()














    def create_slurm_from_template(self):
        if not self.session or not self.session.get("connected"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        template_key = self._pick_template_key()
        if not template_key:
            return
        try:
            template_path = self._resolve_template_path(template_key)
            template_text = template_path.read_text(encoding="utf-8")
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=f"template.slurm okunamadi: {e}", exc=e, area="FILES")
            return

        default_dir = self.panel_scratch.current_dir or ""
        if not default_dir:
            cfg = self.session.get("cfg") if self.session else None
            user = getattr(cfg, "username", "") or "user"
            system = normalize_system_settings(
                getattr(cfg, "system_settings", None)
            )
            default_dir = format_remote_path(system["scratch_dir"], user)

        name, ok = QInputDialog.getText(
            self,
            t("dirs.new_slurm_name_title"),
            t("dirs.new_slurm_name_label"),
            text="new_job.slurm",
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if not name.lower().endswith((".slurm", ".sbatch")):
            name += ".slurm"
        target_path = default_dir.rstrip("/") + "/" + name

        files = self.session.get("files") if self.session else None
        if files is not None:
            exists = False
            try:
                exists = bool(files.exists(target_path))
            except Exception:
                exists = False
            if exists:
                ans = QMessageBox.question(
                    self,
                    t("dirs.conflict_title"),
                    (t("dirs.new_slurm_exists")),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return

        append_event({"type": "new_slurm_from_template", "path": target_path})
        self.open_in_editor.emit(target_path, template_text)

    def _pick_template_key(self) -> str:
        options = [
            t("dirs.template_core"),
            t("dirs.template_cpu"),
            t("dirs.template_gpu"),
            t("dirs.template_mpi"),
        ]
        choice, ok = QInputDialog.getItem(
            self,
            t("dirs.template_select_title"),
            t("dirs.template_select_label"),
            options,
            0,
            False,
        )
        if not ok:
            return ""
        mapping = {
            options[0]: "core",
            options[1]: "cpu",
            options[2]: "gpu",
            options[3]: "mpi",
        }
        return mapping.get(choice, "core")

    @staticmethod
    def _resolve_template_path(template_key: str) -> Path:
        root = Path(__file__).resolve().parents[4]
        from hpc_gui.core.paths import app_data_dir

        user_tpl = app_data_dir() / "templates"
        env_tpl = Path(os.environ.get("TRUBA_TEMPLATE_DIR", "")).expanduser() if os.environ.get("TRUBA_TEMPLATE_DIR") else None
        filename_map = {
            "core": "template.slurm",
            "cpu": "template_cpu.slurm",
            "gpu": "template_gpu.slurm",
            "mpi": "template_mpi.slurm",
        }
        mapping = {
            "core": root / "template.slurm",
            "cpu": root / "templates" / "template_cpu.slurm",
            "gpu": root / "templates" / "template_gpu.slurm",
            "mpi": root / "templates" / "template_mpi.slurm",
        }
        fname = filename_map.get(template_key, "template.slurm")
        search_paths = []
        if env_tpl:
            search_paths.append(env_tpl / fname)
        search_paths.append(user_tpl / fname)
        search_paths.append(mapping.get(template_key, mapping["core"]))
        for p in search_paths:
            if p.exists():
                return p
        # Safe fallback to core template if variant file missing.
        return mapping["core"]

    def shutdown(self) -> None:
        """Best-effort shutdown for file operations (cancel in-flight batches)."""
        for p in (getattr(self, "panel_scratch", None), getattr(self, "panel_home", None)):
            try:
                if p is not None and hasattr(p, "shutdown"):
                    p.shutdown()
            except Exception:
                pass

    def on_open_file(self, path: str):
        # If directory, we don't support navigation yet (next step). For now ignore.
        if path.endswith("/"):
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(t("dirs.file_actions"))

        btn_download = QPushButton(t("dirs.download"))
        btn_edit = QPushButton(t("dirs.edit"))
        btn_edit_new_window = QPushButton(
            t("dirs.edit_new_window"))
        btn_close = QPushButton(t("common.cancel"))

        row = QHBoxLayout(dlg)
        row.addWidget(QLabel(path))
        row.addStretch(1)
        row.addWidget(btn_download)
        row.addWidget(btn_edit)
        row.addWidget(btn_edit_new_window)
        row.addWidget(btn_close)

        def do_download():
            if not self.session or not self.session.get("files"):
                QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
                return
            try:
                content = self.session["files"].read_text(path)
            except Exception as e:
                show_exception(self, title=t("common.error"), user_message=t("dirs.unreadable").format(err=e), exc=e, area="FILES")
                return
            save_path, _ = QFileDialog.getSaveFileName(self, t("dirs.save_as"))
            if not save_path:
                return
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                show_exception(self, title=t("common.error"), user_message=f"Kaydedilemedi: {e}", exc=e, area="FILES")
                return
            append_event({"type": "download", "remote": path, "local": save_path})
            dlg.accept()

        def read_for_editor(new_window: bool) -> None:
            if not self.session or not self.session.get("files"):
                QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
                return
            files = self.session["files"]
            reader = getattr(files, "read_text_for_edit", files.read_text)
            worker = AsyncCall(path, lambda: reader(path))
            self._read_workers.add(worker)

            def finished(_path, content):
                self._read_workers.discard(worker)
                append_event({"type": "open_editor_new_window" if new_window else "open_editor", "path": path})
                (self.open_in_editor_new_window if new_window else self.open_in_editor).emit(path, content)
                dlg.accept()

            def failed(_path, error):
                self._read_workers.discard(worker)
                show_exception(self, title=t("common.error"), user_message=f"Okunamadı: {error}", exc=error, area="FILES")

            worker.signals.finished.connect(finished)
            worker.signals.failed.connect(failed)
            QThreadPool.globalInstance().start(worker)

        def do_edit():
            read_for_editor(False)

        def do_edit_new_window():
            read_for_editor(True)
        btn_download.clicked.connect(do_download)
        btn_edit.clicked.connect(do_edit)
        btn_edit_new_window.clicked.connect(do_edit_new_window)
        btn_close.clicked.connect(dlg.reject)

        dlg.exec()
