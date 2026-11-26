"""Native About dialog and offline legal-file access regressions."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.semantic
@pytest.mark.parametrize("fallback", [False, True])
def test_about_shows_version_and_no_network(fallback):
    root = Path(__file__).resolve().parents[1]
    code = """
import socket
import sys
from unittest.mock import patch

import wx

from hpc_gui import __version__
from hpc_gui import wx_about
from hpc_gui.core.i18n import load_language

load_language("en")
app = wx.App(False)
opened = []
local = []
fallback = sys.argv[1] == "True"

def deny_network(*args, **kwargs):
    raise AssertionError("About dialog attempted a network connection")

with patch.object(socket, "create_connection", deny_network), \\
     patch.object(socket.socket, "connect", deny_network), \\
     patch.object(wx_about.webbrowser, "open", side_effect=lambda url: opened.append(url)), \\
     patch.object(wx, "LaunchDefaultApplication", side_effect=lambda path: local.append(path) or not fallback):
    dialog = wx_about._create_about_dialog()
    try:
        controls = dialog._wx_about_controls
        assert __version__ in controls["version"].GetLabel()
        for key in ("repo", "license", "notices", "close"):
            assert controls[key].GetLabel()
        assert not opened and not local

        def click(key):
            button = controls[key]
            event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
            event.SetEventObject(button)
            button.GetEventHandler().ProcessEvent(event)

        click("repo")
        assert opened == ["https://github.com/mskomek/hpc-client-gui"]
        click("license")
        click("notices")
        assert len(local) == 2
        assert local[0].endswith("LICENSE")
        assert local[1].endswith("THIRD_PARTY_NOTICES.md")
        if fallback:
            assert opened[1:] == [
                "https://github.com/mskomek/hpc-client-gui/blob/main/LICENSE",
                "https://github.com/mskomek/hpc-client-gui/blob/main/THIRD_PARTY_NOTICES.md",
            ]
        else:
            assert len(opened) == 1
    finally:
        dialog.Destroy()
        app.ProcessPendingEvents()

assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
print("about-dialog-behavior=PASS", flush=True)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(fallback)], cwd=root,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(
            [str(root / "src"), os.environ.get("PYTHONPATH", "")]
        )}, capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "about-dialog-behavior=PASS" in result.stdout
