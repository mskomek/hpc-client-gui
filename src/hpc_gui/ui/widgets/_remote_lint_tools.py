"""Remote lint-tools leaf for the file-manager remote panel.

Owns ``RemoteLintToolsMixin``: the ``_RemoteLintWorker`` folder-scan worker
(off-GUI-thread ``QRunnable``), remote suffix helpers, send-to-plugin menu
building, and the ANSYS lint single/batch/folder entry points. Plugin and
dialog imports stay lazy function-level imports exactly as before, so existing
`hpc_gui.plugins.*` / `hpc_gui.ui.dialogs.*` test patches keep intercepting the
same module namespaces. Error surfacing stays owned by the facade and is
reached via ``self``.

Imports Qt, threading pool primitives, and lower-level core/services only —
never the local panel, FTP widget, controllers, or another branch's private
implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QMessageBox

from hpc_gui.core.i18n import t

logger = logging.getLogger(__name__)


def _remote_file_name(remote_path: str) -> str:
    return remote_path.rstrip("/").rsplit("/", 1)[-1]


def _remote_suffix(remote_path: str) -> str:
    name = _remote_file_name(remote_path)
    dot = name.rfind(".")
    return name[dot:].lower() if dot >= 0 else ""


class _RemoteLintSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class _RemoteLintWorker(QRunnable):
    """Read and lint a remote folder without blocking the Qt event loop."""

    # ponytail: cap remote scans at 200 files; add paged/cancellable scanning if needed.
    MAX_FILES = 200

    def __init__(self, files, remote_dir: str) -> None:
        super().__init__()
        self.files = files
        self.remote_dir = remote_dir.rstrip("/") or "/"
        self.signals = _RemoteLintSignals()

    @Slot()
    def run(self) -> None:
        try:
            from hpc_gui.plugins.linter_tools import lint_text_with_tool, supported_suffixes

            supported = supported_suffixes()
            paths: list[str] = []
            pending = [self.remote_dir]
            while pending and len(paths) < self.MAX_FILES:
                current = pending.pop()
                for entry in self.files.listdir_entries(current):
                    path = entry.path.rstrip("/")
                    if entry.is_dir:
                        pending.append(path)
                    elif _remote_suffix(path) in supported:
                        paths.append(path)
                        if len(paths) >= self.MAX_FILES:
                            break
            results = [
                lint_text_with_tool(self.files.read_text(path), file_name=path)
                for path in paths
            ]
            self.signals.finished.emit((paths, results))
        except Exception as exc:
            self.signals.failed.emit(exc)


class RemoteLintToolsMixin:
    """Linter-tool entry-point ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    _remote_lint_worker: Optional[_RemoteLintWorker]

    @staticmethod
    def _ansys_lint_supported(remote_path: str) -> bool:
        from hpc_gui.plugins.linter_tools import supported_suffixes

        name = remote_path.rstrip("/").rsplit("/", 1)[-1]
        dot = name.rfind(".")
        if dot < 0:
            return False
        return name[dot:].lower() in supported_suffixes()

    @staticmethod
    def _remote_file_name(remote_path: str) -> str:
        return _remote_file_name(remote_path)

    @staticmethod
    def _remote_suffix(remote_path: str) -> str:
        return _remote_suffix(remote_path)

    def _build_send_to_plugin_menu(self, menu, remote_path: str | None):
        """Attach a "send to plugin" submenu when a tool supports the file."""
        if not remote_path:
            return None
        from hpc_gui.plugins.linter_tools import tools_supporting_suffix

        try:
            tools = tools_supporting_suffix(self._remote_suffix(remote_path))
        except Exception:  # defensive: menu building never breaks the panel
            logger.warning("Tool lookup failed for %s", remote_path, exc_info=True)
            return None
        if not tools:
            return None
        send_menu = menu.addMenu(t("files.send_to_plugin"))
        for tool in tools:
            action = send_menu.addAction(tool.title)
            action.triggered.connect(
                lambda _=False, tl=tool, p=remote_path: self.open_in_tool(tl, p)
            )
        return send_menu

    def open_in_tool(self, tool, remote_path: str) -> None:
        """Open a linter-tool page pre-loaded with one remote file.

        Tool pages re-read paths from disk, so the current content is
        materialized into a suffixed temporary file for the lifetime of
        the modal page and removed afterwards.
        """
        from hpc_gui.plugins.linter_tools import (
            remove_temp_copy,
            temp_copy_for_tool,
        )
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return
        temp_path = None
        try:
            text = files.read_text(remote_path)
            temp_path = temp_copy_for_tool(text, self._remote_file_name(remote_path))
        except Exception as exc:  # network or disk failure stays contained
            logger.warning("Could not fetch %s for tool", remote_path, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"  # type: ignore[arg-type]
            )
            return
        try:
            host_tool_page(
                self,  # type: ignore[arg-type]
                tool,
                initial_paths=[str(temp_path)],
                title=f"{tool.title} — {self._remote_file_name(remote_path)}",
            )
        finally:
            remove_temp_copy(temp_path)

    def run_ansys_lint(self, remote_path: str) -> None:
        from hpc_gui.plugins.linter_tools import (
            ToolLoadError,
            lint_text_with_tool,
        )
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import first_linter_tool

            try:
                self.open_in_tool(first_linter_tool(), remote_path)
            except Exception as exc:  # already messaged by the fetch/host path
                logger.warning("Fix redirect failed for %s", remote_path, exc_info=exc)

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(
                self, t("common.error"), t("common.no_connection")  # type: ignore[arg-type]
            )
            return
        try:
            text = files.read_text(remote_path)
            run = lint_text_with_tool(text, file_name=remote_path)
        except ToolLoadError as exc:
            QMessageBox.warning(self, t("ansyslint.title"), str(exc))  # type: ignore[arg-type]
            return
        except Exception as exc:  # defensive: network/engine failures stay contained
            logger.warning(
                "ANSYS lint failed for %s", remote_path, exc_info=exc
            )
            QMessageBox.warning(
                self,
                t("ansyslint.title"),
                f"{type(exc).__name__}: {exc}",  # type: ignore[arg-type]
            )
            return
        show_ansys_lint_results(
            self,  # type: ignore[arg-type]
            f"{t('ansyslint.title')} — "
            f"{self._remote_file_name(remote_path)}",
            run,
            open_in_tool=open_in_tool,
        )

    def open_in_tool_batch(self, tool, remote_paths: list[str]) -> None:
        """Open a linter-tool page pre-loaded with multiple remote files."""
        from hpc_gui.plugins.linter_tools import (
            remove_temp_copy,
            temp_copy_for_tool,
        )
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return
        temp_paths: list[Path] = []
        try:
            for remote_path in remote_paths:
                text = files.read_text(remote_path)
                temp_paths.append(
                    temp_copy_for_tool(text, self._remote_file_name(remote_path))
                )
        except Exception as exc:  # network or disk failure stays contained
            for p in temp_paths:
                remove_temp_copy(p)
            logger.warning("Could not fetch %s for tool", remote_paths, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"  # type: ignore[arg-type]
            )
            return
        try:
            names = ", ".join(self._remote_file_name(p) for p in remote_paths[:3])
            if len(remote_paths) > 3:
                names += f" +{len(remote_paths) - 3}"
            host_tool_page(
                self,  # type: ignore[arg-type]
                tool,
                initial_paths=[str(p) for p in temp_paths],
                title=f"{tool.title} — {names}",
            )
        finally:
            for p in temp_paths:
                remove_temp_copy(p)

    def run_ansys_lint_batch(self, remote_paths: list[str]) -> None:
        from hpc_gui.plugins.linter_tools import ToolLoadError, lint_text_with_tool
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )
        import types

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

            try:
                suffixes = [self._remote_suffix(p) for p in remote_paths]
                tools = tools_supporting_all_suffixes(suffixes)
                if not tools:
                    return
                self.open_in_tool_batch(tools[0], remote_paths)
            except Exception as exc:
                logger.warning("Fix redirect failed for %s", remote_paths, exc_info=exc)

        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return
        file_results = []
        try:
            for remote_path in remote_paths:
                text = files.read_text(remote_path)
                file_results.append(lint_text_with_tool(text, file_name=remote_path))
        except ToolLoadError as exc:
            QMessageBox.warning(self, t("ansyslint.title"), str(exc))  # type: ignore[arg-type]
            return
        except Exception as exc:  # defensive: network/engine failures stay contained
            logger.warning("ANSYS lint failed for %s", remote_paths, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"  # type: ignore[arg-type]
            )
            return
        # Build a LintRunResult-like object for the dialog.
        totals = {"error": 0, "warning": 0, "info": 0}
        for fr in file_results:
            for key in totals:
                totals[key] += fr.summary.get(key, 0) if hasattr(fr, "summary") else 0
        run = types.SimpleNamespace(files=file_results, summary=totals)
        names = ", ".join(self._remote_file_name(p) for p in remote_paths[:3])
        if len(remote_paths) > 3:
            names += f" +{len(remote_paths) - 3}"
        show_ansys_lint_results(
            self,  # type: ignore[arg-type]
            f"{t('ansyslint.title')} — {names}",
            run,
            open_in_tool=open_in_tool,
        )

    def run_ansys_lint_folder(self, remote_path: str) -> None:
        files = (self.session or {}).get("files")
        if not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))  # type: ignore[arg-type]
            return
        if self._remote_lint_worker is not None:
            return
        worker = _RemoteLintWorker(files, remote_path)
        self._remote_lint_worker = worker
        worker.signals.finished.connect(self._on_remote_lint_finished)
        worker.signals.failed.connect(self._on_remote_lint_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_remote_lint_failed(self, error: object) -> None:
        self._remote_lint_worker = None
        logger.warning("Remote folder lint failed: %r", error)
        QMessageBox.warning(self, t("ansyslint.title"), f"{type(error).__name__}: {error}")  # type: ignore[arg-type]

    def _on_remote_lint_finished(self, payload: object) -> None:
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        self._remote_lint_worker = None
        remote_paths, file_results = payload
        if not remote_paths:
            QMessageBox.information(
                self, t("ansyslint.title"), t("files.no_supported_remote_lint_files")  # type: ignore[arg-type]
            )
            return
        import types

        totals = {"error": 0, "warning": 0, "info": 0}
        for result in file_results:
            for key in totals:
                totals[key] += result.summary.get(key, 0)
        run = types.SimpleNamespace(files=file_results, summary=totals)

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

            tools = tools_supporting_all_suffixes(
                [self._remote_suffix(path) for path in remote_paths]
            )
            if tools:
                self.open_in_tool_batch(tools[0], remote_paths)

        show_ansys_lint_results(
            self,  # type: ignore[arg-type]
            f"{t('ansyslint.title')} — {self._remote_file_name(remote_paths[0])} +{len(remote_paths) - 1}",
            run,
            open_in_tool=open_in_tool,
        )


__all__ = [
    "RemoteLintToolsMixin",
    "_RemoteLintSignals",
    "_RemoteLintWorker",
]
