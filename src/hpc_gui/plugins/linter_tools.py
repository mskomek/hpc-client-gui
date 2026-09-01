"""Lazy, defensive loading of the application-approved ANSYS trusted tool.

The loader (``plugins.loader``) only records the declared engine path.
Importing plugin-supplied code happens here - and only when the user
explicitly opens a tool. Every failure is contained in
:class:`ToolLoadError` so a broken engine can never affect application
startup or other plugins.
"""

from __future__ import annotations

import logging
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import importlib.util
import importlib
import sys

from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool

logger = logging.getLogger(__name__)

def _tool_module_name(installed) -> str:
    """Return a private namespace for this immutable installed tool."""
    manifest = installed.manifest
    identity = "\0".join(
        [manifest.id, manifest.version, *(file.sha256 for file in manifest.files)]
    )
    digest = hashlib.sha256(identity.encode("ascii")).hexdigest()[:16]
    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", manifest.id)
    return f"_hpc_gui_trusted_{safe_id}_{digest}"


def _remove_module_namespace(module_name: str) -> None:
    for name in tuple(sys.modules):
        if name == module_name or name.startswith(module_name + "."):
            sys.modules.pop(name, None)


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

    ``installed`` is an :class:`~hpc_gui.plugins.models.InstalledPlugin` whose
    identity has passed the application-owned Trusted Tool policy.
    """
    if not is_approved_trusted_tool(installed.manifest):
        raise ToolLoadError("Executable plugin is disabled unless it is an application-approved trusted tool.")
    descriptor = getattr(installed, "linter_engine", None) or {}
    rel = descriptor.get("module")
    if rel != "engine/ansys_lint/__init__.py":
        raise ToolLoadError("Trusted tool entrypoint is not approved.")
    package_dir = Path(installed.directory)
    init_path = package_dir / rel
    if not init_path.is_file():
        raise ToolLoadError("Trusted tool engine is missing.")
    module_name = _tool_module_name(installed)
    previous_dont_write_bytecode = sys.dont_write_bytecode
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, init_path, submodule_search_locations=[str(init_path.parent)]
        )
        if spec is None or spec.loader is None:
            raise ToolLoadError("Trusted tool engine cannot be loaded.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_dont_write_bytecode
        descriptor = module.create_plugin()
        return LinterTool(
            plugin_id=installed.manifest.id,
            version=installed.manifest.version,
            title=str(descriptor["title"]),
            description=str(descriptor.get("description", "")),
            page_factory=descriptor["page_factory"],
            module_name=module_name,
        )
    except ToolLoadError:
        raise
    except Exception as exc:
        sys.dont_write_bytecode = previous_dont_write_bytecode
        _remove_module_namespace(module_name)
        raise ToolLoadError(f"Trusted tool failed to load: {exc}") from exc


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
    try:
        return sys.modules[tool.module_name]
    except KeyError as exc:
        raise ToolLoadError("Trusted tool is no longer loaded.") from exc


def tool_supported_suffixes(tool: LinterTool) -> frozenset[str]:
    """Suffixes one tool's engine declares (empty when undeclarable).

    The engine package ``__init__`` lazily re-exports only the callable
    API; ``SUPPORTED_SUFFIXES`` lives in the ``api`` submodule, so fall
    back to importing that sibling when the attribute is absent.
    """
    module = _engine_module(tool)
    suffixes = getattr(module, "SUPPORTED_SUFFIXES", None)
    if suffixes is None:
        try:
            api = sys.modules.get(f"{module.__name__}.api") or importlib.import_module(f"{module.__name__}.api")
            suffixes = api.SUPPORTED_SUFFIXES
        except (AttributeError, ImportError):
            return frozenset()
    return frozenset(str(value).lower() for value in suffixes)


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
        try:
            supported = tool_supported_suffixes(tool)
        except ToolLoadError:
            continue
        if wanted in supported:
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
        try:
            declared = tool_supported_suffixes(tool)
        except ToolLoadError:
            continue
        if all(s in declared for s in wanted):
            matching.append(tool)
    return matching
