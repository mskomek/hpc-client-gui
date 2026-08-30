"""Lazy, defensive loading of installed Plugin API v2 linter tools.

The loader (``plugins.loader``) only records the declared engine path.
Importing plugin-supplied code happens here - and only when the user
explicitly opens a tool. Every failure is contained in
:class:`ToolLoadError` so a broken engine can never affect application
startup or other plugins.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from hpc_gui.plugins.loader import load_installed_plugins

logger = logging.getLogger(__name__)

_TOOL_CACHE: dict[tuple[str, str], LinterTool] = {}


class ToolLoadError(RuntimeError):
    """Raised when an installed linter tool cannot be loaded."""


@dataclass(frozen=True)
class LinterTool:
    """A successfully loaded plugin tool descriptor."""

    plugin_id: str
    version: str
    title: str
    description: str
    page_factory: Callable[..., Any]
    module_name: str

    @property
    def display_name(self) -> str:
        return self.title


def load_tool_for_plugin(installed) -> LinterTool:
    """Load (and cache) the linter tool of one installed plugin.

    ``installed`` is an :class:`~hpc_gui.plugins.models.InstalledPlugin`.
    """
    raise ToolLoadError(
        "Executable linter plugins are disabled. Update or reinstall this plugin "
        "as a declarative rule pack."
    )


def list_linter_tools(root=None, app_version=None) -> list[LinterTool]:
    """Load every available linter tool from active installed plugins."""
    from hpc_gui import __version__ as default_version

    tools: list[LinterTool] = []
    result = load_installed_plugins(root=root, app_version=app_version or default_version)
    for installed in result.plugins:
        if "linter-tool" not in installed.manifest.capabilities:
            continue
        try:
            tools.append(load_tool_for_plugin(installed))
        except ToolLoadError as exc:
            logger.warning("Skipping linter tool %s@%s: %s",
                           installed.manifest.id, installed.manifest.version, exc)
    return tools


_NOT_INSTALLED_MESSAGE = (
    "No linter tool plugin is installed. Install the ANSYS Script & Journal "
    "Linter from the Plugin Manager (Discover tab)."
)


def first_linter_tool(root=None, app_version=None) -> LinterTool:
    tools = list_linter_tools(root=root, app_version=app_version)
    if not tools:
        raise ToolLoadError(_NOT_INSTALLED_MESSAGE)
    return tools[0]


def _engine_module(tool: LinterTool):
    raise ToolLoadError("Executable plugin engines are disabled.")


def tool_supported_suffixes(tool: LinterTool) -> frozenset[str]:
    """Suffixes one tool's engine declares (empty when undeclarable).

    The engine package ``__init__`` lazily re-exports only the callable
    API; ``SUPPORTED_SUFFIXES`` lives in the ``api`` submodule, so fall
    back to importing that sibling when the attribute is absent.
    """
    return frozenset()


def supported_suffixes() -> frozenset[str]:
    """File suffixes the installed linter tool understands (empty if none)."""
    try:
        tool = first_linter_tool()
    except ToolLoadError:
        return frozenset()
    return tool_supported_suffixes(tool)


def tools_supporting_suffix(suffix: str, root=None, app_version=None) -> list[LinterTool]:
    """Every installed tool whose engine supports a file suffix."""
    wanted = str(suffix).lower()
    if not wanted:
        return []
    matches: list[LinterTool] = []
    for tool in list_linter_tools(root=root, app_version=app_version):
        if wanted in tool_supported_suffixes(tool):
            matches.append(tool)
    return matches


def temp_copy_for_tool(text: str, file_name: str):
    """Materialize in-memory content under its real name for tool pages.

    Tool pages re-read paths from disk, so remote files must exist
    locally for the duration of the hosted page. The caller removes the
    returned path with :func:`remove_temp_copy` once the page closes.
    """
    import tempfile

    suffix = Path(file_name).suffix or ".txt"
    handle = tempfile.NamedTemporaryFile(
        prefix="hpcgui-lint-",
        suffix=suffix,
        delete=False,
        mode="w",
        encoding="utf-8",
        newline="",
    )
    try:
        handle.write(text)
    finally:
        handle.close()
    return Path(handle.name)


def remove_temp_copy(path) -> None:
    """Best-effort cleanup for :func:`temp_copy_for_tool` results."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove lint temp copy %s", path, exc_info=True)


def lint_paths_with_tool(paths, options=None):
    """Run the installed engine over files/folders; returns its run result."""
    module = _engine_module(first_linter_tool())
    if options is None:
        return module.lint_paths(paths)
    return module.lint_paths(paths, options)


def lint_text_with_tool(text: str, *, file_name: str = "", options=None):
    """Run the installed engine over in-memory content."""
    module = _engine_module(first_linter_tool())
    if options is None:
        return module.lint_text(text, file_name=file_name)
    return module.lint_text(text, file_name=file_name, options=options)


def lint_text_with_tool_for(
    tool: LinterTool, text: str, *, file_name: str = "", options=None
):
    """Run a specific installed engine over in-memory content."""
    module = _engine_module(tool)
    if options is None:
        return module.lint_text(text, file_name=file_name)
    return module.lint_text(text, file_name=file_name, options=options)


def tools_supporting_all_suffixes(
    suffixes: list[str], root=None, app_version=None
) -> list[LinterTool]:
    """Tools whose engine supports every suffix in the list."""
    wanted = [str(s).lower() for s in suffixes if str(s).lower()]
    if not wanted:
        return []
    candidates = list_linter_tools(root=root, app_version=app_version)
    matching: list[LinterTool] = []
    for tool in candidates:
        declared = tool_supported_suffixes(tool)
        if all(s in declared for s in wanted):
            matching.append(tool)
    return matching
