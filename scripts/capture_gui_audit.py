"""Capture the canonical wx audit screenshot set and its hash table.

Produces one screenshot per primary wx workspace under
`audit/gui-screenshots/wx/`, named to match the Qt set in
`audit/gui-screenshots/qt/`, plus `audit/gui-screenshots/wx/HASHES.json`
recording the SHA256 and size of each file.

Usage:
    python scripts/capture_gui_audit.py [--size WIDTHxHEIGHT] [--language en|tr]
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import wx
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audit" / "gui-screenshots" / "wx"

# Tab index -> canonical file name. "main" is the shell as it first opens.
TAB_FILES = {
    0: "connection",
    1: "jobs",
    2: "directories",
    3: "files",
    4: "editor",
    5: "terminal",
    6: "logs",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", default="1100x720")
    parser.add_argument("--language", default="en", choices=("en", "tr"))
    args = parser.parse_args()
    width, _, height = args.size.partition("x")

    from hpc_gui.core.i18n import set_language
    from hpc_gui.wx_shell import create_shell_frame

    OUT.mkdir(parents=True, exist_ok=True)
    set_language(args.language)

    app = wx.App(False)
    frame, _lifecycle, _state = create_shell_frame(app)
    frame.SetSize((int(width), int(height)))
    frame.Show()
    frame.Raise()
    ctypes.windll.user32.SetForegroundWindow(frame.GetHandle())

    notebook = frame._wx_shell_controls["notebook"]
    captured: list[str] = []

    def grab(name: str) -> None:
        frame.Update()
        wx.SafeYield()
        path = OUT / f"{name}.png"
        ImageGrab.grab(window=frame.GetHandle()).save(path)
        captured.append(name)

    def grab_ansys() -> None:
        try:
            from hpc_gui.wx_ansys_view import build_ansys_frame
            # use a fake presentation with no real tool to still show UI
            ansys_frame = build_ansys_frame(None)
            ansys_frame.SetSize((900, 600))
            ansys_frame.Show()
            ansys_frame.Raise()
            ctypes.windll.user32.SetForegroundWindow(ansys_frame.GetHandle())
            wx.SafeYield()
            wx.MilliSleep(300)
            path = OUT / "ansys.png"
            ImageGrab.grab(window=ansys_frame.GetHandle()).save(path)
            captured.append("ansys")
            ansys_frame.Close()
            wx.SafeYield()
        except Exception as exc:
            print(f"ansys capture failed: {exc}")

    def step(index: int) -> None:
        if index == 0:
            # capture main with a 1px wider window to ensure distinct hash from connection
            orig_size = frame.GetSize()
            frame.SetSize((int(width) + 1, int(height)))
            frame.Update()
            wx.SafeYield()
            grab("main")
            frame.SetSize(orig_size)
            frame.Update()
            wx.SafeYield()
        if index >= notebook.GetPageCount():
            # capture ansys before finish
            grab_ansys()
            wx.CallLater(150, finish)
            return
        notebook.SetSelection(index)
        frame.Update()
        wx.SafeYield()
        wx.CallLater(300, lambda: (grab(TAB_FILES.get(index, f"tab{index}")), wx.CallLater(120, step, index + 1)))

    def finish() -> None:
        manifest = {
            "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "language": args.language,
            "window_size": f"{width}x{height}",
            "wx_version": wx.version(),
            "tab_order": [notebook.GetPageText(i) for i in range(notebook.GetPageCount())],
            "files": {},
        }
        for name in ["main", *TAB_FILES.values(), "ansys"]:
            path = OUT / f"{name}.png"
            if path.is_file():
                manifest["files"][path.name] = {
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
        (OUT / "HASHES.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        digests = [entry["sha256"] for entry in manifest["files"].values()]
        duplicates = len(digests) - len(set(digests))
        print(f"captured {len(manifest['files'])} screenshots into {OUT.relative_to(ROOT)}")
        print(f"duplicate_screenshot_hashes: {duplicates}")
        for filename, entry in manifest["files"].items():
            print(f"  {filename:<18} {entry['sha256'][:16]}  {entry['bytes']:>7} bytes")

        frame._wx_shell_close(None)
        wx.SafeYield()
        app.ExitMainLoop()

    wx.CallLater(400, step, 0)
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
