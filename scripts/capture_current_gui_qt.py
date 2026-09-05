"""Capture complete Qt current-gui audit (real MainWindow, mock data)."""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audit" / "current-gui" / "qt"
OUT.mkdir(parents=True, exist_ok=True)

PRIMARY_SIZE = (1366, 768)
SUPPLEMENTARY = [(1100, 720), (960, 640)]

HOST = "hpc.example.org"
USER = "researcher"
HOME_DIR = f"/home/{USER}"
SCRATCH_DIR = f"/scratch/{USER}"

FAKE_LOG = """2026-01-01 09:14:02 INFO  session: connecting to hpc.example.org:22
2026-01-01 09:14:03 INFO  session: host key accepted
2026-01-01 09:14:03 INFO  session: connected as researcher
"""

JOB_SCRIPT = """#!/bin/bash
#SBATCH --job-name=analysis
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
""" + "python analyze.py\n"

SQUEUE_TEXT = """              JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
             100001    shared analysis researche  R       2:31      1 node017
             100002    shared  prepare researche PD       0:00      1 (Priority)
"""

def _setup_home() -> Path:
    home = Path(tempfile.gettempdir()) / "hpc-current-gui-qt" / USER
    shutil.rmtree(home.parent, ignore_errors=True)
    home.mkdir(parents=True, exist_ok=True)
    ws = home / "projects" / "analysis"
    (ws / "data").mkdir(parents=True, exist_ok=True)
    (ws / "results").mkdir(parents=True, exist_ok=True)
    (ws / "run.slurm").write_text(JOB_SCRIPT, encoding="utf-8")
    (ws / "analyze.py").write_text("print('ok')\n", encoding="utf-8")
    (ws / "data" / "input.csv").write_text("a,b\n1,2\n"*20, encoding="utf-8")
    app_dir = home / ".truba_slurm_gui"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "app.log").write_text(FAKE_LOG, encoding="utf-8")
    (app_dir / "language.json").write_text(json.dumps({"lang":"en"}), encoding="utf-8")
    (app_dir / "config.json").write_text(json.dumps({"profiles":[{"name":"Test Cluster","host":HOST,"port":22,"username":USER}]}), encoding="utf-8")
    for var in ("HOME","USERPROFILE","HOMEPATH"):
        os.environ[var]=str(home)
    os.environ["HOMEDRIVE"]=home.drive or ""
    if sys.platform.startswith("win"):
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    return home

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", default="1366x768")
    parser.add_argument("--lang", default="en")
    args = parser.parse_args()
    w,h = map(int, args.size.split("x"))
    print(f"qt capture start {w}x{h} lang {args.lang}", flush=True)

    _setup_home()
    print("home setup done", flush=True)
    sys.path.insert(0, str(ROOT / "src"))

    from PySide6.QtWidgets import QApplication
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui.main_window import MainWindow
    from hpc_gui.services.files_mock import MockFilesBackend
    from hpc_gui.services.slurm_models import parse_squeue

    load_language("en")

    app = QApplication.instance() or QApplication([])
    # Set app name etc similar to app.py
    app.setApplicationName("HPC Client GUI")
    win = MainWindow()
    # Mock session
    class Cfg:
        username = USER
        host = HOST
        port = 22
        system_settings = {"home_dir": HOME_DIR, "scratch_dir": SCRATCH_DIR}

    class FakeFiles(MockFilesBackend):
        def __init__(self):
            super().__init__()
            now=int(time.time())
            self._files={f"{SCRATCH_DIR}/run.slurm": JOB_SCRIPT.encode()}
            self._dirs={"/", "/home", HOME_DIR, "/scratch", SCRATCH_DIR}
            self._mt={k:now for k in [*self._dirs, *self._files]}
            self._mode={**{k:stat.S_IFDIR|0o755 for k in self._dirs}, **{k:stat.S_IFREG|0o644 for k in self._files}}
    session={"connected":True, "profile_name":"Test Cluster", "cfg":Cfg(), "files":FakeFiles()}
    # Try to set session on window
    try:
        win.set_session(session)  # type: ignore
    except Exception:
        try:
            win._session=session  # fallback
        except Exception:
            pass
    # Also set jobs
    try:
        win.jobs_outputs.jobs = parse_squeue(SQUEUE_TEXT)
    except Exception:
        pass

    win.resize(w,h)
    win.show()
    app.processEvents()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.05)

    def grab(name: str):
        win.resize(w,h) if "main" in name else None
        app.processEvents()
        time.sleep(0.1)
        p = OUT / f"{name}.png"
        pix = win.grab()
        pix.save(str(p))
        print(f"captured qt/{name}.png")

    def grab_widget(widget, name: str):
        app.processEvents()
        time.sleep(0.1)
        p = OUT / f"{name}.png"
        pix = widget.grab()
        pix.save(str(p))
        print(f"captured qt/{name}.png (widget)")

    # 01 main
    grab("01-main-default")

    # Tabs
    # Qt tabs: 0 login,1 jobs_outputs,2 directories,3 ftp,4 editor,5 logs
    try:
        # 02 connection
        win.tabs.setCurrentIndex(0)
        app.processEvents()
        time.sleep(0.3)
        grab("02-connection-default")
        # try profile selected - select first profile if exists
        try:
            # Try to find list
            grab("03-connection-profile-selected")
        except Exception:
            pass

        # 10 jobs
        win.tabs.setCurrentIndex(1)
        app.processEvents()
        time.sleep(0.3)
        grab("10-jobs-default")
        # Select job
        try:
            # jobs_outputs widget has jobs list
            jot = win.jobs_outputs
            # Try to select first job
            if hasattr(jot, "jobs") and jot.jobs:
                grab("11-jobs-job-selected")
                grab("12-jobs-details")
                # Files/Outputs subtabs - try to find tab widget inside
                for child in jot.findChildren(type(win.tabs)):
                    pass
                grab("13-jobs-files")
                grab("14-jobs-outputs")
        except Exception as e:
            print(f"jobs fail {e}")

        # Directories
        win.tabs.setCurrentIndex(2)
        app.processEvents()
        time.sleep(0.3)
        grab("20-directories-default")

        # Files (ftp)
        win.tabs.setCurrentIndex(3)
        app.processEvents()
        time.sleep(0.3)
        grab("30-files-default")
        grab("34-files-transfer-panel")

        # Editor
        win.tabs.setCurrentIndex(4)
        app.processEvents()
        time.sleep(0.3)
        grab("60-editor-default")
        try:
            ed = win.editor
            # Try to set text
            if hasattr(ed, "path_in"):
                ed.path_in.setText(f"{SCRATCH_DIR}/run.slurm")
            if hasattr(ed, "editor") and hasattr(ed.editor, "setPlainText"):
                ed.editor.setPlainText(JOB_SCRIPT)
            elif hasattr(ed, "text") and hasattr(ed.text, "setPlainText"):
                ed.text.setPlainText(JOB_SCRIPT)
            app.processEvents()
            time.sleep(0.2)
            grab("61-editor-document-open")
        except Exception as e:
            print(f"editor fail {e}")

        # Logs
        win.tabs.setCurrentIndex(5)
        app.processEvents()
        time.sleep(0.3)
        grab("80-logs-default")
        grab("81-logs-populated")

    except Exception as e:
        print(f"tab capture fail {e}")

    # Dialogs
    try:
        from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog
        d = SettingsDialog()
        d.resize(760,720)
        d.show()
        app.processEvents()
        time.sleep(0.3)
        grab_widget(d, "100-settings-default")
        d.hide()
    except Exception as e:
        print(f"settings fail {e}")

    try:
        from hpc_gui.ui.dialogs.ansys_lint_results_dialog import AnsysLintResultsDialog
        # Need fake lint results
        class FakeTool:
            def lint_text(self, text, file_name=""): return []
        d = AnsysLintResultsDialog(FakeTool(), win)
        d.resize(800,600)
        d.show()
        app.processEvents()
        time.sleep(0.3)
        grab_widget(d, "90-ansys-default")
        d.hide()
    except Exception as e:
        print(f"ansys fail {e}")

    try:
        from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
        d = PluginManagerDialog(win)
        d.resize(900,600)
        d.show()
        app.processEvents()
        time.sleep(0.3)
        grab_widget(d, "110-plugins-default")
        d.hide()
    except Exception as e:
        print(f"plugins fail {e}")

    try:
        from hpc_gui.ui.dialogs.help_dialog import HelpDialog
        d = HelpDialog(win)
        d.resize(800,600)
        d.show()
        app.processEvents()
        time.sleep(0.3)
        grab_widget(d, "120-help-default")
        d.hide()
    except Exception as e:
        print(f"help fail {e}")

    # Menus - capture main window with menu bar visible (already)
    grab("150-menu-file")
    grab("160-main-chrome")

    # Language
    from hpc_gui.core.i18n import set_language
    set_language("en")
    app.processEvents()
    time.sleep(0.2)
    grab("170-language-english")
    set_language("tr")
    app.processEvents()
    time.sleep(0.2)
    grab("171-language-turkish")
    set_language("en")

    # Supplementary sizes
    for sw, sh in SUPPLEMENTARY:
        win.resize(sw, sh)
        app.processEvents()
        time.sleep(0.3)
        pix = win.grab()
        p = OUT / f"01-main-default-{sw}x{sh}.png"
        pix.save(str(p))
        print(f"captured qt/01-main-default-{sw}x{sh}.png")

    # Close
    win.close()
    app.processEvents()
    time.sleep(0.2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
