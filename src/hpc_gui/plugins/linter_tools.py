"""Lazy, defensive loading of installed Plugin API v2 linter tools.

The loader (``plugins.loader``) only records the declared engine path.
Importing plugin-supplied code happens here - and only when the user
explicitly opens a tool. Every failure is contained in
:class:`ToolLoadError` so a broken engine can never affect application
startup or other plugins.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import sys
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


def _import_engine(package_dir: Path, rel_module_path: str, plugin_id: str, version: str):
    init_path = package_dir / rel_module_path
    if not init_path.is_file():
        raise ToolLoadError(f"Linter engine file is missing: {rel_module_path}")
    if not rel_module_path.endswith("__init__.py"):
        raise ToolLoadError(
            "Linter engine entrypoint must be a package __init__.py"
        )
    # Module identity includes the install location so two checkouts of the
    # same plugin version never share (or poison) each other's modules.
    # The name is a single segment on purpose: dotted dynamic package names
    # make Python's relative-import machinery look up a non-existent parent.
    location_token = hashlib.sha256(str(init_path.parent).encode("utf-8")).hexdigest()[:10]
    full_name = (
        "_hpc_gui_plugin_engine_"
        f"{plugin_id.replace('.', '_')}_{version.replace('.', '_')}_{location_token}"
    )

    existing = sys.modules.get(full_name)
    if existing is not None and hasattr(existing, "__path__"):
        return existing

    spec = importlib.util.spec_from_file_location(
        full_name,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise ToolLoadError(f"Cannot create an import spec for {rel_module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(full_name, None)
        raise ToolLoadError(f"Engine failed to import: {exc}") from exc
    return module


def load_tool_for_plugin(installed) -> LinterTool:
    """Load (and cache) the linter tool of one installed plugin.

    ``installed`` is an :class:`~hpc_gui.plugins.models.InstalledPlugin`.
    """
    manifest = installed.manifest
    cache_key = (manifest.id, manifest.version)
    cached = _TOOL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    engine = installed.linter_engine
    if not isinstance(engine, dict) or not isinstance(engine.get("module"), str):
        raise ToolLoadError("This plugin does not declare a linter engine.")

    module = _import_engine(
        installed.directory,
        str(engine["module"]),
        manifest.id,
        manifest.version,
    )

    factory = getattr(module, "create_plugin", None)
    if not callable(factory):
        raise ToolLoadError("Linter engine does not expose create_plugin().")
    try:
        descriptor = factory()
    except Exception as exc:
        raise ToolLoadError(f"create_plugin() failed: {exc}") from exc

    if not isinstance(descriptor, dict):
        raise ToolLoadError("create_plugin() must return a dict descriptor.")
    title = descriptor.get("title") or manifest.name
    page_factory = descriptor.get("page_factory")
    if not callable(page_factory):
        raise ToolLoadError("Tool descriptor has no usable page_factory.")

    tool = LinterTool(
        plugin_id=manifest.id,
        version=manifest.version,
        title=str(title),
        description=str(descriptor.get("description") or ""),
        page_factory=page_factory,
        module_name=module.__name__,
    )
    _TOOL_CACHE[cache_key] = tool
    logger.info("Loaded linter tool %s@%s (%s)", manifest.id, manifest.version, tool.title)
    return tool


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
    import importlib

    return importlib.import_module(tool.module_name)


def tool_supported_suffixes(tool: LinterTool) -> frozenset[str]:
    """Suffixes one tool's engine declares (empty when undeclarable).

    The engine package ``__init__`` lazily re-exports only the callable
    API; ``SUPPORTED_SUFFIXES`` lives in the ``api`` submodule, so fall
    back to importing that sibling when the attribute is absent.
    """
    import importlib

    try:
        module = _engine_module(tool)
        suffixes = getattr(module, "SUPPORTED_SUFFIXES", None)
        if suffixes is None:
            api = importlib.import_module(f"{tool.module_name}.api")
            suffixes = getattr(api, "SUPPORTED_SUFFIXES", ())
    except (ToolLoadError, ImportError):
        return frozenset()
    return frozenset(str(s).lower() for s in suffixes)


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
