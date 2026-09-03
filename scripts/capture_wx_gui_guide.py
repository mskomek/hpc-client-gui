"""Capture real wx migration surfaces with disposable mock HPC data.

Run from the repository root with ``python scripts/capture_wx_gui_guide.py``.
The script never connects to a cluster and never writes under ``.tmp``.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "wiki" / "assets" / "gui-guide"
sys.path.insert(0, str(ROOT / "src"))

import wx  # noqa: E402
from PIL import ImageGrab  # noqa: E402

from hpc_gui.core.i18n import load_language  # noqa: E402
from hpc_gui.wx_editor_view import show_editor  # noqa: E402
from hpc_gui.wx_help import show_help  # noqa: E402
from hpc_gui.wx_jobs import WxJobsModel, show_job_output, show_jobs  # noqa: E402
from hpc_gui.wx_local_files import show_local_files  # noqa: E402
from hpc_gui.wx_remote_files import RemoteEntry  # noqa: E402
from hpc_gui.wx_remote_files_view import show_remote_files  # noqa: E402
from hpc_gui.wx_connection import show_connection  # noqa: E402
from hpc_gui.wx_terminal import show_terminal  # noqa: E402


class MockSession:
    """Small provider-neutral session boundary used only for screenshots."""

    def __init__(self, local_root: Path) -> None:
        self.local_root = local_root
        self.jobs = (
            {"id": "100001", "state": "RUNNING", "name": "analysis", "stdout_path": "/scratch/demo/analysis.out", "stderr_path": "/scratch/demo/analysis.err"},
            {"id": "100002", "state": "PENDING", "name": "prepare", "stdout_path": "", "stderr_path": ""},
        )

    def iterdir_entries(self, _path: str):
        return (RemoteEntry("/scratch/demo/run.slurm", size=412), RemoteEntry("/scratch/demo/results", is_dir=True), RemoteEntry("/scratch/demo/analysis.out", size=128))

    def read_text(self, path: str) -> str:
        if path.endswith("analysis.out"):
            return "step 1/3 complete\nstep 2/3 complete\nstep 3/3 complete\n"
        return "#!/bin/bash\n#SBATCH --job-name=analysis\n"

    def list_jobs(self):
        return self.jobs

    def read_output(self, _job_id: str):
        return {"stdout": "step 1/3 complete\nstep 2/3 complete\n", "stderr": ""}


def _new_window(before):
    current = [window for window in wx.GetTopLevelWindows() if window and window not in before]
    if not current:
        raise RuntimeError("wx surface did not create a top-level window")
    return current[-1]


_APP = None


def _capture(frame: wx.Window, name: str, ready=None) -> None:
    frame.SetSize((1100, 720))
    frame.Show()
    frame.Raise()
    ctypes.windll.user32.SetForegroundWindow(frame.GetHandle())
    def capture_when_ready() -> None:
        if ready is not None and not ready():
            wx.CallLater(50, capture_when_ready)
            return
        frame.Update()
        image = ImageGrab.grab(window=frame.GetHandle())
        path = ASSETS / f"{name}.png"
        image.save(path)
        frame.Destroy()
        _APP.ExitMainLoop()
        print(path.relative_to(ROOT))

    wx.CallLater(250, capture_when_ready)
    _APP.MainLoop()


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="hpc-client-gui-guide-"))
    try:
        local_root = temp_root / "analysis"
        local_root.mkdir()
        (local_root / "run.slurm").write_text("#!/bin/bash\n#SBATCH --job-name=analysis\n#SBATCH --time=00:10:00\n", encoding="utf-8")
        (local_root / "analyze.py").write_text("print('mock result')\n", encoding="utf-8")
        (local_root / "results").mkdir()
        mock = MockSession(local_root)
        load_language("en")
        global _APP
        _APP = wx.App(False)

        before = list(wx.GetTopLevelWindows())
        show_connection(None, [{"name": "mock-cluster", "host": "127.0.0.1", "username": "demo"}])
        _capture(_new_window(before), "wx-connection")

        before = list(wx.GetTopLevelWindows())
        show_local_files(None, local_root)
        _capture(_new_window(before), "wx-local-files")

        before = list(wx.GetTopLevelWindows())
        show_remote_files(None, loader=mock.iterdir_entries, read_text=mock.read_text)
        _capture(_new_window(before), "wx-remote-files")

        editor = show_editor(None, path="/scratch/demo/run.slurm", content="#!/bin/bash\n#SBATCH --job-name=analysis\n", is_local=False)
        _capture(editor, "wx-editor")

        before = list(wx.GetTopLevelWindows())
        show_jobs(None, list_jobs=mock.list_jobs, read_output=mock.read_output)
        jobs_frame = _new_window(before)
        _capture(jobs_frame, "wx-jobs", lambda: bool(jobs_frame._wx_jobs_state["items"]))

        jobs = WxJobsModel()
        detached = jobs.open_detached("/scratch/demo/analysis.out", "/scratch/demo/analysis.err")
        before = list(wx.GetTopLevelWindows())
        show_job_output(None, jobs, detached.id, read_output=lambda: ("stdout", "stderr"), interval_ms=100000)
        _capture(_new_window(before), "wx-detached-output")

        before = list(wx.GetTopLevelWindows())
        show_help(None, topic_id="help.keyboard-shortcuts")
        _capture(_new_window(before), "wx-help-shortcuts")

        before = list(wx.GetTopLevelWindows())
        show_terminal(None, send_input=lambda _text: None)
        _capture(_new_window(before), "wx-terminal")
        _APP.Destroy()
        return 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
