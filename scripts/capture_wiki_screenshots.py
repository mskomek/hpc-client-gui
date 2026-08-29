"""Capture the wiki feature screenshots from an offline, fabricated session.

Run it whenever the interface changes so `docs/wiki/assets/` stays current:

    python scripts/capture_wiki_screenshots.py

Nothing here touches a real cluster or the real application directory: HOME is
redirected to a throwaway directory before `hpc_gui` is imported, so every
profile, log line, path, and job id in the images is fabricated.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "docs" / "wiki" / "assets"

# Fabricated identities. Nothing below refers to a real host, account, or job.
HOST = "hpc.example.org"
USER = "researcher"
HOME_DIR = f"/home/{USER}"
SCRATCH_DIR = f"/scratch/{USER}"

FAKE_LOG = """\
2026-01-01 09:14:02 INFO  session: connecting to hpc.example.org:22
2026-01-01 09:14:03 INFO  session: host key accepted from known_hosts
2026-01-01 09:14:03 INFO  session: connected as researcher
2026-01-01 09:14:04 INFO  files: transport initialised (sftp)
2026-01-01 09:14:11 INFO  files: listdir /scratch/researcher (4 entries)
2026-01-01 09:15:20 INFO  transfer: upload inputs/run.slurm -> /scratch/researcher/run.slurm
2026-01-01 09:15:21 INFO  transfer: sha-256 verified, 1 file, 412 bytes
2026-01-01 09:15:44 INFO  jobs: sbatch /scratch/researcher/run.slurm
2026-01-01 09:15:45 INFO  jobs: submitted, job id 100001
2026-01-01 09:18:02 WARN  jobs: squeue returned a banner line, parsing degraded
2026-01-01 09:18:02 INFO  jobs: 2 jobs parsed for researcher
"""

JOB_SCRIPT = """\
#!/bin/bash
#SBATCH --job-name=analysis
#SBATCH --partition=<partition>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

module purge
# module load python/3.14

python analyze.py --input data/input.csv --output results/
"""

SQUEUE_TEXT = """\
             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
            100001    shared analysis researche  R       2:31      1 node017
            100002    shared  prepare researche PD       0:00      1 (Priority)
"""


def _fake_home() -> Path:
    """Redirect HOME before hpc_gui is imported; several modules read it at import time.

    Deliberately not under the system temp directory: on Windows that path
    embeds the real account name, and the file manager renders its local path
    verbatim into the screenshot.
    """
    root = Path(tempfile.gettempdir()).drive or REPO_ROOT.drive or ""
    home = Path(f"{root}/wiki-capture/{USER}")
    shutil.rmtree(home.parent, ignore_errors=True)
    home.mkdir(parents=True)

    # A plausible local workspace, so the local panel shows real-looking work
    # instead of the application's own dot-directory.
    workspace = home / "projects" / "analysis"
    (workspace / "data").mkdir(parents=True)
    (workspace / "results").mkdir(parents=True)
    (workspace / "run.slurm").write_text(JOB_SCRIPT, encoding="utf-8")
    (workspace / "analyze.py").write_text("import sys\nprint('ok')\n", encoding="utf-8")
    (workspace / "data" / "input.csv").write_text("a,b,c\n" + "1,2,3\n" * 40, encoding="utf-8")
    (workspace / "results" / "summary.csv").write_text("metric,value\nrmse,0.031\n", encoding="utf-8")

    for var in ("HOME", "USERPROFILE", "HOMEPATH"):
        os.environ[var] = str(home)
    os.environ["HOMEDRIVE"] = home.drive or ""
    # The offscreen platform resolves no system font database here and renders
    # every glyph as a box, so capture on the native platform by default.
    # Override with QT_QPA_PLATFORM if a headless run is ever needed.
    if sys.platform.startswith("win"):
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    app_dir = home / ".truba_slurm_gui"
    app_dir.mkdir(parents=True)
    (app_dir / "app.log").write_text(FAKE_LOG, encoding="utf-8")
    (app_dir / "language.json").write_text(json.dumps({"lang": "en"}), encoding="utf-8")
    (app_dir / "config.json").write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "name": "example-cluster",
                        "host": HOST,
                        "port": 22,
                        "username": USER,
                        "key_path": "",
                        "host_key_policy": "accept-new",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return home


HOME = _fake_home()
LOCAL_WORKSPACE = HOME / "projects" / "analysis"

sys.path.insert(0, str(REPO_ROOT / "src"))

from PySide6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget  # noqa: E402

from hpc_gui.core.i18n import load_language  # noqa: E402
from hpc_gui.services.files_mock import MockFilesBackend  # noqa: E402
from hpc_gui.services.slurm_models import parse_squeue  # noqa: E402


class NeutralFilesBackend(MockFilesBackend):
    """The bundled mock ships site-specific paths; this one is anonymous."""

    def __init__(self) -> None:
        super().__init__()
        now = int(time.time())
        self._files = {
            f"{SCRATCH_DIR}/run.slurm": JOB_SCRIPT.encode("utf-8"),
            f"{SCRATCH_DIR}/analyze.py": b"import sys\nprint('ok')\n",
            f"{SCRATCH_DIR}/data/input.csv": b"a,b,c\n1,2,3\n" * 40,
            f"{SCRATCH_DIR}/results/summary.csv": b"metric,value\nrmse,0.031\n",
            f"{SCRATCH_DIR}/logs/analysis_100001.out": b"step 1/3 complete\nstep 2/3 complete\n",
            f"{SCRATCH_DIR}/logs/analysis_100001.err": b"",
            f"{HOME_DIR}/notes.md": b"# Notes\n",
        }
        self._dirs = {
            "/",
            "/home",
            HOME_DIR,
            "/scratch",
            SCRATCH_DIR,
            f"{SCRATCH_DIR}/data",
            f"{SCRATCH_DIR}/results",
            f"{SCRATCH_DIR}/logs",
        }
        self._mt = {k: now for k in [*self._dirs, *self._files]}
        self._mode = {
            **{k: stat.S_IFDIR | 0o755 for k in self._dirs},
            **{k: stat.S_IFREG | 0o644 for k in self._files},
        }


class _Cfg:
    username = USER
    host = HOST
    port = 22
    system_settings = {"home_dir": HOME_DIR, "scratch_dir": SCRATCH_DIR}


def _session() -> dict:
    return {
        "connected": True,
        "profile_name": "example-cluster",
        "cfg": _Cfg(),
        "files": NeutralFilesBackend(),
    }


def _save(widget, name: str, size: tuple[int, int]) -> Path:
    widget.resize(*size)
    widget.show()
    QApplication.processEvents()
    for _ in range(3):
        QApplication.processEvents()
    path = ASSET_DIR / f"{name}.png"
    widget.grab().save(str(path))
    widget.hide()
    return path


def _capture_file_manager(app) -> Path:
    from hpc_gui.ui.widgets.ftp_widget import FtpWidget

    w = FtpWidget()
    w.set_session(_session())
    w.local_panel.set_dir(str(LOCAL_WORKSPACE))
    QApplication.processEvents()
    return _save(w, "file-manager", (1100, 640))


def _capture_jobs(app) -> Path:
    from hpc_gui.ui.widgets.jobs_widget import JobsWidget

    w = JobsWidget()
    w.jobs = parse_squeue(SQUEUE_TEXT)
    w.out.setPlainText(SQUEUE_TEXT)
    return _save(w, "jobs", (900, 380))


def _capture_overview(app) -> Path:
    from hpc_gui.ui.widgets.ftp_widget import FtpWidget
    from hpc_gui.ui.widgets.jobs_widget import JobsWidget

    w = QWidget()
    layout = QVBoxLayout(w)
    layout.addWidget(QLabel("Connected: example-cluster  •  researcher@hpc.example.org"))
    columns = QHBoxLayout()
    files = FtpWidget()
    files.set_session(_session())
    files.local_panel.set_dir(str(LOCAL_WORKSPACE))
    jobs = JobsWidget()
    jobs.jobs = parse_squeue(SQUEUE_TEXT)
    jobs.out.setPlainText(SQUEUE_TEXT)
    columns.addWidget(files, 3)
    columns.addWidget(jobs, 2)
    layout.addLayout(columns)
    return _save(w, "overview", (1300, 760))


def _capture_editor(app) -> Path:
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    w = EditorWidget()
    w.path_in.setText(f"{SCRATCH_DIR}/run.slurm")
    editor = getattr(w, "editor", None) or getattr(w, "text", None)
    if editor is not None and hasattr(editor, "setPlainText"):
        editor.setPlainText(JOB_SCRIPT)
    return _save(w, "script-editor", (900, 620))


def _capture_settings(app) -> Path:
    from hpc_gui.ui.dialogs.settings_dialog import SettingsDialog

    d = SettingsDialog()
    d.setModal(False)
    return _save(d, "settings", (760, 720))


def _capture_send_logs(app) -> Path:
    from hpc_gui.ui.dialogs.send_logs_dialog import SendLogsDialog

    d = SendLogsDialog()
    d.setModal(False)
    return _save(d, "send-logs", (820, 560))


CAPTURES = {
    "overview": _capture_overview,
    "file-manager": _capture_file_manager,
    "jobs": _capture_jobs,
    "script-editor": _capture_editor,
    "settings": _capture_settings,
    "send-logs": _capture_send_logs,
}


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    load_language("en")
    app = QApplication.instance() or QApplication([])

    failures = 0
    try:
        for name, capture in CAPTURES.items():
            try:
                path = capture(app)
                size_kb = path.stat().st_size / 1024
                print(f"  OK   {path.relative_to(REPO_ROOT)}  ({size_kb:.0f} KiB)")
            except Exception as exc:  # keep going; one broken widget is not fatal
                failures += 1
                print(f"  FAIL {name}: {type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(HOME.parent, ignore_errors=True)

    print(f"\n{len(CAPTURES) - failures}/{len(CAPTURES)} screenshots captured")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
