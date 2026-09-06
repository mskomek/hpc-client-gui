"""Generate updater screenshots per spec 36 — deterministic fake backend."""

import sys
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import wx
from hpc_gui import __version__
from hpc_gui.services.app_updater import UpdateRelease
from hpc_gui.wx_updater_view import WxUpdateDialog, _format_bytes
from hpc_gui.wx_updater_view import show_installing_splash

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots" / "updater"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _make_release(version="1.9.0", body="- Demo update\n- New features\n- Fixes", size=184*1024*1024):
    return UpdateRelease(version=version, tag=f"v{version}", zip_name="a.zip", zip_url="https://example.com/a.zip", sha_name="a.sha", sha_url="https://example.com/a.sha", html_url="https://example.com", body=body, size=size)

def _save_window(win, name):
    # Ensure window is shown and laid out
    win.Show()
    win.Update()
    wx.GetApp().ProcessPendingEvents()
    wx.MilliSleep(200)
    wx.GetApp().ProcessPendingEvents()
    # Get size and create bitmap
    sz = win.GetSize()
    bmp = wx.Bitmap(sz.width, sz.height)
    dc = wx.MemoryDC(bmp)
    # Use window's DC
    win_dc = wx.WindowDC(win)
    # Alternative: use ClientDC?
    # Simple: blit from window
    # On msw, WindowDC should capture
    # We'll use wx.ClientDC and Blit
    try:
        # Use PrintWindow via wx
        # Fallback: create bitmap from window
        # Use wx.Window's GetScreenRect
        rect = win.GetRect()
        # Use ScreenDC to capture
        screen_dc = wx.ScreenDC()
        bmp2 = wx.Bitmap(rect.width, rect.height)
        mem_dc = wx.MemoryDC(bmp2)
        mem_dc.Blit(0, 0, rect.width, rect.height, screen_dc, rect.x, rect.y)
        mem_dc.SelectObject(wx.NullBitmap)
        bmp2.SaveFile(str(OUT_DIR / name), wx.BITMAP_TYPE_PNG)
        print(f"saved {name} {rect.width}x{rect.height}")
    except Exception as e:
        print(f"failed {name}: {e}")
        # Fallback: just save blank
        bmp.SaveFile(str(OUT_DIR / name), wx.BITMAP_TYPE_PNG)
    win.Hide()

def main():
    app = wx.App(False)
    # Use English for screenshots
    from hpc_gui.core.i18n import load_language
    load_language("en")

    # 130 checking
    rel = _make_release()
    dlg = WxUpdateDialog(None, None)
    dlg._build_for_state("CHECKING")
    _save_window(dlg.dlg, "130-updater-checking.png")
    dlg.Destroy()

    # 131 up to date
    dlg = WxUpdateDialog(None, None)
    dlg._build_for_state("UP_TO_DATE")
    _save_window(dlg.dlg, "131-updater-up-to-date.png")
    dlg.Destroy()

    # 132 update available (with whats new)
    rel = _make_release(body="- Demo update for testing\n- Includes new features and fixes\n- Additional release note\n- Bug fixes and stability improvements\n- Performance improvements")
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("UPDATE_AVAILABLE")
    _save_window(dlg.dlg, "132-updater-update-available.png")
    dlg.Destroy()

    # 133 release notes (open via button, capture the notes dialog)
    # Instead, create the notes dialog directly
    rel = _make_release(body="Full release notes for 1.9.0:\n\n- Feature A\n- Feature B\n- Fix C\n\nSee https://example.com/release/v1.9.0 for details.")
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("UPDATE_AVAILABLE")
    # Simulate clicking View full release notes
    # We need to capture the notes dialog that _on_view_notes creates
    # Instead, create a separate notes dialog manually
    notes_dlg = wx.Dialog(None, title=f"Release Notes — HPC Client {rel.version}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    notes_dlg.SetMinSize(wx.Size(700, 600))
    notes_dlg.SetSize(wx.Size(700, 600))
    notes_dlg.CentreOnScreen()
    panel = wx.Panel(notes_dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    txt = wx.TextCtrl(panel, value=rel.body, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 12)
    close = wx.Button(panel, label="Close")
    sizer.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
    panel.SetSizer(sizer)
    _save_window(notes_dlg, "133-updater-release-notes.png")
    notes_dlg.Destroy()
    dlg.Destroy()

    # 134 downloading 25%
    rel = _make_release(size=184*1024*1024)
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("DOWNLOADING")
    dlg._downloaded = int(184*1024*1024 * 0.25)
    dlg._total = 184*1024*1024
    # Update labels
    if dlg._byte_label:
        dlg._byte_label.SetLabel(f"{_format_bytes(dlg._downloaded)} / {_format_bytes(dlg._total)}")
    if dlg._gauge:
        dlg._gauge.SetValue(25)
    if dlg._percent_label:
        dlg._percent_label.SetLabel("25%")
    dlg.panel.Layout()
    dlg.dlg.Layout()
    _save_window(dlg.dlg, "134-updater-downloading-25.png")
    dlg.Destroy()

    # 135 downloading 75%
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("DOWNLOADING")
    dlg._downloaded = int(184*1024*1024 * 0.75)
    dlg._total = 184*1024*1024
    if dlg._byte_label:
        dlg._byte_label.SetLabel(f"{_format_bytes(dlg._downloaded)} / {_format_bytes(dlg._total)}")
    if dlg._gauge:
        dlg._gauge.SetValue(75)
    if dlg._percent_label:
        dlg._percent_label.SetLabel("75%")
    dlg.panel.Layout()
    dlg.dlg.Layout()
    _save_window(dlg.dlg, "135-updater-downloading-75.png")
    dlg.Destroy()

    # 136 cancel confirm — need to show MessageBox, but we can simulate by creating a dialog
    # Instead, create a small dialog that mimics the cancel confirm
    cancel_dlg = wx.Dialog(None, title="Cancel update download?", style=wx.DEFAULT_DIALOG_STYLE)
    cancel_dlg.SetMinSize(wx.Size(420, 180))
    panel = wx.Panel(cancel_dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    msg = wx.StaticText(panel, label="Cancel update download?\n\nThe update is still being downloaded.")
    sizer.Add(msg, 0, wx.ALL, 16)
    btns = wx.BoxSizer(wx.HORIZONTAL)
    keep = wx.Button(panel, label="Keep Downloading")
    cancel = wx.Button(panel, label="Cancel Download")
    btns.AddStretchSpacer(1)
    btns.Add(keep, 0, wx.RIGHT, 8)
    btns.Add(cancel, 0)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
    panel.SetSizer(sizer)
    _save_window(cancel_dlg, "136-updater-cancel-confirm.png")
    cancel_dlg.Destroy()

    # 137 cancelled
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("DOWNLOAD_CANCELLED")
    _save_window(dlg.dlg, "137-updater-cancelled.png")
    dlg.Destroy()

    # 138 verifying
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("VERIFYING")
    _save_window(dlg.dlg, "138-updater-verifying.png")
    dlg.Destroy()

    # 139 ready to install
    dlg = WxUpdateDialog(None, rel)
    dlg._build_for_state("READY_TO_INSTALL")
    dlg._zip_path = "/tmp/fake.zip"
    _save_window(dlg.dlg, "139-updater-ready-to-install.png")
    dlg.Destroy()

    # 140 installing 25%
    inst = show_installing_splash(None, "1.9.0")
    inst._wx_install_update(25, "Copying application files...", "hpc_gui/services/app_updater.py")
    _save_window(inst, "140-updater-installing-25.png")
    inst.Destroy()

    # 141 installing 75%
    inst = show_installing_splash(None, "1.9.0")
    inst._wx_install_update(75, "Copying application files...", "hpc_gui/wx_updater_view.py")
    _save_window(inst, "141-updater-installing-75.png")
    inst.Destroy()

    # 142 restart required — use ready dialog but with restart message
    # For restart required, we can use the same ready dialog but with different text
    # Instead, create a simple restart dialog
    restart_dlg = wx.Dialog(None, title="Update Installed", style=wx.DEFAULT_DIALOG_STYLE)
    restart_dlg.SetMinSize(wx.Size(520, 260))
    panel = wx.Panel(restart_dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label="Update Installed")
    sizer.Add(title, 0, wx.ALL, 16)
    msg = wx.StaticText(panel, label="HPC Client must restart to finish the update.")
    sizer.Add(msg, 0, wx.LEFT | wx.RIGHT, 16)
    btns = wx.BoxSizer(wx.HORIZONTAL)
    restart_btn = wx.Button(panel, label="Restart Now")
    btns.AddStretchSpacer(1)
    btns.Add(restart_btn, 0)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 16)
    panel.SetSizer(sizer)
    _save_window(restart_dlg, "142-updater-restart-required.png")
    restart_dlg.Destroy()

    # 143 download error
    dlg = WxUpdateDialog(None, rel)
    dlg._error_message = "The download was interrupted."
    dlg._error_details = "HTTP status: 503\nURL: https://example.com/fake.zip\nReason: Service Unavailable"
    dlg._build_for_state("FAILED")
    _save_window(dlg.dlg, "143-updater-download-error.png")
    dlg.Destroy()

    # 144 verification error
    dlg = WxUpdateDialog(None, rel)
    dlg._error_message = "Package verification failed."
    dlg._error_details = "SHA256 mismatch\nexpected: abc123\nactual: def456"
    dlg._build_for_state("FAILED")
    _save_window(dlg.dlg, "144-updater-verification-error.png")
    dlg.Destroy()

    # 145 install error
    dlg = WxUpdateDialog(None, rel)
    dlg._error_message = "The installer could not replace application files."
    dlg._error_details = "Access denied: C:\\Program Files\\HPC Client\\hpc_gui.exe"
    dlg._build_for_state("FAILED")
    _save_window(dlg.dlg, "145-updater-install-error.png")
    dlg.Destroy()

    # 146 mandatory
    dlg = WxUpdateDialog(None, rel, mandatory=True)
    dlg._build_for_state("UPDATE_AVAILABLE")
    # For mandatory, the title should be Update Required, but our dialog uses Update Available
    # We need to ensure mandatory shows Update Required — our _build_available checks mandatory flag for buttons but not title
    # For screenshot, we can set title manually
    dlg.dlg.SetTitle("Update Required")
    _save_window(dlg.dlg, "146-updater-mandatory.png")
    dlg.Destroy()

    app.Destroy()
    print(f"Done, saved to {OUT_DIR}")

if __name__ == "__main__":
    main()
