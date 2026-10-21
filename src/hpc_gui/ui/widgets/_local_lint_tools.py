"""Local lint/tool-integration leaf for the file-manager local panel.

Owns the ``LocalLintToolsMixin``: suffix discovery, folder tool lookup,
send-to-plugin menus, single/batch ANSYS lint runs, and rulepack fallback.
Plugin and dialog imports stay lazy (as before) to keep this leaf free of
hard UI-controller dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from hpc_gui.core.i18n import t

logger = logging.getLogger(__name__)


class LocalLintToolsMixin:
    """Linter/tool integration helpers (mixed into ``LocalDirPanel``)."""

    def _folder_contains_supported_file(self, folder: str) -> bool:
        try:
            supported = self._local_lint_suffixes()  # type: ignore[attr-defined]
            if not supported:
                return False
            count = 0
            for p in Path(folder).rglob("*"):
                if p.is_file() and p.suffix.lower() in supported:
                    return True
                count += 1
                if count > 200:
                    break
        except Exception:
            return False
        return False

    @staticmethod
    def _local_lint_suffixes() -> set[str]:
        """Return suffixes supported by installed declarative or v2 linters."""
        suffixes: set[str] = set()
        try:
            from hpc_gui.plugins.linter_tools import (
                list_linter_tools,
                supported_suffixes,
                tool_supported_suffixes,
            )

            suffixes.update(supported_suffixes())
            for tool in list_linter_tools():
                suffixes.update(tool_supported_suffixes(tool))
        except Exception:
            pass
        try:
            from hpc_gui.lint.rulepack import load_lint_packs

            for pack in load_lint_packs():
                for pattern in pack.file_patterns:
                    suffix = Path(pattern).suffix.lower()
                    if suffix and not any(char in suffix for char in "*?["):
                        suffixes.add(suffix)
        except Exception:
            pass
        return suffixes

    @classmethod
    def _local_lint_supports_suffixes(cls, suffixes: list[str]) -> bool:
        supported = cls._local_lint_suffixes()
        return bool(suffixes) and all(suffix.lower() in supported for suffix in suffixes)

    def _tools_for_folder(self, folder: str) -> list:
        from hpc_gui.plugins.linter_tools import list_linter_tools, tool_supported_suffixes

        try:
            supported = set()
            for p in Path(folder).rglob("*"):
                if p.is_file():
                    sfx = p.suffix.lower()
                    if sfx:
                        supported.add(sfx)
                    if len(supported) > 20:
                        break
            if not supported:
                return []
            tools = []
            for tool in list_linter_tools():
                declared = tool_supported_suffixes(tool)
                if declared & supported:
                    tools.append(tool)
            return tools
        except Exception:
            logger.warning("Tool lookup failed for folder %s", folder, exc_info=True)
            return []

    @staticmethod
    def _ansys_lint_supported(suffix: str) -> bool:
        from hpc_gui.plugins.linter_tools import supported_suffixes

        return suffix in supported_suffixes()

    def _edit_selected(self, new_window: bool) -> None:
        selected = self._selected_items()  # type: ignore[attr-defined]
        if len(selected) != 1:
            return
        path = str(selected[0].data(0, Qt.ItemDataRole.UserRole))
        if not path or Path(path).is_dir():
            return
        self.editRequested.emit(path, new_window)  # type: ignore[attr-defined]

    def _build_send_to_plugin_menu(self, plugin_menu, path_str: str | None):
        """Attach a "send to plugin" submenu when a tool supports the file."""
        if not path_str:
            return None
        from hpc_gui.plugins.linter_tools import tools_supporting_suffix

        try:
            tools = tools_supporting_suffix(Path(path_str).suffix.lower())
        except Exception:  # defensive: menu building never breaks the panel
            logger.warning("Tool lookup failed for %s", path_str, exc_info=True)
            return None
        if not tools:
            return None
        if plugin_menu is None:
            return None
        send_menu = plugin_menu.addMenu(t("files.send_to_plugin"))
        for tool in tools:
            action = send_menu.addAction(tool.title)
            action.triggered.connect(
                lambda _=False, tl=tool, p=path_str: self.open_in_tool(tl, p)  # type: ignore[attr-defined]
            )
        return send_menu

    def open_in_tool(self, tool, path_str: str) -> None:
        """Open a linter-tool page pre-loaded with one local file."""
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        host_tool_page(
            self,  # type: ignore[arg-type]
            tool,
            initial_paths=[path_str],
            title=f"{tool.title} — {Path(path_str).name}",
        )

    def open_in_tool_batch(self, tool, paths: list[str]) -> None:
        """Open a linter-tool page pre-loaded with multiple local files."""
        from hpc_gui.ui.dialogs.linter_tool_host import host_tool_page

        names = ", ".join(Path(str(p)).name for p in paths[:3])
        if len(paths) > 3:
            names += f" +{len(paths) - 3}"
        host_tool_page(
            self,  # type: ignore[arg-type]
            tool,
            initial_paths=[str(p) for p in paths],
            title=f"{tool.title} — {names}",
        )

    def run_ansys_lint(self, path: Path) -> None:
        from hpc_gui.plugins.linter_tools import ToolLoadError, lint_paths_with_tool
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import first_linter_tool

            try:
                self.open_in_tool(first_linter_tool(), str(path))  # type: ignore[attr-defined]
            except Exception as exc:  # already messaged by the host
                logger.warning("Fix redirect failed for %s", path, exc_info=exc)

        try:
            run = lint_paths_with_tool([path])
        except ToolLoadError as exc:
            diagnostics = self._run_local_rulepack_lint(path)  # type: ignore[attr-defined]
            if diagnostics is None:
                QMessageBox.warning(self, t("ansyslint.title"), str(exc))  # type: ignore[arg-type]
            else:
                self._show_local_lint_results(path, diagnostics)  # type: ignore[attr-defined]
            return
        except Exception as exc:  # defensive: engine failures stay contained
            logger.warning("ANSYS lint failed for %s", path, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"  # type: ignore[arg-type]
            )
            return
        show_ansys_lint_results(
            self, f"{t('ansyslint.title')} — {path.name}", run, open_in_tool=open_in_tool  # type: ignore[arg-type]
        )

    @staticmethod
    def _run_local_rulepack_lint(path: Path) -> list | None:
        from hpc_gui.lint.engine import lint_text
        from hpc_gui.lint.rulepack import load_lint_packs

        try:
            text = path.read_text(encoding="utf-8")
            packs = [pack for pack in load_lint_packs() if pack.matches(str(path))]
            if not packs:
                return None
            diagnostics = []
            for pack in packs:
                diagnostics.extend(lint_text(text, file_name=str(path), rule_pack=pack))
            return diagnostics
        except (OSError, UnicodeError):
            return None

    def _show_local_lint_results(self, path: Path, diagnostics: list) -> None:
        if not diagnostics:
            QMessageBox.information(
                self, t("ansyslint.title"), f"{path.name}: {t('editor.lint_ok')}"  # type: ignore[arg-type]
            )
            return
        lines = []
        for diagnostic in diagnostics:
            location = f"{diagnostic.line}:{diagnostic.column or 1}" if diagnostic.line else "-"
            severity = getattr(diagnostic.severity, "value", diagnostic.severity)
            lines.append(f"[{location}] {severity}: {diagnostic.message} ({diagnostic.rule_id})")
        QMessageBox.warning(self, t("ansyslint.title"), "\n".join(lines))  # type: ignore[arg-type]

    def run_ansys_lint_batch(self, paths: list[Path]) -> None:
        from hpc_gui.plugins.linter_tools import ToolLoadError, lint_paths_with_tool
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import (
            show_ansys_lint_results,
        )

        if not paths:
            return

        def open_in_tool() -> None:
            from hpc_gui.plugins.linter_tools import tools_supporting_all_suffixes

            try:
                suffixes = [p.suffix.lower() for p in paths]
                tools = tools_supporting_all_suffixes(suffixes)
                if not tools:
                    return
                self.open_in_tool_batch(tools[0], [str(p) for p in paths])  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning("Fix redirect failed for %s", paths, exc_info=exc)

        try:
            run = lint_paths_with_tool(paths)
        except ToolLoadError as exc:
            results = [(path, self._run_local_rulepack_lint(path)) for path in paths]  # type: ignore[attr-defined]
            if any(diagnostics is not None for _path, diagnostics in results):
                lines = []
                for path, diagnostics in results:
                    lines.append(f"{path.name}:")
                    if diagnostics:
                        lines.extend(
                            f"  [{d.line}:{d.column or 1}] {d.message} ({d.rule_id})"
                            for d in diagnostics
                        )
                    else:
                        lines.append(f"  {t('editor.lint_ok')}")
                QMessageBox.warning(self, t("ansyslint.title"), "\n".join(lines))  # type: ignore[arg-type]
            else:
                QMessageBox.warning(self, t("ansyslint.title"), str(exc))  # type: ignore[arg-type]
            return
        except Exception as exc:  # defensive: engine failures stay contained
            logger.warning("ANSYS lint failed for %s", paths, exc_info=exc)
            QMessageBox.warning(
                self, t("ansyslint.title"), f"{type(exc).__name__}: {exc}"  # type: ignore[arg-type]
            )
            return
        names = ", ".join(p.name for p in paths[:3])
        if len(paths) > 3:
            names += f" +{len(paths) - 3}"
        show_ansys_lint_results(
            self, f"{t('ansyslint.title')} — {names}", run, open_in_tool=open_in_tool  # type: ignore[arg-type]
        )


__all__ = ["LocalLintToolsMixin"]
