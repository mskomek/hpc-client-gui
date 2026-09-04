import shlex
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_local_files import LocalEntry
from hpc_gui.wx_shell import _dispatch, create_shell_frame


class SSH:
    def __init__(self):
        self.commands = []

    def send_shell_text(self, text):
        self.commands.append(text)

    def send_shell_input(self, _text):
        pass

    def resize_shell_pty(self, _columns, _rows):
        pass


class Files:
    def write_text(self, _path, _content):
        pass


@pytest.fixture
def shell(tmp_path):
    load_language("en")
    app = wx.App(False)
    ssh = SSH()
    state = {"session": {"ssh": ssh, "files": Files()}, "generation": 0}
    frame, lifecycle, state = create_shell_frame(app, tray_factory=lambda _parent: None, session_state=state)
    yield app, frame, lifecycle, state, ssh, tmp_path
    lifecycle.shutdown()
    for window in list(wx.GetTopLevelWindows()):
        window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_file_view_shell_script_runs_in_real_terminal_path(shell):
    _app, shell_frame, lifecycle, state, ssh, tmp_path = shell
    script = tmp_path / "hello world.sh"
    script.write_text("echo hello", encoding="utf-8")

    _dispatch("NAV-FILES", shell_frame, lifecycle, state)
    browser = next(window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_run_action"))
    browser._wx_local_tabs[0]["entries"][:] = [LocalEntry(script, False, script.stat().st_size)]
    listing = browser._wx_local_controls["listing"]
    listing.InsertItem(0, script.name)
    listing.Select(0)
    browser._wx_local_run_action("run_shell")

    assert ssh.commands == [f"bash -- {shlex.quote(str(script))}\n"]


def test_editor_run_button_uses_real_wx_event_and_terminal_path(shell):
    _app, shell_frame, lifecycle, state, ssh, _tmp_path = shell
    _dispatch("NAV-EDITOR", shell_frame, lifecycle, state)
    editor = next(window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_editor_controls"))
    editor._wx_editor_load_document("/remote/job.slurm", "#!/bin/bash\necho job", is_local=False)

    event = wx.CommandEvent(wx.wxEVT_BUTTON, editor._wx_editor_controls["run"].GetId())
    editor._wx_editor_controls["run"].ProcessEvent(event)
    deadline = time.monotonic() + 3
    while not ssh.commands and time.monotonic() < deadline:
        _app.ProcessPendingEvents()
        wx.MilliSleep(10)

    assert ssh.commands == ["bash -- /remote/job.slurm\n"]
