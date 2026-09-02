"""wx editor model using the shared document, template, and lint services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hpc_gui.services.editor_controller import DocumentModel, EditorCommandService, EditorController, LintResult
from hpc_gui.services.focus_command_router import FocusCommandRouter
from hpc_gui.plugins.job_templates import JobTemplate, render_template


@dataclass(frozen=True)
class Diagnostic:
    source: str
    result: LintResult


class WxEditorModel:
    def __init__(self) -> None:
        self.controller = EditorController()
        self.diagnostics: tuple[Diagnostic, ...] = ()

    def open(self, path: str, content: str, *, is_local: bool = False) -> int:
        return self.controller.open(DocumentModel(path, content, content, is_local, suggested_filename=EditorCommandService.suggested_filename(path)))

    def save_target(self, *, submit: bool = False, run: bool = False) -> str:
        active = self.controller.active
        return EditorCommandService.execute_mode(active.path if active else "", force_submit=submit, run_in_terminal=run)

    def render_template(self, template: JobTemplate, values: dict[str, object]) -> int:
        content = render_template(template, values)
        return self.controller.open(DocumentModel(template.file_name, content, "", False, suggested_filename=template.file_name))

    def aggregate_lint(self, results: Iterable[tuple[str, LintResult]]) -> tuple[Diagnostic, ...]:
        seen = set()
        merged = []
        for source, result in results:
            key = (result.line, result.column, result.message)
            if key not in seen:
                seen.add(key)
                merged.append(Diagnostic(source, result))
        self.diagnostics = tuple(merged)
        return self.diagnostics

    @staticmethod
    def route_shortcut(binding: str, context: str, *, text_input: bool = False) -> str | None:
        command = FocusCommandRouter().resolve(binding, context, text_input=text_input)
        return command.id if command else None


__all__ = ["Diagnostic", "WxEditorModel"]
