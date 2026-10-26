"""Verified-byte API 3 linter loader isolated from API 2 compatibility."""
from __future__ import annotations

import hashlib
import importlib
import importlib.abc
import importlib.machinery
import re
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable

from hpc_gui.plugins.trusted_api3 import api3_verified_sources

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
    wx_page_factory: Callable[..., Any] | None = None

    @property
    def display_name(self) -> str:
        return self.title


class _Api3PinnedLoader(importlib.abc.Loader):
    """Execute one pinned payload; no disk, sys.path, or CWD access."""

    def __init__(self, table) -> None:
        self._table = table

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        try:
            rel, data = self._table[module.__name__]
        except KeyError as exc:
            raise ImportError(f"unpinned API 3 module {module.__name__!r}") from exc
        code = compile(bytes(data), f"<pinned:{rel}>", "exec")
        exec(code, module.__dict__)


class _Api3PinnedFinder(importlib.abc.MetaPathFinder):
    """Serve ONLY one private API 3 namespace from verified bytes.

    Immutable ``table`` maps full dotted name -> (pinned rel, bytes).
    Package payloads (``.../__init__.py``) get an empty
    ``submodule_search_locations`` so unpinned siblings fail closed via
    normal import semantics instead of falling back to the filesystem.
    Anything outside ``root`` returns None (host importers handle it).
    """

    def __init__(self, root: str, table) -> None:
        self.root = root
        self._table = table

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self.root and not fullname.startswith(self.root + "."):
            return None
        entry = self._table.get(fullname)
        if entry is None:
            return None
        rel, _data = entry
        is_pkg = rel.endswith("/__init__.py")
        loader = _Api3PinnedLoader(self._table)
        spec = importlib.machinery.ModuleSpec(fullname, loader, is_package=is_pkg)
        if is_pkg:
            spec.submodule_search_locations = []
        return spec


def _api3_pinned_table(module_name: str, rel: str, sources: dict[str, bytes]):
    """Map private dotted names to pinned payloads under the entry dir."""
    prefix = rel.rsplit("/", 1)[0] if "/" in rel else ""
    table: dict[str, tuple[str, bytes]] = {}
    for pinned_rel, data in sources.items():
        if not pinned_rel.endswith(".py") or not isinstance(data, (bytes, bytearray)):
            continue
        if prefix:
            if pinned_rel != rel and not pinned_rel.startswith(prefix + "/"):
                continue
            if pinned_rel == rel:
                full = module_name
            else:
                leaf = pinned_rel[len(prefix) + 1:]
                if leaf.endswith("/__init__.py"):
                    parts = leaf[: -len("/__init__.py")].split("/")
                    if not all(p.isidentifier() for p in parts):
                        continue
                    full = module_name + "." + ".".join(parts)
                elif "/" in leaf:
                    parts = leaf[:-len(".py")].split("/")
                    if not all(p.isidentifier() for p in parts):
                        continue
                    full = module_name + "." + ".".join(parts)
                else:
                    stem = leaf[:-len(".py")]
                    if not stem.isidentifier():
                        continue
                    full = module_name + "." + stem
        else:
            if pinned_rel != rel:
                continue
            full = module_name
        table.setdefault(full, (pinned_rel, bytes(data)))
    return MappingProxyType(table)


def _remove_api3_finder(module_name: str) -> None:
    for existing in list(sys.meta_path):
        if isinstance(existing, _Api3PinnedFinder) and existing.root == module_name:
            try:
                sys.meta_path.remove(existing)
            except ValueError:
                pass


def unload_api3_engine(module_name: str) -> None:
    """Remove a failed API 3 namespace and its scoped byte finder."""
    _remove_api3_finder(module_name)
    _remove_module_namespace(module_name)


def _load_api3_engine_verified(installed, rel: str):
    """Import the API 3 engine ONLY from pin-verified bytes (no re-read).

    The exact ``rel -> bytes`` mapping comes from the host-owned
    :func:`api3_verified_sources` gate (hash-checked, link-rejecting,
    no-follow reads); the manifest alone never grants trust and no path
    is re-read from disk afterwards. A scoped ``sys.meta_path`` finder,
    constrained to this tool's private namespace with an immutable
    table, lazily serves only pinned ``pkg/__init__.py`` and
    ``module.py`` payloads, so relative imports work, import caching and
    normal cycles behave as usual, and the package is registered in
    ``sys.modules`` before its code runs. Unpinned names fail closed
    (``ImportError``); ``__path__`` never points at the filesystem and
    ``sys.path``/CWD are untouched. Verified hashes attest to content
    only: the engine still runs as in-process host code with the user's
    privileges (not an OS sandbox).
    """
    from pathlib import Path as _Path

    package_dir = _Path(installed.directory)
    try:
        sources = api3_verified_sources(installed.manifest, package_dir)
    except OSError as exc:
        raise ToolLoadError(
            f"Plugin API 3 tool is not application-approved: {exc}"
        ) from exc
    if rel not in sources:
        raise ToolLoadError("Trusted tool entrypoint is not approved.")
    module_name = _tool_module_name(installed)
    table = _api3_pinned_table(module_name, rel, sources)
    if module_name not in table:
        raise ToolLoadError("Trusted tool entrypoint is not approved.")
    parent_pkg = rel.rsplit("/", 1)[0].replace("/", ".") if "/" in rel else ""
    _remove_api3_finder(module_name)
    finder = _Api3PinnedFinder(module_name, table)
    sys.meta_path.insert(0, finder)
    _remove_module_namespace(module_name)
    previous_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            try:
                sys.meta_path.remove(finder)
            except ValueError:
                pass
            _remove_module_namespace(module_name)
            raise ToolLoadError(f"Trusted tool failed to load: {exc}") from exc
    finally:
        sys.dont_write_bytecode = previous_dont_write_bytecode
    module.__hpc_api3__ = True  # marker: no filesystem sibling fallback
    module.__hpc_pinned_package__ = parent_pkg
    if not callable(getattr(module, "create_plugin", None)):
        try:
            sys.meta_path.remove(finder)
        except ValueError:
            pass
        _remove_module_namespace(module_name)
        raise ToolLoadError("Trusted tool has no callable create_plugin factory")
    return module
