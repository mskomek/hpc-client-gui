"""Qt-free contracts and privacy regressions for shared UI services."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from hpc_gui.core.debug_telemetry import TelemetryRecorder
from hpc_gui.core.ui_errors import prepare_exception
from hpc_gui.wx_connection_model import describe_wx_connect_failure


@pytest.mark.unit
@pytest.mark.regression
def test_connection_diagnostic_code_matches_log_without_password(caplog):
    secret = "synthetic-private-password"
    safe = describe_wx_connect_failure(
        RuntimeError(f"authentication failed for {secret}"), resolved_password=secret,
    )
    title, message = prepare_exception(title="Connection", user_message=safe, area="SSH")
    assert title == "Connection"
    code = re.search(r"SSH-[0-9A-F]{6}", message)
    assert code is not None
    assert f"Error-ID={code.group(0)}" in caplog.text
    assert secret not in message
    assert secret not in caplog.text
    assert "<redacted>" in message
    _, second = prepare_exception(user_message=safe, area="SSH")
    assert code.group(0) not in second


@pytest.mark.unit
def test_structural_telemetry_records_duration_and_modifiers(caplog):
    times = iter([1.25, 1.375])
    recorder = TelemetryRecorder(clock=lambda: next(times))
    with caplog.at_level("INFO", logger="hpc_gui.debug.telemetry"):
        recorder.action("Button")
        recorder.key("ListCtrl", 127, 0)
        since = recorder.tab_changed("main", 0, 2, 1.0)
        recorder.tab_ready("main", 2, since)
    assert "control=Button" in caplog.text
    assert "key=127 modifiers=0" in caplog.text
    assert "from=0 to=2 previous_visible_ms=250" in caplog.text
    assert "tab=2 render_ms=125" in caplog.text


@pytest.mark.contract
@pytest.mark.subprocess
def test_shared_services_do_not_import_gui_frameworks():
    root = Path(__file__).resolve().parents[1]
    script = """
import importlib.abc
import sys
attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6','wx'}
                or fullname == 'hpc_gui.ui' or fullname.startswith('hpc_gui.ui.')):
            attempts.append(fullname)
            raise ImportError(fullname)
sys.meta_path.insert(0, Guard())
from hpc_gui.core.debug_telemetry import TelemetryRecorder
from hpc_gui.core.ui_errors import prepare_exception
from hpc_gui.services.terminal_bridge import TerminalBridge
assert callable(TerminalBridge().send_input)
TelemetryRecorder().action('Button')
assert 'GEN-' in prepare_exception(user_message='synthetic failure')[1]
assert not attempts, attempts
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.audit
def test_no_production_imports_of_retired_shared_gui_symbols():
    root = Path(__file__).resolve().parents[1] / "src" / "hpc_gui"
    retired = {"hpc_gui.core.ui_errors": "show_exception",
               "hpc_gui.core.debug_telemetry": "DebugTelemetry"}
    errors = []
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.ImportFrom) and node.module in retired:
                if any(alias.name == retired[node.module] for alias in node.names):
                    errors.append(f"{path.relative_to(root)}:{node.lineno}")
    assert not errors, errors


@pytest.mark.contract
@pytest.mark.subprocess
def test_direct_app_entrypoint_is_wx_only():
    root = Path(__file__).resolve().parents[1]
    script = """
import importlib.abc
import sys
attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'}
                or fullname == 'hpc_gui.ui' or fullname.startswith('hpc_gui.ui.')):
            attempts.append(fullname)
            raise ImportError(fullname)
sys.meta_path.insert(0, Guard())
from hpc_gui.app import main
assert main.__module__ == 'hpc_gui.wx_shell'
assert not attempts, attempts
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
