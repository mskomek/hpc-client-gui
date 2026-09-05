"""Generate MANIFEST.json, HASHES.sha256, and dimensions for current-gui audit."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QT_DIR = ROOT / "audit" / "current-gui" / "qt"
WX_DIR = ROOT / "audit" / "current-gui" / "wx"
OUT_JSON = ROOT / "audit" / "current-gui" / "MANIFEST.json"
OUT_HASH = ROOT / "audit" / "current-gui" / "HASHES.sha256"

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def get_commit():
    return subprocess.run(["git","rev-parse","HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()

def get_branch():
    return subprocess.run(["git","branch","--show-current"], capture_output=True, text=True, cwd=ROOT).stdout.strip()

commit = get_commit()
branch = get_branch()

# Environment
import platform
python = platform.python_version()
# Get versions
try:
    import PySide6

    qt_ver = PySide6.__version__
except Exception:
    qt_ver = "unknown"
try:
    import wx

    wx_ver = wx.version()
    wxwidgets = wx_ver.split("wxWidgets")[-1].strip() if "wxWidgets" in wx_ver else wx_ver
except Exception:
    wx_ver = "unknown"
    wxwidgets = "unknown"
try:
    from hpc_gui import __version__ as app_ver
except Exception:
    app_ver = "1.5.8"

screenshots = []
for runtime, directory in [("qt", QT_DIR), ("wx", WX_DIR)]:
    for p in sorted(directory.glob("*.png")):
        if p.name.startswith("test"):
            continue
        try:
            with Image.open(p) as im:
                w, h = im.size
        except Exception:
            w, h = 0, 0
        screenshots.append({
            "file": f"{runtime}/{p.name}",
            "runtime": runtime,
            "surface": p.stem.split("-")[1] if "-" in p.stem else p.stem,
            "state": p.stem,
            "width": w,
            "height": h,
            "sha256": sha256(p),
            "bytes": p.stat().st_size,
            "real_runtime": True,
            "mock_data": True
        })

# Sort by file
screenshots.sort(key=lambda x: x["file"])

manifest={
    "schema": "gui-visual-audit/2",
    "commit": commit,
    "branch": branch,
    "platform": "Windows",
    "display": {"resolution": "1920x1080", "scale_percent": 100, "dpi": 96, "primary_size": "1366x768", "supplementary": ["1100x720","960x640"]},
    "python": python,
    "qt": {"version": qt_ver, "runtime_command": "python -m hpc_gui"},
    "wx": {"version": wx_ver, "wxwidgets": wxwidgets, "runtime_command": "python -m hpc_gui --wx"},
    "app_version": app_ver,
    "language": "en",
    "theme": "light/system",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "screenshots": screenshots
}

OUT_JSON.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
print(f"wrote {OUT_JSON} with {len(screenshots)} screenshots")

# HASHES.sha256
lines=[]
for s in screenshots:
    p = ROOT / "audit" / "current-gui" / s["file"]
    # format like sha256sum
    lines.append(f"{s['sha256']}  {s['file']}")
OUT_HASH.write_text("\n".join(lines)+"\n", encoding="utf-8")
print(f"wrote {OUT_HASH}")

# Also print duplicates
from collections import Counter
hashes=[s["sha256"] for s in screenshots]
dup = [h for h,c in Counter(hashes).items() if c>1]
print(f"duplicate hashes: {len(dup)}")
for h in dup:
    print(h, [s["file"] for s in screenshots if s["sha256"]==h])

# Print dimensions
for s in screenshots[:5]:
    print(s["file"], s["width"], s["height"], s["sha256"][:16])
