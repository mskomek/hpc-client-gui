"""Build the short English-captioned product demo from offline mock data.

The frames are real HPC Client GUI widgets. Remote files and Slurm responses
come from the existing disposable mock backends; no network or credentials are
used. Run from the repository root on a machine with a desktop Qt session:

    python scripts/create_demo_gif.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo" / "hpc-client-gui-demo.gif"
FRAME_DIR = ROOT / "build" / "demo-frames"

sys.path.insert(0, str(ROOT / "scripts"))
import capture_wiki_screenshots as capture  # noqa: E402


def _font(size: int):
    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _save_widget(widget, name: str, size: tuple[int, int]) -> Path:
    from PySide6.QtWidgets import QApplication

    widget.resize(*size)
    widget.show()
    QApplication.processEvents()
    path = FRAME_DIR / f"{name}.png"
    widget.grab().save(str(path))
    widget.hide()
    return path


def _plugin_manager(app) -> Path:
    from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

    dialog = PluginManagerDialog(fetcher=lambda _url, _limit: b"{}")
    registry = json.loads((ROOT / ".." / "hpc-client-gui-plugins" / "registry.json").read_text(encoding="utf-8"))
    dialog._on_registry_loaded(registry, "offline mock")
    return _save_widget(dialog, "plugin-manager", (1000, 680))


def _ansys_lint(app) -> Path:
    from hpc_gui.ui.dialogs.ansys_lint_results_dialog import build_ansys_lint_results_dialog

    diagnostics = [
        SimpleNamespace(code="FLUENT001", severity=SimpleNamespace(value="warning"), message="Use an explicit initialization step.", line=12, column=1, suggested_fix="Add /solve/initialize/hyb-initialization.", source_url=""),
        SimpleNamespace(code="FLUENT003", severity=SimpleNamespace(value="error"), message="Journal contains an unsafe interactive command.", line=18, column=1, suggested_fix="Replace the interactive command with a batch-safe form.", source_url=""),
    ]
    file_result = SimpleNamespace(
        detection=SimpleNamespace(product="ANSYS Fluent", detected_version="2024 R2"),
        summary={"error": 1, "warning": 1, "info": 0},
        file_path="run.jou",
        diagnostics=diagnostics,
        sorted_diagnostics=lambda: diagnostics,
    )
    dialog = build_ansys_lint_results_dialog(
        None,
        "ANSYS Fluent journal lint",
        SimpleNamespace(files=[file_result]),
    )
    return _save_widget(dialog, "ansys-lint", (1000, 620))


def _splash() -> Path:
    from hpc_gui.ui.splash_screen import StartupSplash

    splash = StartupSplash()
    splash.set_status("Loading offline demo workspace")
    return _save_widget(splash, "splash", (480, 220))


def _caption(
    source: Path,
    title: str,
    subtitle: str,
    *,
    pointer: tuple[int, int] | None = None,
    pointer_label: str = "",
    panel: tuple[int, int, int, int] | None = None,
    panel_lines: tuple[str, ...] = (),
) -> Image.Image:
    image = Image.open(source).convert("RGB")
    image.thumbnail((1200, 620), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1280, 720), "#0b1220")
    x = (canvas.width - image.width) // 2
    y = 88 + (620 - image.height) // 2
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1280, 76), fill="#12233c")
    draw.text((40, 18), title, fill="#ffffff", font=_font(30))
    draw.text((40, 47), subtitle, fill="#9edff0", font=_font(16))
    if panel:
        draw.rounded_rectangle(panel, radius=8, fill="#ffffff", outline="#2563eb", width=3)
        px, py = panel[0] + 18, panel[1] + 14
        for line in panel_lines:
            draw.text((px, py), line, fill="#172033", font=_font(17))
            py += 27
    if pointer:
        x, y = pointer
        draw.line((x - 24, y - 30, x, y), fill="#ef4444", width=5)
        draw.polygon(((x, y), (x - 13, y - 4), (x - 5, y - 16)), fill="#ef4444")
        draw.ellipse((x - 20, y - 20, x + 20, y + 20), outline="#f59e0b", width=4)
        if pointer_label:
            draw.rounded_rectangle((x + 18, y - 22, x + 18 + len(pointer_label) * 9, y + 5), radius=5, fill="#f59e0b")
            draw.text((x + 26, y - 18), pointer_label, fill="#111827", font=_font(14))
    return canvas


def main() -> int:
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    capture.load_language("en")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    try:
        paths = {
            name: ROOT / "docs" / "wiki" / "assets" / f"{name}.png"
            for name in ("overview", "file-manager", "jobs", "script-editor")
        }
        paths["splash"] = _splash()
        paths["plugin-manager"] = _plugin_manager(app)
        paths["ansys-lint"] = _ansys_lint(app)

        scenes = [
            ("splash", "HPC Client GUI", "Starting the offline demo workspace", None, "", None, ()),
            ("overview", "Connection profile", "Double-click Test Cluster to connect", (454, 218), "Double-click", (610, 130, 1050, 250), ("Test Cluster", "Status: Connected", "researcher@hpc.example.org")),
            ("file-manager", "Files", "Select 2 folders and 1 file, then upload", (1000, 326), "Click Upload", (730, 430, 1235, 575), ("3 items queued", "data/     results/     run.slurm", "Transfer complete  •  verified")),
            ("file-manager", "Directories", "Right-click the Slurm job and choose Edit", (525, 255), "Right-click", (520, 260, 785, 398), ("Open", "Download", "Edit", "Delete")),
            ("script-editor", "Edit Slurm job", "Update resources, then Save and Submit", (810, 592), "Click Save and Submit", (590, 300, 1135, 640), ("Job name: analysis", "CPUs: 8   Memory: 16G", "[OK] Saved   [OK] Submitted as 100001")),
            ("jobs", "Jobs / Outputs", "Submitted job 100001 is visible and running", (640, 250), "Job 100001", (390, 275, 1210, 450), ("100001   analysis   RUNNING", "Partition: shared   Nodes: 1", "Elapsed: 00:02:31")),
            ("jobs", "Outputs", "Open the output tab to follow the run", (920, 335), "Open Outputs", (390, 275, 1210, 450), ("analysis_100001.out", "[1/3] Loading input.csv", "[2/3] Computing metrics", "[3/3] Complete  •  exit code 0")),
            ("plugin-manager", "Plugin Manager", "Extend the client with cluster tools", None, "", None, ()),
            ("ansys-lint", "ANSYS journal lint", "Review warnings before sending a Fluent journal", None, "", None, ()),
        ]
        frames = [
            _caption(paths[name], title, subtitle, pointer=pointer, pointer_label=label, panel=panel, panel_lines=lines)
            for name, title, subtitle, pointer, label, panel, lines in scenes
        ]
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            OUTPUT,
            save_all=True,
            append_images=frames[1:],
            duration=[4000, 6000, 6000, 6000, 6000, 6000, 6000, 4500, 4500],
            loop=0,
            optimize=True,
        )
        print(f"created {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KiB, 49 seconds)")
        return 0
    finally:
        shutil.rmtree(capture.HOME.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
