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


def _caption(source: Path, title: str, subtitle: str) -> Image.Image:
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
        paths["plugin-manager"] = _plugin_manager(app)
        paths["ansys-lint"] = _ansys_lint(app)

        scenes = [
            ("overview", "Connection profile", "Connect to a saved HPC cluster profile"),
            ("file-manager", "Remote file manager", "Browse remote files and folders over SFTP"),
            ("file-manager", "Parallel transfer", "Move multiple files with progress and verification"),
            ("script-editor", "Submit a Slurm job", "Prepare and submit a reproducible batch script"),
            ("jobs", "Track jobs and output", "Follow queue state, accounting, and job output"),
            ("plugin-manager", "Plugin Manager", "Install declarative cluster and application tools"),
            ("ansys-lint", "ANSYS journal lint", "Review warnings before sending a Fluent journal"),
        ]
        frames = [_caption(paths[name], title, subtitle) for name, title, subtitle in scenes]
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            OUTPUT,
            save_all=True,
            append_images=frames[1:],
            duration=[7000] * len(frames),
            loop=0,
            optimize=True,
        )
        print(f"created {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KiB, 49 seconds)")
        return 0
    finally:
        shutil.rmtree(capture.HOME.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
