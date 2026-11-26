"""Actual menu events, grouped results, snapshot tool redirect and stale session."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_file_lint_menu_and_remote_generation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import sys
import time
import threading
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import wx
from hpc_gui.core.i18n import load_language
from hpc_gui.services.file_context_actions import context_selection
from hpc_gui.services.file_lint import LintCatalog
from hpc_gui.plugins.linter_tools import LinterTool
from hpc_gui.wx_file_lint import append_file_lint_actions
from hpc_gui.wx_shell_files import _file_lint_callback

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
frame.Show()
local = Path(sys.argv[1]) / "a.jou"
local.write_text("local journal", encoding="utf-8")
tool = LinterTool("org.test", "1", "Test", "Fixture", lambda **kwargs: None, "_fixture")
catalog = LintCatalog((), ((tool, frozenset({".jou"})),))
state = {"session": None, "generation": 1}
calls = []
shown = []
opened = []
def result(tool, text, file_name):
    calls.append((file_name, text))
    return NS(diagnostics=[NS(code="W1", severity=NS(value="warning"), message="finding",
        line=2, column=1, suggested_fix="fix", source_url="https://docs.ansys.com/rule")])
def show(owner, title, results, open_in_tool=None):
    shown.append(results)
    if open_in_tool:
        open_in_tool()
def open_tool(owner, presentation, lifecycle=None, initial_documents=None):
    opened.append(initial_documents)
def pump(predicate):
    end = time.monotonic() + 8
    while time.monotonic() < end:
        wx.Yield()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError("condition timed out")
def dispatch(selection, remote=False, tool_only=False):
    menu = wx.Menu()
    items = append_file_lint_actions(menu, selection,
        _file_lint_callback(state, None, remote=remote), frame)
    try:
        item = items["files.send_to_plugin" if tool_only else "editor.lint"]
        event = wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId())
        event.SetEventObject(menu)
        assert menu.ProcessEvent(event)
    finally:
        menu.Destroy()
def done():
    return frame._wx_file_lint_request is None

class Remote:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.block = False
        self.reads = []
    def is_dir(self, path):
        return False
    def stat(self, path):
        return 14, 0
    def read_text(self, path):
        self.reads.append(path)
        self.entered.set()
        if self.block:
            assert self.release.wait(5)
        return "remote journal"

backend = Remote()
with patch("hpc_gui.wx_file_lint.load_catalog", return_value=catalog),      patch("hpc_gui.plugins.linter_tools.lint_text_with_tool_for", result),      patch("hpc_gui.wx_lint_results.show_lint_results", show),      patch("hpc_gui.wx_ansys_view.show_ansys_lint", open_tool),      patch("hpc_gui.services.ansys_tool_presentation.tool_supported_suffixes", return_value=frozenset({".jou"})):
    dispatch(context_selection(str(local), False))
    pump(done)
    assert shown[0].files[0].summary["warning"] == 1
    assert opened == [((str(local), "local journal"),)]
    assert local.read_text() == "local journal"
    state["session"] = {"files": backend}
    dispatch(context_selection("/job/b.jou", False), remote=True, tool_only=True)
    pump(done)
    assert opened[-1] == (("/job/b.jou", "remote journal"),)
    assert calls == [(str(local), "local journal")]
    backend.entered.clear()
    backend.block = True
    dispatch(context_selection("/job/c.jou", False), remote=True)
    pump(backend.entered.is_set)
    state["generation"] += 1
    backend.release.set()
    pump(done)
    assert len(shown) == 1 and len(opened) == 2
    assert backend.reads == ["/job/b.jou", "/job/c.jou"]
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr
