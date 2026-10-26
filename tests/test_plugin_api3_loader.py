"""Scoped API 3 loader: verified-bytes-only package imports.

Uses synthetic ``api3_verified_sources`` mappings via monkeypatch (never
production pins). Covers relative imports, lazy siblings, a safe import
cycle, unpinned/mismatched/no-fallback rejection, and failure cleanup.
"""

from __future__ import annotations

import sys
from types import MappingProxyType, SimpleNamespace

import pytest

from hpc_gui.plugins import linter_tools
from hpc_gui.plugins.linter_tools import (
    ToolLoadError,
    _remove_module_namespace,
    _tool_module_name,
)


def _installed(tmp_path, *, ident="org.example.apithree", version="9.9.9"):
    manifest = SimpleNamespace(id=ident, version=version, files=())
    return SimpleNamespace(manifest=manifest, directory=str(tmp_path))


def _cleanup(module_name):
    linter_tools._remove_api3_finder(module_name)
    _remove_module_namespace(module_name)


def _tracked_load(monkeypatch, tmp_path, rel, sources):
    installed = _installed(tmp_path)
    module_name = _tool_module_name(installed)
    monkeypatch.setattr(
        # The isolated byte loader owns this imported trust-boundary
        # reference. Patching the public facade alias would not intercept
        # the loader and would accidentally consult production pins.
        "hpc_gui.plugins._api3_engine_loader.api3_verified_sources",
        lambda manifest, package_dir: dict(sources),
    )
    return installed, module_name


def _finder_for(module_name):
    return [
        f for f in sys.meta_path
        if isinstance(f, linter_tools._Api3PinnedFinder) and f.root == module_name
    ]


def test_package_relative_imports_and_caching(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    sources = {
        rel: (
            b"from .api import VALUE\nfrom . import sub\n"
            b"SUPPORTED_SUFFIXES = frozenset()\n"
            b"def create_plugin():\n"
            b"    return {'title': 'T', 'description': 'd',"
            b" 'page_factory': lambda parent=None: None}\n"
        ),
        "engine/pkg/api.py": b"VALUE = 41 + 1\n",
        "engine/pkg/sub.py": b"SUB = 's'\n",
    }
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    try:
        module = linter_tools._load_api3_engine_verified(installed, rel)
        assert module.VALUE == 42
        assert module.sub.SUB == "s"
        assert module.__package__ == name
        assert module.__path__ == []
        assert module.__hpc_api3__ is True
        assert sys.modules[name] is module
        assert sys.modules[name + ".api"].VALUE == 42
        import importlib

        assert importlib.import_module(name) is module
        assert importlib.import_module(name + ".api").VALUE == 42
        finder = _finder_for(name)
        assert len(finder) == 1
        assert isinstance(finder[0]._table, MappingProxyType)
        assert finder[0].find_spec("os", None) is None
        assert finder[0].find_spec(name + ".nope", None) is None
    finally:
        _cleanup(name)
    assert name not in sys.modules


def test_single_module_entrypoint(monkeypatch, tmp_path):
    rel = "engine/tool.py"
    sources = {
        rel: (
            b"SUPPORTED_SUFFIXES = frozenset()\n"
            b"def create_plugin():\n"
            b"    return {'title': 'Solo', 'description': 'd',"
            b" 'page_factory': lambda parent=None: None}\n"
            b"ANSWER = 7\n"
        ),
    }
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    try:
        module = linter_tools._load_api3_engine_verified(installed, rel)
        assert module.ANSWER == 7
        assert not getattr(module, "__path__", None)
    finally:
        _cleanup(name)


def test_siblings_stay_lazy_until_imported(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    sources = {
        rel: (
            b"SUPPORTED_SUFFIXES = frozenset()\n"
            b"def create_plugin():\n"
            b"    return {'title': 'T', 'description': 'd',"
            b" 'page_factory': lambda parent=None: None}\n"
        ),
        "engine/pkg/deferred.py": b"MARKER = object()\n",
    }
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    try:
        linter_tools._load_api3_engine_verified(installed, rel)
        assert name + ".deferred" not in sys.modules
        import importlib

        assert importlib.import_module(name + ".deferred").MARKER is not None
    finally:
        _cleanup(name)


def test_safe_relative_import_cycle(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    sources = {
        rel: (
            b"from . import a\n"
            b"def create_plugin():\n"
            b"    return {'title': 'T', 'description': 'd',"
            b" 'page_factory': lambda parent=None: None}\n"
        ),
        "engine/pkg/a.py": b"X = 1\nfrom . import b\n",
        "engine/pkg/b.py": b"from . import a\nY = a.X + 1\n",
    }
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    try:
        module = linter_tools._load_api3_engine_verified(installed, rel)
        assert sys.modules[name + ".a"].X == 1
        assert sys.modules[name + ".b"].Y == 2
        assert module.a.b.Y == 2
    finally:
        _cleanup(name)


def test_unpinned_import_fails_closed(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    sources = {
        rel: (
            b"from . import missing\n"
            b"def create_plugin():\n"
            b"    return {'title': 'T', 'description': 'd',"
            b" 'page_factory': lambda parent=None: None}\n"
        ),
    }
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    path_before = list(sys.path)
    with pytest.raises(ToolLoadError):
        linter_tools._load_api3_engine_verified(installed, rel)
    assert name not in sys.modules
    assert not [m for m in sys.modules if m == name or m.startswith(name + ".")]
    assert _finder_for(name) == []
    assert list(sys.path) == path_before


def test_hash_mismatch_rejected_before_exec(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"POISON = True\n")
    installed = _installed(tmp_path)
    name = _tool_module_name(installed)

    def _mismatch(manifest, package_dir):
        raise OSError("payload integrity mismatch for 'engine/pkg/__init__.py'")

    monkeypatch.setattr(
        "hpc_gui.plugins._api3_engine_loader.api3_verified_sources", _mismatch
    )
    with pytest.raises(ToolLoadError, match="application-approved"):
        linter_tools._load_api3_engine_verified(installed, rel)
    assert "POISON" not in str(getattr(sys.modules.get(name), "__dict__", ""))
    assert name not in sys.modules
    assert _finder_for(name) == []


def test_no_disk_fallback_uses_verified_bytes(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"raise RuntimeError('must not import from disk')\n")
    good = (
        b"VALUE = 'verified'\n"
        b"def create_plugin():\n"
        b"    return {'title': 'Good', 'description': 'd',"
        b" 'page_factory': lambda parent=None: None}\n"
    )
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, {rel: good})
    try:
        module = linter_tools._load_api3_engine_verified(installed, rel)
        assert module.VALUE == "verified"
        assert getattr(module, "__file__", None) is None
    finally:
        _cleanup(name)


def test_exec_failure_cleans_up(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    sources = {rel: b"raise RuntimeError('boom')\n"}
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    path_before = list(sys.path)
    with pytest.raises(ToolLoadError, match="failed to load"):
        linter_tools._load_api3_engine_verified(installed, rel)
    assert not [m for m in sys.modules if m == name or m.startswith(name + ".")]
    assert _finder_for(name) == []
    assert list(sys.path) == path_before


def test_absolute_unpinned_package_name_not_served(monkeypatch, tmp_path):
    rel = "engine/pkg/__init__.py"
    sources = {
        rel: (
            b"def create_plugin():\n"
            b"    return {'title': 'T', 'description': 'd',"
            b" 'page_factory': lambda parent=None: None}\n"
        ),
    }
    installed, name = _tracked_load(monkeypatch, tmp_path, rel, sources)
    try:
        linter_tools._load_api3_engine_verified(installed, rel)
        finder = _finder_for(name)[0]
        assert finder.find_spec("hpc_gui.plugins.openfoam_lint.api", None) is None
        assert finder.find_spec("unrelated", None) is None
    finally:
        _cleanup(name)
