"""Lazy, defensive loading of the application-approved ANSYS trusted tool.

The loader (``plugins.loader``) only records the declared engine path.
Importing plugin-supplied code happens here - and only when the user
explicitly opens a tool. Every failure is contained in
:class:`ToolLoadError` so a broken engine can never affect application
startup or other plugins.
"""

from __future__ import annotations

import logging
from pathlib import Path
import importlib
import importlib.machinery
import importlib.util
import sys
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.trusted_api3 import api3_linter_entrypoint
from hpc_gui.plugins.trusted_tools import (
    APPROVED_TRUSTED_TOOLS,
    is_approved_trusted_tool,
)
from hpc_gui.plugins._api3_engine_loader import (
    LinterTool,
    ToolLoadError,
    _Api3PinnedFinder as _Api3PinnedFinder,
    _api3_pinned_table as _api3_pinned_table,
    _load_api3_engine_verified,
    _remove_api3_finder as _remove_api3_finder,
    _remove_module_namespace,
    _tool_module_name,
    unload_api3_engine,
)

logger = logging.getLogger(__name__)


def load_tool_for_plugin(installed) -> LinterTool:
    """Load (and cache) the linter tool of one installed plugin.

    ``installed`` is an :class:`~hpc_gui.plugins.models.InstalledPlugin` whose
    identity has passed the application-owned Trusted Tool policy (API v2)
    or the application-owned API v3 release pin (exact identity, contract
    and payload hashes, re-verified from bytes on disk here, immediately
    before import).
    """
    descriptor = getattr(installed, "linter_engine", None) or {}
    rel = descriptor.get("module")
    if getattr(installed.manifest, "plugin_api", None) == 3:
        # Verified-bytes gate: the expected path is policy-derived (the
        # host pin's entrypoint), never manifest-derived. The bounded
        # loader below executes only pin-verified bytes (no disk re-read),
        # closing the hash-to-import race for the pinned closure.
        expected = api3_linter_entrypoint(installed.manifest)
        if expected is None or rel != expected:
            raise ToolLoadError("Trusted tool entrypoint is not approved.")
        module = _load_api3_engine_verified(installed, rel)
        module_name = module.__name__
        try:
            tool_descriptor = module.create_plugin()
            if not isinstance(tool_descriptor, dict):
                raise TypeError("create_plugin must return a descriptor object")
            if tool_descriptor.get("id") != installed.manifest.id:
                raise TypeError("create_plugin id does not match the installed plugin")
            page_factory = tool_descriptor.get("page_factory")
            wx_page_factory = tool_descriptor.get("wx_page_factory")
            if not callable(page_factory):
                raise TypeError("create_plugin must return a callable page_factory")
            if wx_page_factory is not None and not callable(wx_page_factory):
                raise TypeError("create_plugin wx_page_factory must be callable")
        except Exception as exc:
            unload_api3_engine(module_name)
            raise ToolLoadError(f"Trusted tool descriptor is invalid: {exc}") from exc
        return LinterTool(
            plugin_id=installed.manifest.id,
            version=installed.manifest.version,
            title=str(tool_descriptor["title"]),
            description=str(tool_descriptor.get("description", "")),
            page_factory=page_factory,
            module_name=module_name,
            wx_page_factory=wx_page_factory,
        )
    else:
        if not is_approved_trusted_tool(installed.manifest):
            raise ToolLoadError("Executable plugin is disabled unless it is an application-approved trusted tool.")
        # W65 r12: the expected engine path is policy-derived (one approved
        # entrypoint per plugin identity), never manifest-derived. An approved
        # id with a wrong publisher already fails is_approved_trusted_tool
        # above, so keying on the id here cannot be spoofed by a manifest.
        policy = APPROVED_TRUSTED_TOOLS.get(getattr(installed.manifest, "id", None))
        expected = policy["entrypoint"] if isinstance(policy, dict) else None
    if expected is None or rel != expected:
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
            wx_page_factory=descriptor.get("wx_page_factory"),
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
    back to that sibling when the attribute is absent. API 3 engines
    (``__hpc_api3__``) never fall back to a filesystem import: only an
    already-loaded pinned ``.api`` module from verified bytes is read,
    otherwise the suffix set stays empty (fail closed).
    """
    module = _engine_module(tool)
    suffixes = getattr(module, "SUPPORTED_SUFFIXES", None)
    if suffixes is None:
        if getattr(module, "__hpc_api3__", False):
            api = sys.modules.get(f"{module.__name__}.api")
            if api is None:
                return frozenset()
        else:
            try:
                api = sys.modules.get(f"{module.__name__}.api") or importlib.import_module(f"{module.__name__}.api")
            except (AttributeError, ImportError):
                return frozenset()
        try:
            suffixes = api.SUPPORTED_SUFFIXES
        except AttributeError:
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
