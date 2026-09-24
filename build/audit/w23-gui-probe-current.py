import tempfile
from pathlib import Path

import wx

from hpc_gui.wx_local_files import LocalBrowserModel, _build_local_files

app = wx.App(False)
tmp = Path(tempfile.mkdtemp(prefix="w23gui-"))
(tmp / "f.txt").write_bytes(b"y" * 10)
m = LocalBrowserModel(tmp)
ents = m.list_entries()
print("W23_GUI_ENTRIES=", len(ents))
print("W23_GUI_MTIME=", any(getattr(e, "mtime", 0) > 0 for e in ents))
frame = wx.Frame(None, title="w23probe")
host = _build_local_files(frame, path=str(tmp), embedded=True)
ctrls = host._wx_local_controls
print("W23_GUI_KEYS=", sorted(ctrls.keys()))
print("W23_GUI_FORWARD_KEY=", "btn_forward" in ctrls)
frame.Destroy()
app.Destroy()
print("W23_GUI_PROBE=PASS")
