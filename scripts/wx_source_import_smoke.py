"""Source-import smoke for wx modules (NOT packaged evidence).

This script imports wx modules from `src/` to verify source-level importability.
It does NOT prove a packaged artifact launches without `src` on sys.path.
For real packaged evidence see `scripts/wx_packaged_smoke.py` which requires
a built artifact and isolates `src`.
"""

from __future__ import annotations

import importlib
import json
import platform
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


STAGES = {
    "launch": ("hpc_gui.wx_shell",),
    "terminal": ("hpc_gui.wx_terminal",),
    "files": ("hpc_gui.wx_local_files", "hpc_gui.wx_remote_files"),
    "editor": ("hpc_gui.wx_editor",),
    "plugin_ansys": ("hpc_gui.wx_plugins", "hpc_gui.wx_ansys"),
    "diagnostics_updater": ("hpc_gui.core.diagnostics", "hpc_gui.services.app_updater"),
}


def run_smoke() -> dict[str, object]:
    results = {}
    for stage, modules in STAGES.items():
        try:
            for module in modules:
                importlib.import_module(module)
            results[stage] = "PASS"
        except Exception as exc:
            results[stage] = f"FAIL: {type(exc).__name__}: {exc}"
    return {
        "schema": "wx-source-import-smoke/1",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "stages": results,
        "note": "source import only; not packaged artifact evidence",
        "manual_required": ["display", "cluster", "MFA", "X11", "DnD", "transfer-conflict"],
    }


def main() -> int:
    report = run_smoke()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(value == "PASS" for value in report["stages"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
