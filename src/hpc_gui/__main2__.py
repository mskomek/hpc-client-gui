"""Mock-update entry point using the normal startup splash."""

import sys
import time
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


MOCK_VERSION = "1.5.9-mock"


def _show_install_splash(wx, parent) -> None:
    splash = wx.Dialog(parent, title="Mock Yükleme", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    splash.SetSize((480, 220))
    splash.Centre()
    panel = wx.Panel(splash)
    root = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label="YENİ SÜRÜM YÜKLENİYOR")
    status = wx.StaticText(panel, label=f"v{MOCK_VERSION} hazırlanıyor...")
    gauge = wx.Gauge(panel, range=100)
    root.Add(title, 0, wx.ALIGN_CENTER | wx.TOP, 28)
    root.Add(status, 0, wx.ALIGN_CENTER | wx.TOP, 18)
    root.Add(gauge, 0, wx.EXPAND | wx.ALL, 28)
    panel.SetSizer(root)

    def finish():
        gauge.SetValue(100)
        status.SetLabel(f"v{MOCK_VERSION} başlatılıyor...")
        wx.CallLater(500, lambda: splash.EndModal(wx.ID_OK))

    gauge.SetValue(55)
    wx.CallLater(1200, finish)
    splash.ShowModal()
    splash.Destroy()


def _run_mock_startup(app, wx) -> None:
    from hpc_gui.core.i18n import load_saved_language, system_default_language
    from hpc_gui.wx_splash import STATE_ACTIVE, STATE_COMPLETE, create_startup_splash
    from hpc_gui.wx_shell import create_shell_frame

    load_saved_language(system_default_language())
    splash = create_startup_splash(None, pure_splash=True, mock_update=True)
    splash.Show()
    app.SetTopWindow(splash)
    app.Yield(True)
    splash._wx_splash_set_stage("updates", STATE_ACTIVE)
    splash._wx_splash_set_progress(20, "Güncellenme denetleniyor...")
    splash._wx_splash_append_log("Güncellenme denetleniyor...", "OK")
    splash._wx_splash_show_mock_update(MOCK_VERSION)

    controls = splash._wx_splash_controls
    download = controls["mandatory_view"]
    install = controls["mandatory_update"]
    skip = controls["mandatory_skip"]
    total_bytes = 100 * 1024 * 1024
    download_state = {"bytes": 0, "started": 0.0, "closed": False}

    def open_main(version: str):
        download_state["closed"] = True
        splash.Destroy()
        frame, _lifecycle, _session_state = create_shell_frame(app)
        frame.SetTitle(f"HPC Client GUI v{version}")
        frame.Show()

    def downloaded():
        splash._wx_splash_set_progress(100, "Mock güncelleme indirildi.")
        splash._wx_splash_append_log("Mock güncelleme indirildi", "OK")
        install.Enable()
        answer = wx.MessageBox(
            "Güncelleme indirildi. Şimdi yüklemek ister misiniz?",
            "Güncelleme hazır",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if answer == wx.YES:
            on_install(None)

    def download_tick():
        if download_state["closed"]:
            return
        current = min(total_bytes, download_state["bytes"] + 8 * 1024 * 1024)
        download_state["bytes"] = current
        elapsed = max(0.1, time.monotonic() - download_state["started"])
        speed = current / elapsed
        remaining = (total_bytes - current) / max(1, speed)
        splash._wx_splash_set_download_metrics(current, total_bytes, speed, remaining)
        splash._wx_splash_set_status("Mock güncelleme indiriliyor...")
        if current < total_bytes:
            wx.CallLater(200, download_tick)
        else:
            downloaded()

    def on_download(_event):
        download.Disable()
        download_state["started"] = time.monotonic()
        download_tick()

    def on_install(_event):
        install.Disable()
        splash.Hide()
        _show_install_splash(wx, splash)
        splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        splash._wx_splash_set_progress(100, "Güncelleme tamamlandı.")
        open_main(MOCK_VERSION)

    def on_skip(_event):
        open_main("current")

    download.Bind(wx.EVT_BUTTON, on_download)
    install.Bind(wx.EVT_BUTTON, on_install)
    skip.Bind(wx.EVT_BUTTON, on_skip)
    splash.Bind(wx.EVT_CLOSE, lambda event: event.Skip())


def main() -> int:
    import wx

    app = wx.App(False)
    _run_mock_startup(app, wx)
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
