"""Independent native wx WebView2 baseline for a Windows CI GUI runner.

Diagnostic ONLY: a standalone browser pass never satisfies packaged W55.
No application import, no remote access, no persisted profile data.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
from pathlib import Path


def run(mode: str, output: Path, timeout: int) -> int:
    state = {
        "mode": mode,
        "result": "FAIL",
        "created": False,
        "loaded": False,
        "frame_visible": False,
        "error": "",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="w55-webview2-baseline-",
                                         ignore_cleanup_errors=True) as temporary:
            # The one-step default case also gets an isolated user-data path.
            profile = Path(temporary) / "edge-profile"
            profile.mkdir()
            os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(profile)
            import wx
            import wx.html2

            state["wx"] = wx.version()
            state["edge_available"] = bool(
                wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge)
            )
            app = wx.App(False)
            frame = wx.Frame(None, title="WebView2 CI baseline", size=(600, 400))
            frame.Show()
            state["frame_visible"] = bool(frame.IsShownOnScreen())
            controller = None
            done = False

            def finish(reason: str = "") -> None:
                nonlocal done
                if done:
                    return
                done = True
                state["error"] = reason
                state["result"] = "PASS" if state["created"] and state["loaded"] else "FAIL"
                try:
                    frame.Destroy()
                finally:
                    wx.CallAfter(app.ExitMainLoop)

            def on_created(event) -> None:
                state["created"] = True
                try:
                    controller.LoadURL("about:blank")
                except Exception as exc:
                    finish(f"navigation: {type(exc).__name__}")
                event.Skip()

            def on_loaded(event) -> None:
                state["loaded"] = True
                finish()
                event.Skip()

            def on_error(event) -> None:
                detail = event.GetString() if hasattr(event, "GetString") else ""
                finish(f"webview: {detail}")
                event.Skip()

            def create() -> None:
                nonlocal controller
                try:
                    if mode == "configured":
                        config = wx.html2.WebView.NewConfiguration()
                        config.SetDataPath(str(profile))
                        controller = wx.html2.WebView.New(config)
                    else:
                        controller = wx.html2.WebView.New(frame)
                    controller.Bind(wx.html2.EVT_WEBVIEW_CREATED, on_created)
                    controller.Bind(wx.html2.EVT_WEBVIEW_LOADED, on_loaded)
                    controller.Bind(wx.html2.EVT_WEBVIEW_ERROR, on_error)
                    if mode == "configured" and controller.Create(frame) is False:
                        finish("Create returned False")
                except Exception as exc:
                    finish(f"creation: {type(exc).__name__}: {exc}")

            wx.CallAfter(create)
            wx.CallLater(timeout * 1000, lambda: finish("native creation timeout"))
            app.MainLoop()
    except BaseException as exc:
        state["error"] = f"{type(exc).__name__}: {exc}"
    output.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("WEBVIEW2_BASELINE=" + json.dumps(state, ensure_ascii=False), flush=True)
    return 0 if state["result"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("default", "configured"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()
    return run(args.mode, args.output, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
