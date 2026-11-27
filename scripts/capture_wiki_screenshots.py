"""Capture the six wiki screenshots from the real wx shell and offline demo.

Run with --verify-flow for the native workflow without writing images.
Historical Qt audit PNGs are retained separately; this script never loads Qt.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from unittest.mock import patch

from create_demo_gif import ROOT, _capture, _pump, _run_demo

ASSET_DIR = ROOT / "docs" / "wiki" / "assets"
SCENES = {
    "connected": "overview", "selected": "file-manager",
    "edited": "script-editor", "jobs": "jobs",
}
EXPECTED = {"overview", "file-manager", "script-editor", "jobs", "settings", "send-logs"}


def capture_wiki(*, verify_only=False):
    with tempfile.TemporaryDirectory(prefix="hpc-wx-wiki-") as temporary:
        root = Path(temporary)
        workspace = root / "local"
        workspace.mkdir()
        staging = root / "images"
        staging.mkdir()
        log = root / "app.log"
        log.write_text("INFO  mock session connected\nINFO  upload verified\n", encoding="utf-8")
        seen = set()

        def capture(wx, app, window, name):
            if name in seen:
                raise RuntimeError(f"duplicate wiki capture: {name}")
            if not verify_only:
                _capture(wx, app, window, staging / f"{name}.png")
            seen.add(name)

        def emit(wx, app, window, scene):
            if scene not in SCENES:
                return
            capture(wx, app, window, SCENES[scene])
            if scene != "connected":
                return
            from hpc_gui.wx_settings_view import show_settings
            from hpc_gui.wx_send_logs_view import show_send_logs

            show_settings(window)
            settings = next(w for w in wx.GetTopLevelWindows()
                            if hasattr(w, "_wx_settings_controls"))
            try:
                capture(wx, app, settings, "settings")
            finally:
                settings.Close()
                app.ProcessPendingEvents()

            show_send_logs(window, log_path=log)
            logs = next(w for w in wx.GetTopLevelWindows()
                        if hasattr(w, "_wx_send_logs_controls"))
            try:
                _pump(wx, app, lambda: "upload verified" in
                      logs._wx_send_logs_controls["log_view"].GetValue(), "wiki logs")
                capture(wx, app, logs, "send-logs")
            finally:
                logs.Close()
                app.ProcessPendingEvents()

        def deny(*args, **kwargs):
            raise AssertionError("wiki capture attempted a real network connection")

        with patch.dict(os.environ, {"HPC_GUI_CONFIG_ROOT": str(root / "config"),
                                    "HPC_GUI_LANGUAGE": "en"}):
            with patch.object(socket, "create_connection", deny), patch.object(socket.socket, "connect", deny):
                _run_demo(workspace, emit)
        if seen != EXPECTED:
            raise RuntimeError(f"incomplete wiki capture: {sorted(EXPECTED - seen)}")
        if not verify_only:
            ASSET_DIR.mkdir(parents=True, exist_ok=True)
            for name in sorted(seen):
                shutil.copyfile(staging / f"{name}.png", ASSET_DIR / f"{name}.png")
        print("wx-wiki-flow=PASS " + ",".join(sorted(seen)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(capture_wiki(verify_only="--verify-flow" in sys.argv[1:]))
