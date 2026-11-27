from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.config import storage
from hpc_gui.wx_jobs import build_jobs_panel
from hpc_gui.wx_shell_files import _remote_files_callbacks


SCRIPT = "#SBATCH --job-name=demo\n#SBATCH --output=run-%j.out\n#SBATCH --error=run-%j.err\n"


def _pump(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        wx.Yield()
        if predicate():
            return
        wx.MilliSleep(10)
    wx.Yield()
    assert predicate()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.parametrize(
    "mode",
    [
        storage.SBATCH_FOLLOW_MODE_NONE,
        storage.SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
        storage.SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
        storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED,
        storage.SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT,
    ],
)
def test_wx_file_submission_registers_job_and_routes_output_followers(
    wx_app, monkeypatch, mode
):
    class Files:
        def read_text(self, path):
            assert path == "/work/demo.sbatch"
            return SCRIPT

    class Slurm:
        def sbatch(self, path):
            assert path == "/work/demo.sbatch"
            return "Submitted batch job 678"

    monkeypatch.setattr(storage, "get_sbatch_follow_mode", lambda: mode)
    frame = wx.Frame(None)
    shell = wx.Notebook(frame)
    shell.AddPage(wx.Panel(shell), "Files")
    files = Files()
    session_state = {
        "session": {
            "connected": True,
            "files": files,
            "slurm": Slurm(),
            "profile": {"id": "profile-a"},
        }
    }
    panel = build_jobs_panel(
        shell,
        list_jobs=lambda: [],
        session_state=session_state,
        profile_id="profile-a",
        cluster_id="cluster-a",
        provider_id="provider-a",
        remote_files_callbacks={"read_text": lambda path: f"tail {path}"},
    )
    shell.AddPage(panel, "Jobs & Outputs")
    session_state["_embedded_main_notebook"] = shell
    session_state["_embedded_jobs_panel"] = panel
    frame.Show()

    try:
        callbacks = _remote_files_callbacks(session_state, frame, None)
        result = callbacks["submit_slurm"]("/work/demo.sbatch")
        assert result == "Submitted batch job 678"
        _pump(lambda: panel._wx_jobs_model.selected_job_store.job_id == "678")

        context = panel._wx_jobs_model.selected_job_store.context
        assert panel._wx_jobs_state["selected_job"] == "678"
        assert context.script_path == "/work/demo.sbatch"
        assert context.script_text == SCRIPT
        assert context.profile_id == "profile-a"
        assert context.cluster_id == "cluster-a"
        assert context.provider_id == "provider-a"
        assert context.stdout_path == "/work/run-678.out"
        assert context.stderr_path == "/work/run-678.err"

        if mode == storage.SBATCH_FOLLOW_MODE_NONE:
            assert shell.GetSelection() == 0
            assert not panel._wx_jobs_state["resolved_channels"]
        elif mode in {
            storage.SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
            storage.SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
        }:
            assert shell.GetSelection() == 1
            controls = panel._wx_jobs_controls
            assert controls["notebook"].GetSelection() == 4
            paths = {control.GetValue() for control in controls["output_channel_paths"].values()}
            assert paths == {"/work/run-678.out", "/work/run-678.err"}
            _pump(lambda: all(control.GetValue().startswith("tail ") for control in controls["output_channels"].values()))
        elif mode == storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED:
            _pump(lambda: any(getattr(window, "_wx_output_followers", None) for window in wx.GetTopLevelWindows()))
            pair = next(window for window in wx.GetTopLevelWindows() if getattr(window, "_wx_output_followers", None))
            assert pair.GetTitle() == "Job 678 — Output and Error"
            assert [follower.state.path for follower in pair._wx_output_followers] == [
                "/work/run-678.out",
                "/work/run-678.err",
            ]
            labels = []
            pending = list(pair.GetChildren())
            while pending:
                child = pending.pop()
                pending.extend(child.GetChildren())
                if isinstance(child, wx.StaticText):
                    labels.append(child.GetLabel())
            assert any(label == "Output: /work/run-678.out" for label in labels)
            assert any(label == "Error: /work/run-678.err" for label in labels)
            _pump(lambda: all(control.GetValue().startswith("tail ") for control in pair._wx_output_controls))
        else:
            _pump(lambda: sum(bool(getattr(window, "_wx_output_controls", {}).get("follower")) for window in wx.GetTopLevelWindows()) == 2)
            paths = {
                window._wx_output_controls["follower"].state.path
                for window in wx.GetTopLevelWindows()
                if getattr(window, "_wx_output_controls", {}).get("follower")
            }
            assert paths == {"/work/run-678.out", "/work/run-678.err"}
            _pump(lambda: all(
                window._wx_output_controls["output"].GetValue().startswith("tail ")
                for window in wx.GetTopLevelWindows()
                if getattr(window, "_wx_output_controls", {}).get("follower")
            ))
    finally:
        frame.Close()
        for window in list(wx.GetTopLevelWindows()):
            if window is not frame and not window.IsBeingDeleted():
                window.Close()
        for _ in range(4):
            wx.Yield()
