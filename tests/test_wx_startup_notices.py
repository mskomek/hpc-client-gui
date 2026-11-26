"""Native and storage-backed startup notice parity tests."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from hpc_gui import __version__
from hpc_gui.config.storage import get_last_seen_changelog_version, get_ui_pref_bool
from hpc_gui.wx_startup_notices import show_startup_notices


class _Owner:
    def IsBeingDeleted(self):
        return False


@pytest.mark.unit
@pytest.mark.regression
def test_startup_notices_persist_version_and_welcome_choice(monkeypatch, tmp_path):
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path))
    calls = []

    def present(parent, title, text, *, allow_opt_out=False):
        assert text.strip()
        calls.append((title, allow_opt_out))
        return allow_opt_out

    owner = _Owner()
    show_startup_notices(owner, present=present)
    assert [opt for _, opt in calls] == [False, True]
    assert get_last_seen_changelog_version() == __version__
    assert not get_ui_pref_bool("show_welcome", True)
    show_startup_notices(owner, present=present)
    assert len(calls) == 2


@pytest.mark.unit
def test_failed_changelog_does_not_mark_version_seen(monkeypatch, tmp_path):
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path))
    calls = []

    def present(parent, title, text, *, allow_opt_out=False):
        calls.append(allow_opt_out)
        if not allow_opt_out:
            raise RuntimeError("synthetic display failure")
        return False

    show_startup_notices(_Owner(), present=present)
    assert calls == [False, True]
    assert get_last_seen_changelog_version() != __version__
    assert get_ui_pref_bool("show_welcome", True)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_startup_dialogs_are_read_only_and_opt_out_is_persisted(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
import wx
from hpc_gui import __version__
from hpc_gui.config.storage import get_last_seen_changelog_version, get_ui_pref_bool
from hpc_gui.wx_startup_notices import show_startup_notices

app = wx.App(False)
frame = wx.Frame(None)
frame.Show()
seen = []
def close_notice():
    for window in wx.GetTopLevelWindows():
        controls = getattr(window, '_wx_startup_notice_controls', None)
        if controls is None or not window.IsModal():
            continue
        assert not controls['content'].IsEditable()
        assert controls['content'].GetValue().strip()
        checkbox = controls['opt_out']
        seen.append(checkbox is not None)
        if checkbox is not None:
            checkbox.SetValue(True)
        window.EndModal(wx.ID_OK)
        if len(seen) < 2:
            wx.CallLater(50, close_notice)
        return
    wx.CallLater(50, close_notice)
wx.CallLater(50, close_notice)
show_startup_notices(frame)
assert seen == [False, True], seen
assert get_last_seen_changelog_version() == __version__
assert not get_ui_pref_bool('show_welcome', True)
show_startup_notices(frame)
assert seen == [False, True]
assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    env["HPC_GUI_CONFIG_ROOT"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
