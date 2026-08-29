"""Capture the English product demo from the real application window.

All cluster operations use the application's built-in mock session. The script
never connects to SSH or uses saved user profiles.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo" / "hpc-client-gui-demo.gif"
FRAME_DIR = ROOT / "build" / "demo-frames"
sys.path.insert(0, str(ROOT / "src"))


def _font(size: int):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _caption(
    source: Path,
    title: str,
    subtitle: str,
) -> Image.Image:
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
        ("outputs", "Outputs", "Live stdout and stderr for job 12347"),
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


def _configure_demo_environment() -> tuple[Path, dict]:
    home = Path(tempfile.gettempdir()) / "hpc-client-gui-demo" / "researcher"
    shutil.rmtree(home.parent, ignore_errors=True)
    home.mkdir(parents=True)
    for variable in ("HOME", "USERPROFILE", "HOMEPATH"):
        os.environ[variable] = str(home)
    os.environ["HOMEDRIVE"] = home.drive or ""
    os.environ["TRUBA_GUI_FTP_TEST_MODE"] = "1"
    os.environ["HPC_GUI_LANGUAGE"] = "en"
    # The real terminal widget is not part of this demo flow.  Disable its
    # QtWebEngine helper in Windows/headless capture environments; the real
    # MainWindow then uses its built-in console fallback.
    os.environ["HPC_GUI_DISABLE_WEBENGINE"] = "1"
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    (home / ".truba_slurm_gui").mkdir()
    profile = {
        "name": "Test Cluster",
        "host": "mock",
        "port": 22,
        "username": "researcher",
        "key_path": "",
        "host_key_policy": "accept-new",
        "system": {"home_dir": "/arf/home", "scratch_dir": "/arf/scratch"},
    }
    return home, profile


def _real_window(app, profile):
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui import main_window
    from hpc_gui.ui.widgets import login_widget

    load_language("en")
    login_widget.load_profiles = lambda: [dict(profile)]
    window = main_window.MainWindow()
    window._startup_changelog_timer.stop()
    window._startup_update_timer.stop()
    window.resize(1280, 720)
    window.show()
    app.processEvents()
    return window


def _capture(widget, name: str) -> Path:
    path = FRAME_DIR / f"{name}.png"
    widget.grab().save(str(path))
    return path


def _wait(app, milliseconds: int) -> None:
    from PySide6.QtTest import QTest

    QTest.qWait(milliseconds)
    app.processEvents()


def _find_item(tree, text: str):
    for index in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(index)
        if item.text(0) == text:
            return item
    raise RuntimeError(f"real widget item not found: {text}")


def _select_local_items(ftp, names: tuple[str, ...]) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    tree = ftp.local_panel.tree
    tree.clearSelection()
    for index, name in enumerate(names):
        item = _find_item(tree, name)
        point = tree.visualItemRect(item).center()
        modifiers = Qt.KeyboardModifier.NoModifier if index == 0 else Qt.KeyboardModifier.ControlModifier
        QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, modifiers, point)


def _capture_popup(window, name: str) -> Path | None:
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QApplication, QMenu

    popup = next((w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()), None)
    if popup is None:
        return None
    pixmap = window.grab()
    painter = QPainter(pixmap)
    top_left = popup.mapTo(window, popup.rect().topLeft())
    painter.drawPixmap(top_left, popup.grab())
    painter.end()
    path = FRAME_DIR / f"{name}.png"
    pixmap.save(str(path))
    return path


def _click_popup_action(window, fragment: str) -> None:
    from PySide6.QtCore import QTimer
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMenu

    popup = next((w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()), None)
    if popup is None:
        QTimer.singleShot(50, lambda: _click_popup_action(window, fragment))
        return
    action = next((a for a in popup.actions() if fragment.lower() in a.text().lower()), None)
    if action is None:
        raise RuntimeError(f"real context menu action not found: {fragment}")
    QTest.mouseClick(popup, Qt.MouseButton.LeftButton, pos=popup.actionGeometry(action).center())


def _build_demo_session(window, workspace: Path):
    from hpc_gui.services.files_mock import MockFilesBackend
    from hpc_gui.services.slurm_mock import MockSlurmBackend
    from hpc_gui.ui.widgets import remote_dir_panel

    class DemoFiles(MockFilesBackend):
        supports_parallel_transfers = False
        # Keep the demo backend deterministic: the production transfer path
        # falls back to direct mock uploads when a backend has no rename API.
        rename = None

        def upload(self, local_path: str, remote_path: str) -> None:
            time.sleep(0.18)
            super().upload(local_path, remote_path)

    files = DemoFiles()
    slurm = MockSlurmBackend()
    session = dict(window.login._session)
    session.update({"connected": True, "files": files, "slurm": slurm, "profile_name": "Test Cluster"})
    remote_dir_panel.set_upload_preflight_confirmation_enabled(False)
    remote_dir_panel.get_upload_preflight_confirmation_enabled = lambda: False
    window.on_session_changed(session)
    window.ftp.local_panel.set_dir(str(workspace))
    return session, files


def _make_local_workspace() -> Path:
    workspace = Path(tempfile.gettempdir()) / "hpc-client-gui-demo" / "local"
    shutil.rmtree(workspace, ignore_errors=True)
    (workspace / "case").mkdir(parents=True)
    (workspace / "mesh").mkdir()
    (workspace / "run.slurm").write_text(
        "#!/bin/bash\n#SBATCH --job-name=demo_case\n#SBATCH --output=logs/%x_%j.out\n#SBATCH --error=logs/%x_%j.err\n#SBATCH --time=00:05:00\n\npython solve.py\n",
        encoding="utf-8",
    )
    return workspace


def validate_connection() -> int:
    """Open the real app and capture the three required connection frames."""
    home, profile = _configure_demo_environment()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui.splash_screen import StartupSplash

    app = QApplication.instance() or QApplication([])
    load_language("en")
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    splash = StartupSplash()
    splash.set_status("Preparing demo workspace")
    splash.show()
    app.processEvents()
    splash.grab().save(str(FRAME_DIR / "validation-splash.png"))
    window = _real_window(app, profile)
    splash.finish(window)
    login = window.login
    _capture(window, "validation-profile")
    item = login.profiles_list.item(0)
    if item is None or item.text() != "Test Cluster":
        raise RuntimeError("real profile screen did not contain Test Cluster")
    point = login.profiles_list.visualItemRect(item).center()
    QTest.mouseClick(login.profiles_list.viewport(), Qt.MouseButton.LeftButton, pos=point)
    app.processEvents()
    QTest.mouseMove(login.profiles_list.viewport(), point)
    QTest.mouseDClick(login.profiles_list.viewport(), Qt.MouseButton.LeftButton, pos=point, delay=120)
    app.processEvents()
    QTest.qWait(250)
    _capture(window, "validation-connected")
    if not login._session.get("connected"):
        raise RuntimeError("real double-click did not produce a connected mock session")
    print(f"created real connection validation frames in {FRAME_DIR}")
    window.close()
    app.processEvents()
    shutil.rmtree(home.parent, ignore_errors=True)
    return 0


def _full_capture() -> int:
    print("capture: setup", flush=True)
    home, profile = _configure_demo_environment()
    workspace = _make_local_workspace()
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui.splash_screen import StartupSplash

    app = QApplication.instance() or QApplication([])
    load_language("en")
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    splash = StartupSplash()
    splash.set_status("Preparing demo workspace")
    splash.show()
    app.processEvents()
    print("capture: splash", flush=True)
    paths = [(splash.grab(), "splash", "HPC Client GUI", "Starting the offline demo workspace", None)]
    window = _real_window(app, profile)
    splash.finish(window)
    login = window.login
    item = login.profiles_list.item(0)
    point = login.profiles_list.visualItemRect(item).center()
    QTest.mouseClick(login.profiles_list.viewport(), Qt.MouseButton.LeftButton, pos=point)
    app.processEvents()
    paths.append((window.grab(), "profile", "Connection", "Select Test Cluster", point))
    QTest.mouseMove(login.profiles_list.viewport(), point)
    QTest.mouseDClick(login.profiles_list.viewport(), Qt.MouseButton.LeftButton, pos=point, delay=120)
    _wait(app, 250)
    if not login._session.get("connected"):
        raise RuntimeError("real double-click did not connect the mock session")
    paths.append((window.grab(), "connected", "Connection", "Connected with the application's mock backend", point))
    print("capture: connected", flush=True)
    session, files = _build_demo_session(window, workspace)
    print("capture: session injected", flush=True)
    print("capture: ftp remote", window.ftp.active_remote_panel().current_dir, flush=True)

    ftp_index = window.tabs.indexOf(window.ftp)
    QTest.mouseClick(window.tabs.tabBar(), Qt.MouseButton.LeftButton, pos=window.tabs.tabBar().tabRect(ftp_index).center())
    _wait(app, 350)
    print("capture: files", flush=True)
    _select_local_items(window.ftp, ("case", "mesh", "run.slurm"))
    print("capture: selected", flush=True)
    print("capture: selected paths", window.ftp.local_panel.selected_paths(), flush=True)
    paths.append((window.grab(), "selected", "Files", "Select case/, mesh/, and run.slurm", window.ftp.local_panel.tree.visualItemRect(_find_item(window.ftp.local_panel.tree, "run.slurm")).center()))
    print("capture: click upload", flush=True)
    QTest.mouseClick(window.ftp.btn_upload, Qt.MouseButton.LeftButton)
    print("capture: upload clicked", flush=True)
    _wait(app, 180)
    paths.append((window.grab(), "uploading", "Files", "Upload selected items", window.ftp.btn_upload.mapTo(window, window.ftp.btn_upload.rect().center())))
    for _ in range(60):
        if files.exists("/arf/scratch/run.slurm"):
            break
        _wait(app, 500)
    else:
        raise RuntimeError("real upload did not finish run.slurm within 30 seconds")
    panel_debug = window.ftp.active_remote_panel()
    for _ in range(60):
        if not panel_debug._transfer_dialogs:
            break
        _wait(app, 500)
    paths.append((window.grab(), "uploaded", "Files", "Transfer completed in the real transfer area", window.ftp.btn_upload.mapTo(window, window.ftp.btn_upload.rect().center())))
    print("capture: backend", files.listdir("/arf/scratch"), flush=True)
    print("capture: transfer counts", window.ftp.transfer_activity.completed_list.topLevelItemCount(), window.ftp.transfer_activity.failed_list.topLevelItemCount(), flush=True)
    panel_debug = window.ftp.active_remote_panel()
    print("capture: transfer state", len(panel_debug._planning_jobs), len(panel_debug._transfer_dialogs), flush=True)
    print("capture: upload", flush=True)

    dirs_index = window.tabs.indexOf(window.directories)
    QTest.mouseClick(window.tabs.tabBar(), Qt.MouseButton.LeftButton, pos=window.tabs.tabBar().tabRect(dirs_index).center())
    _wait(app, 2000)
    print("capture: directories", flush=True)
    view = window.directories.panel_scratch.views["all"]
    window.directories.panel_scratch.set_dir(window.directories.panel_scratch.current_dir)
    _wait(app, 1000)
    print("capture: remote", window.directories.panel_scratch.current_dir, [view.topLevelItem(i).text(0) for i in range(view.topLevelItemCount())], flush=True)
    run_item = _find_item(view, "run.slurm")
    run_point = view.visualItemRect(run_item).center()
    from PySide6.QtWidgets import QMenu

    original_menu_exec = QMenu.exec

    def demo_menu_exec(menu, position):
        menu.popup(position)
        app.processEvents()
        path = _capture_popup(window, "context-menu")
        if path is not None:
            from PySide6.QtGui import QPixmap

            paths.append((QPixmap(str(path)), "context-menu", "Directories", "Choose Edit from the real context menu", run_point))
        action = next((candidate for candidate in menu.actions() if "edit" in candidate.text().lower()), None)
        if action is None:
            raise RuntimeError("real context menu Edit action not found")
        # The menu itself is a real QMenu created by the application. On
        # Windows, synthetic native-popup mouse events can hang when no
        # desktop compositor is available; trigger the real QAction after the
        # visible menu capture so the connected editor slot still runs.
        action.trigger()
        app.processEvents()
        menu.close()
        return action

    QMenu.exec = demo_menu_exec
    original_menu_exec_legacy = getattr(QMenu, "exec_", None)
    if original_menu_exec_legacy is not None:
        QMenu.exec_ = demo_menu_exec
    try:
        context_event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, run_point)
        QApplication.sendEvent(view.viewport(), context_event)
    finally:
        QMenu.exec = original_menu_exec
        if original_menu_exec_legacy is not None:
            QMenu.exec_ = original_menu_exec_legacy
    _wait(app, 600)
    _wait(app, 500)
    print("capture: editor", flush=True)

    editor = window.editor
    editor_widget = getattr(editor, "editor", None) or getattr(editor, "text", None)
    if editor_widget is None:
        raise RuntimeError("real editor text widget not found")
    _wait(app, 500)
    editor_widget.setFocus()
    QTest.keyClick(editor_widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    updated = "#!/bin/bash\n#SBATCH --job-name=demo_case_v2\n#SBATCH --output=logs/%x_%j.out\n#SBATCH --error=logs/%x_%j.err\n#SBATCH --time=00:05:00\n\npython solve.py\n"
    QApplication.clipboard().setText(updated)
    QTest.keyClick(editor_widget, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    _wait(app, 150)
    paths.append((window.grab(), "edited", "Edit Slurm job", "Change demo_case to demo_case_v2", editor_widget.mapTo(window, editor_widget.rect().center())))
    submit_button = editor.btn_save_submit

    def accept_submit_dialog() -> None:
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QMessageBox):
            paths.append((window.grab(), "submit-confirmation", "Submit job", "Confirm Save + Submit", dialog.mapTo(window, dialog.rect().center())))
            button = next((b for b in dialog.buttons() if "submit" in b.text().lower() or "yes" in b.text().lower()), None)
            if button is not None:
                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                return
        QTimer.singleShot(100, accept_submit_dialog)

    QTimer.singleShot(300, accept_submit_dialog)
    QTest.mouseClick(submit_button, Qt.MouseButton.LeftButton)
    _wait(app, 1600)
    print("capture: submitted", flush=True)
    job_id = "12347"
    out = "/arf/scratch/logs/demo_case_v2_12347.out"
    err = "/arf/scratch/logs/demo_case_v2_12347.err"
    files.write_text(out, "[1/3] Loading case/\n[2/3] Solving on 1 node\n[3/3] Complete\nexit code: 0\n")
    files.write_text(err, "")
    jobs_index = window.tabs.indexOf(window.jobs_outputs)
    QTest.mouseClick(window.tabs.tabBar(), Qt.MouseButton.LeftButton, pos=window.tabs.tabBar().tabRect(jobs_index).center())
    window.on_script_submitted(job_id, "/arf/scratch/run.slurm")
    _wait(app, 900)
    paths.append((window.grab(), "jobs", "Jobs / Outputs", "Job 12347 is visible in the real job panel", window.jobs_outputs.meta_job_id.mapTo(window, window.jobs_outputs.meta_job_id.rect().center())))
    window.jobs_outputs.section_tabs.setCurrentWidget(window.jobs_outputs.outputs_tab)
    _wait(app, 900)
    paths.append((window.grab(), "outputs", "Outputs", "Live stdout and stderr for job 12347", window.jobs_outputs.out_box.mapTo(window, window.jobs_outputs.out_box.rect().center())))
    print("capture: outputs", flush=True)

    frames = []
    for pixmap, name, title, subtitle, point in paths:
        raw = FRAME_DIR / f"real-{name}.png"
        pixmap.save(str(raw))
        frames.append(_caption(raw, title, subtitle))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    durations = [4000, 4000, 4000, 4000, 4500, 4500, 4500, 4500, 4500, 4500, 4500]
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"created {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KiB, {sum(durations) / 1000:.1f} seconds)")
    window.close()
    app.processEvents()
    shutil.rmtree(home.parent, ignore_errors=True)
    return 0


def main() -> int:
    if "--assemble" in sys.argv[1:]:
        return _assemble_existing()
    if "--check-connection" in sys.argv[1:]:
        return validate_connection()
    return _full_capture()


if __name__ == "__main__":
    raise SystemExit(main())
