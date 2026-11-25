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
