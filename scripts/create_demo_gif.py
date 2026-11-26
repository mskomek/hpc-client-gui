"""Capture the real wx application with isolated, offline demo backends.

--check-connection captures the first three scenes; --verify-flow runs all
operations without screen capture; --assemble rebuilds from existing frames.
A visible desktop is required for image capture, never for a remote server.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from threading import Event
from unittest.mock import patch
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo" / "hpc-client-gui-demo.gif"
FRAME_DIR = ROOT / "build" / "demo-frames"
sys.path.insert(0, str(ROOT / "src"))


def _font(size: int):
    from PIL import ImageFont

    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _caption(
    source: Path,
    title: str,
    subtitle: str,
):
    from PIL import Image, ImageDraw

    image = Image.open(source).convert("RGB")
    image.thumbnail((1280, 650), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1280, 720), "#0b1220")
    x = (canvas.width - image.width) // 2
    y = 70 + (650 - image.height) // 2
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1280, 62), fill="#12233c")
    draw.text((28, 10), title, fill="#ffffff", font=_font(25))
    draw.text((28, 38), subtitle, fill="#9edff0", font=_font(15))
    return canvas


def _assemble_existing() -> int:
    """Rebuild the GIF from the last successful real-app capture."""
    scenes = (
        ("splash", "HPC Client GUI", "Starting the offline demo workspace"),
        ("profile", "Connection", "Select Test Cluster"),
        ("connected", "Connection", "Connected with the application's mock backend"),
        ("selected", "Files", "Select case/, mesh/, and run.slurm"),
        ("uploading", "Files", "Upload selected items"),
        ("uploaded", "Files", "Transfer completed in the real transfer area"),
        ("edited", "Edit Slurm job", "Change demo_case to demo_case_v2"),
        ("jobs", "Jobs / Outputs", "Job 12347 is visible in the real job panel"),
        ("outputs", "Outputs", "Mock stdout and stderr for job 12347"),
    )
    frames = []
    for name, title, subtitle in scenes:
        source = FRAME_DIR / f"real-{name}.png"
        if not source.exists():
            raise RuntimeError(f"missing real capture frame: {source}")
        frames.append(_caption(source, title, subtitle))
    durations = [4000, 4000, 5000, 4500, 4500, 4500, 4500, 4500, 4500]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"created {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KiB, {sum(durations) / 1000:.1f} seconds)")
    return 0



SCENES = ("splash", "profile", "connected", "selected", "uploading",
          "uploaded", "edited", "jobs", "outputs")
WORKDIR = "/arf/scratch/user"
SCRIPT = "#!/bin/bash\n#SBATCH --job-name=demo_case\n#SBATCH --output=demo.out\n#SBATCH --error=demo.err\n#SBATCH --time=00:05:00\n\necho solve\n"


def _click(wx, button):
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)


def _pump(wx, app, predicate, label, timeout=10):
    if predicate():
        return
    loop = wx.GUIEventLoop()
    deadline = time.monotonic() + timeout
    timer = None

    def poll():
        nonlocal timer
        if predicate():
            loop.Exit(0)
        elif time.monotonic() >= deadline:
            loop.Exit(1)
        else:
            timer = wx.CallLater(25, poll)

    with wx.EventLoopActivator(loop):
        timer = wx.CallLater(25, poll)
        code = loop.Run()
    if timer is not None:
        timer.Stop()
    if code != 0 or not predicate():
        raise RuntimeError(f"demo timed out: {label}")


def _capture(wx, app, window, destination):
    window.Raise()
    window.Update()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    rect = window.GetScreenRect()
    if not window.IsShownOnScreen() or min(rect.width, rect.height) <= 0:
        raise RuntimeError("demo capture requires a visible window on a desktop")
    bitmap = wx.Bitmap(rect.width, rect.height)
    target = wx.MemoryDC(bitmap)
    try:
        if not target.Blit(0, 0, rect.width, rect.height, wx.ScreenDC(), rect.x, rect.y):
            raise RuntimeError("native screen capture failed")
    finally:
        target.SelectObject(wx.NullBitmap)
    if not bitmap.SaveFile(str(destination), wx.BITMAP_TYPE_PNG):
        raise RuntimeError(f"cannot save capture: {destination}")


def _make_backends(release, entered):
    from hpc_gui.services.files_mock import MockFilesBackend
    from hpc_gui.services.slurm_mock import MockSlurmBackend

    class DemoFiles(MockFilesBackend):
        supports_parallel_transfers = False

        def upload(self, local_path, remote_path, progress_cb=None):
            entered.set()
            if not release.wait(15):
                raise TimeoutError("demo upload was not released")
            super().upload(local_path, remote_path)
            if progress_cb is not None:
                size = Path(local_path).stat().st_size
                progress_cb(size, size)

    files = DemoFiles()

    class DemoSlurm(MockSlurmBackend):
        submitted = False

        def sbatch(self, script_path):
            if files.read_text(script_path) != SCRIPT.replace("demo_case", "demo_case_v2"):
                raise RuntimeError("demo job was not saved before submission")
            self.submitted = True
            files.write_text(WORKDIR + "/demo.out", "[1/3] Loading case/\n[2/3] Solving\n[3/3] Complete\n")
            files.write_text(WORKDIR + "/demo.err", "No errors\n")
            return super().sbatch(script_path)

        def squeue(self, user):
            rows = super().squeue(user)
            if self.submitted:
                rows += f"12347 short demo_case_v2 {user} R 0:01 1 node001\n"
            return rows

        def scontrol_show_job(self, job_id):
            if str(job_id) == "12347":
                return (f"JobId=12347 JobName=demo_case_v2 JobState=RUNNING Partition=short "
                        f"WorkDir={WORKDIR} Command={WORKDIR}/run.slurm "
                        f"StdOut={WORKDIR}/demo.out StdErr={WORKDIR}/demo.err")
            return super().scontrol_show_job(job_id)

        def active_job_ids(self, user):
            return super().active_job_ids(user) + ("12347\n" if self.submitted else "")

        def job_state(self, job_id):
            return "RUNNING\n" if str(job_id) == "12347" else super().job_state(job_id)

    return files, DemoSlurm()


def _select_rows(listing, names):
    found = set()
    for index in range(listing.GetItemCount()):
        name = listing.GetItemText(index)
        listing.Select(index, name in names)
        if name in names:
            found.add(name)
    if found != set(names):
        raise RuntimeError(f"demo file rows missing: {set(names) - found}")


def _run_demo(workspace, emit, *, connection_only=False):
    """Drive real wx controls. Only SSH/Slurm/files and terminal navigation are mocked."""
    import wx
    from hpc_gui.config.storage import upsert_profile
    from hpc_gui.core.i18n import load_language
    from hpc_gui.wx_splash import create_startup_splash
    from hpc_gui.wx_shell_frame import create_shell_frame
    from hpc_gui.wx_shell_files import _editor_session_key

    load_language("en")
    app = wx.App(False)
    app.SetExitOnFrameDelete(False)
    profile = {"name": "Test Cluster", "host": "mock.invalid", "port": 22,
               "username": "user", "system": {"home_dir": "/arf/home/user", "scratch_dir": WORKDIR},
               "file_manager": {"local_start_dir": str(workspace)}, "save_password": False}
    upsert_profile(profile)
    for name in ("case", "mesh"):
        (workspace / name).mkdir()
        (workspace / name / "input.txt").write_text(name, encoding="utf-8")
    (workspace / "run.slurm").write_text(SCRIPT, encoding="utf-8")
    release, entered = Event(), Event()
    files, slurm = _make_backends(release, entered)
    splash = create_startup_splash(pure_splash=True)
    splash._wx_splash_set_status("Preparing offline demo workspace")
    splash.Show()
    emit(wx, app, splash, "splash")
    splash.Destroy()
    frame, lifecycle, state = create_shell_frame(app, tray_factory=lambda _frame: None,
                                                 defer_terminal_webview=True)
    frame.Show()
    app.SetTopWindow(frame)
    shell = frame._wx_shell_controls
    book, pages = shell["notebook"], shell["pages"]

    def select(key):
        index = book.FindPage(pages[key]["page"])
        if index < 0:
            raise RuntimeError(f"missing demo page: {key}")
        book.SetSelection(index)
        app.ProcessPendingEvents()

    try:
        panel = pages["APP-CONNECT"]["page"]
        controls = panel._wx_connection_controls
        choices = controls["choices"]
        if choices.FindString("Test Cluster") < 0:
            raise RuntimeError("isolated demo profile not visible")
        choices.SetStringSelection("Test Cluster")
        event = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        event.SetEventObject(choices)
        event.SetInt(choices.GetSelection())
        choices.GetEventHandler().ProcessEvent(event)
        panel._wx_connection_model._connect = lambda p: {
            "connected": True, "profile": p, "profile_name": p["name"],
            "files": files, "slurm": slurm, "ssh": None,
        }
        emit(wx, app, frame, "profile")
        # Terminal isn't a demo scene. Avoid opening a native browser or
        # contacting a transport while leaving the real connection path intact.
        with patch("hpc_gui.wx_shell_events._select_embedded_page", return_value=True):
            _click(wx, controls["connect"])
            _pump(wx, app, lambda: state.get("connection_status") == "connected"
                  and (state.get("session") or {}).get("files") is files, "mock connection")
        select("APP-CONNECT")
        emit(wx, app, frame, "connected")
        if connection_only:
            return

        select("NAV-FILES")
        local = pages["NAV-FILES"]["local"]
        remote = pages["NAV-FILES"]["remote"]
        remote._wx_remote_controls["navigate"](WORKDIR)
        remote._wx_remote_controls["load"]()
        listing = local._wx_local_controls["listing"]
        _pump(wx, app, lambda: {"case", "mesh", "run.slurm"}.issubset(
            {listing.GetItemText(i) for i in range(listing.GetItemCount())}), "profile local start directory")
        assert local._wx_local_model.current_path == workspace.resolve()
        assert local._wx_local_tabs[local._wx_local_notebook.GetSelection()]["path"] == workspace.resolve()
        _select_rows(listing, ("case", "mesh", "run.slurm"))
        emit(wx, app, frame, "selected")
        _click(wx, pages["NAV-FILES"]["upload_selected"])
        transfers = pages["NAV-FILES"]["transfers"]
        _pump(wx, app, lambda: entered.is_set() and bool(transfers._wx_transfer_state["queue_map"]),
              "upload queue")
        emit(wx, app, frame, "uploading")
        release.set()
        _pump(wx, app, lambda: all(files.exists(WORKDIR + "/" + item)
              for item in ("case/input.txt", "mesh/input.txt", "run.slurm"))
              and not state.get("transfer_sessions"), "upload completion")
        if transfers._wx_transfer_state["failed_map"]:
            raise RuntimeError("demo transfer failed")
        emit(wx, app, frame, "uploaded")

        # Use the actual remote Edit action; it creates the real editor window.
        remote._wx_remote_controls["load"]()
        remote_listing = remote._wx_remote_controls["listing"]
        _pump(wx, app, lambda: any(remote_listing.GetItemText(i) == "run.slurm"
                                   for i in range(remote_listing.GetItemCount())), "remote listing")
        remote._wx_remote_run_action("edit", [WORKDIR + "/run.slurm"], WORKDIR)
        manager = state["editor_manager"]
        _pump(wx, app, lambda: manager.primary_frame is not None, "remote editor")
        editor = manager.primary_frame
        editor_controls = editor._wx_editor_controls
        editor_controls["editor"].SetValue(SCRIPT.replace("demo_case", "demo_case_v2"))
        emit(wx, app, editor, "edited")
        _click(wx, editor_controls["submit"])
        _pump(wx, app, lambda: slurm.submitted and not editor._wx_editor_state["in_flight"],
              "save and submit")
        assert files.read_text(WORKDIR + "/run.slurm") == SCRIPT.replace("demo_case", "demo_case_v2")
        assert _editor_session_key(state)
        editor.Close()
        select("NAV-JOBS")
        jobs = pages["NAV-JOBS"]["page"]
        job_controls = jobs._wx_jobs_controls
        jobs._wx_jobs_refresh_jobs()
        table = job_controls["jobs"]

        def job_index():
            return next((i for i in range(table.GetItemCount()) if table.GetItemText(i) == "12347"), -1)

        _pump(wx, app, lambda: job_index() >= 0, "submitted job row")
        table.Select(job_index())
        event = wx.ListEvent(wx.EVT_LIST_ITEM_SELECTED.typeId, table.GetId())
        event.SetIndex(job_index())
        event.SetEventObject(table)
        table.GetEventHandler().ProcessEvent(event)
        emit(wx, app, frame, "jobs")
        job_controls["notebook"].SetSelection(4)
        jobs._wx_jobs_refresh_outputs()
        _pump(wx, app, lambda: "Complete" in " ".join(
            control.GetValue() for control in job_controls["output_channels"].values()),
            "live mock stdout")
        emit(wx, app, frame, "outputs")
    finally:
        release.set()
        frame.Close()
        loop = wx.GUIEventLoop()
        with wx.EventLoopActivator(loop):
            # Close callbacks are owned by the production shell.
            app.ProcessPendingEvents()
            loop.ProcessIdle()
            app.ProcessPendingEvents()
        store = state.pop("_job_record_store", None)
        if store is not None:
            store.close()
        del lifecycle


def _capture_run(*, connection_only=False, verify_only=False):
    """Never modify HOME or real saved profiles. Publish captures only after success."""
    with tempfile.TemporaryDirectory(prefix="hpc-wx-demo-") as temporary:
        root = Path(temporary)
        workspace = root / "local"
        workspace.mkdir()
        staging = root / "captures"
        staging.mkdir()
        seen = []

        def emit(wx, app, window, name):
            seen.append(name)
            if not verify_only:
                _capture(wx, app, window, staging / (name + ".png"))

        with patch.dict(os.environ, {"HPC_GUI_CONFIG_ROOT": str(root / "config"),
                                    "HPC_GUI_LANGUAGE": "en"}):
            import socket
            def deny(*args, **kwargs):
                raise AssertionError("demo attempted a real network connection")
            with patch.object(socket, "create_connection", deny), patch.object(socket.socket, "connect", deny):
                _run_demo(workspace, emit, connection_only=connection_only)
        expected = SCENES[:3] if connection_only else SCENES
        if tuple(seen) != expected:
            raise RuntimeError(f"demo scenes incomplete: {seen}")
        if not verify_only:
            FRAME_DIR.mkdir(parents=True, exist_ok=True)
            prefix = "validation-" if connection_only else "real-"
            for name in seen:
                shutil.copyfile(staging / (name + ".png"), FRAME_DIR / (prefix + name + ".png"))
        print("wx-demo-flow=PASS " + ",".join(seen), flush=True)
    return 0 if connection_only or verify_only else _assemble_existing()


def validate_connection() -> int:
    return _capture_run(connection_only=True)


def main() -> int:
    if "--assemble" in sys.argv[1:]:
        return _assemble_existing()
    if "--check-connection" in sys.argv[1:]:
        return validate_connection()
    return _capture_run(verify_only="--verify-flow" in sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
