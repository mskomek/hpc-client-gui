"""wx ANSYS Trusted Tool presentation adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation, ToolRunState


@dataclass(frozen=True)
class FileDiagnostics:
    path: str
    state: ToolRunState


class WxAnsysModel:
    MAX_FOLDER_FILES = 200

    def __init__(self, presentation: AnsysToolPresentation) -> None:
        self.presentation = presentation

    def lint_files(self, files: Iterable[tuple[str, str]]) -> tuple[FileDiagnostics, ...]:
        results = []
        for path, text in files:
            if self.presentation.view.suffixes and Path(path).suffix.lower() not in self.presentation.view.suffixes:
                continue
            results.append(FileDiagnostics(path, self.presentation.run(text, Path(path).name)))
        return tuple(results)

    def lint_folder(self, folder: str | Path, reader) -> tuple[FileDiagnostics, ...]:
        suffixes = self.presentation.view.suffixes
        candidates = [path for path in Path(folder).rglob("*") if path.is_file() and (not suffixes or path.suffix.lower() in suffixes)]
        return self.lint_files(((str(path), reader(path)) for path in candidates[: self.MAX_FOLDER_FILES]))

    @staticmethod
    def group_results(results: Iterable[FileDiagnostics]) -> dict[str, tuple[FileDiagnostics, ...]]:
        groups: dict[str, list[FileDiagnostics]] = {}
        for result in results:
            groups.setdefault(result.state.status, []).append(result)
        return {key: tuple(value) for key, value in groups.items()}

    @staticmethod
    def source_url_allowed(url: str, domains: set[str]) -> bool:
        from hpc_gui.services.help_catalog import is_allowed_external_url

        return is_allowed_external_url(url, domains)


__all__ = ["FileDiagnostics", "WxAnsysModel"]
