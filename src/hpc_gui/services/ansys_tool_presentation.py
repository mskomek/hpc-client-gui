"""Framework-neutral ANSYS Trusted Tool presentation contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpc_gui.plugins.linter_tools import LinterTool, ToolLoadError, tool_supported_suffixes
from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool


@dataclass(frozen=True)
class AnsysToolViewModel:
    plugin_id: str
    version: str
    title: str
    description: str
    suffixes: frozenset[str]
    actions: tuple[str, ...] = ("lint", "open")


@dataclass(frozen=True)
class ToolRunState:
    status: str
    diagnostics: tuple[Any, ...] = ()
    error: str = ""


class AnsysToolPresentation:
    def __init__(self, tool: LinterTool) -> None:
        self.tool = tool
        try:
            suffixes = tool_supported_suffixes(tool)
        except ToolLoadError:
            suffixes = frozenset()
        self.view = AnsysToolViewModel(tool.plugin_id, tool.version, tool.title, tool.description, suffixes)

    def run(self, text: str, file_name: str = "") -> ToolRunState:
        try:
            module = __import__(self.tool.module_name, fromlist=["lint_text"])
            diagnostics = tuple(module.lint_text(text, file_name=file_name))
            return ToolRunState("completed", diagnostics)
        except Exception as exc:
            return ToolRunState("failed", error=str(exc))

    def open_page(self, parent=None) -> Any:
        return self.tool.page_factory(parent=parent)


def approved_tool_manifest(manifest: dict[str, Any]) -> bool:
    return is_approved_trusted_tool(manifest)


__all__ = ["AnsysToolPresentation", "AnsysToolViewModel", "ToolRunState", "approved_tool_manifest"]
