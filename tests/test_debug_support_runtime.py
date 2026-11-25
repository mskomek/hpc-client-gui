"""Framework-neutral diagnostics must not initialize a native toolkit."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.regression
def test_startup_snapshot_does_not_import_gui_toolkits():
    script = """
import importlib.abc
import logging
import sys
from types import SimpleNamespace

attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'PySide6', 'PyQt5', 'PyQt6', 'shiboken6', 'wx'}:
            attempts.append(fullname)
            raise ImportError(fullname)
sys.meta_path.insert(0, Guard())

from hpc_gui.core.debug_support import log_startup_snapshot
logging.basicConfig(level=logging.INFO)
log_startup_snapshot()
assert not attempts, attempts
sys.modules['wx'] = SimpleNamespace(__version__='test-wx-version')
log_startup_snapshot()
assert not attempts, attempts
"""
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wxpython=test-wx-version" in result.stderr


@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.regression
@pytest.mark.parametrize("arguments", [[], ["--wx"], ["--updater-helper", "unused.json"], ["version"]])
def test_v2_entrypoint_never_imports_legacy_gui(arguments):
    script = """
import importlib.abc
import runpy
import sys

attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in {'PySide6', 'PyQt5', 'PyQt6', 'shiboken6'}
                or fullname == 'hpc_gui.app'
                or fullname.startswith('hpc_gui.ui.')):
            attempts.append(fullname)
            raise ImportError(fullname)
sys.meta_path.insert(0, Guard())
namespace = runpy.run_module('hpc_gui.__main__', run_name='entrypoint_probe')
if '--updater-helper' in sys.argv:
    assert callable(namespace['run_helper'])
elif 'version' in sys.argv:
    assert callable(namespace['run_cli'])
else:
    assert namespace['main'].__module__ == 'hpc_gui.wx_shell'
assert not attempts, attempts
"""
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script, *arguments], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.contract
def test_cli_gui_rejects_non_wx_runtime(monkeypatch):
    from hpc_gui.cli import gui

    monkeypatch.setattr(gui, "DEFAULT_GUI_RUNTIME", "qt")
    with pytest.raises(RuntimeError, match="requires the wx GUI runtime"):
        gui.launch_gui()


@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.regression
def test_pytest_fixture_collection_does_not_import_legacy_qt():
    script = """
import importlib.abc
import runpy
import sys
from pathlib import Path

attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in {'PySide6', 'PyQt5', 'PyQt6', 'shiboken6'}
                or fullname == 'hpc_gui.ui'
                or fullname.startswith('hpc_gui.ui.')):
            attempts.append(fullname)
            raise ImportError(fullname)
sys.meta_path.insert(0, Guard())
runpy.run_path(str(Path('tests/conftest.py').resolve()))
assert not attempts, attempts
"""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
