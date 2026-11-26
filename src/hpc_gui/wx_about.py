"""Native wx About dialog – authoritative version, no network required."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.core.paths import is_frozen_exe


def _find_legal_file(name: str) -> Path | None:
    package = Path(__file__).resolve().parent
    candidates = [package / name, package.parent.parent / name]
    if is_frozen_exe():
        base = Path(sys.executable).resolve().parent
        candidates = [
            Path(getattr(sys, "_MEIPASS", base)) / name,
            base / name,
            base / "_internal" / name,
            base.parent / "Resources" / name,
            *candidates,
        ]
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _get_license_text_path() -> Path | None:
    return _find_legal_file("LICENSE")


def _get_notices_path() -> Path | None:
    return _find_legal_file("THIRD_PARTY_NOTICES.md")


def _open_legal_file(wx, path, url):
    if path is not None and path.is_file():
        try:
            if wx.LaunchDefaultApplication(str(path)):
                return
        except Exception:
            pass
    webbrowser.open(url)


def _create_about_dialog(parent=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    dlg = wx.Dialog(parent, title=t("about.title"), size=(480, 360))
    panel = wx.Panel(dlg)
    root = wx.BoxSizer(wx.VERTICAL)

    title = wx.StaticText(panel, label=t("app.title"))
    title_font = title.GetFont()
    title_font.SetPointSize(title_font.GetPointSize() + 4)
    title_font.SetWeight(wx.FONTWEIGHT_BOLD)
    title.SetFont(title_font)
    root.Add(title, 0, wx.ALL | wx.ALIGN_LEFT, 10)

    ver_text = t("about.version_label")
    if ver_text == "[about.version_label]":
        ver_text = f"Version {__version__}"
    else:
        ver_text = ver_text.format(version=__version__)
    ver_label = wx.StaticText(panel, label=ver_text)
    root.Add(ver_label, 0, wx.LEFT | wx.BOTTOM, 10)

    desc_text = t("about.description")
    desc = wx.StaticText(panel, label=desc_text)
    desc.Wrap(440)
    root.Add(desc, 0, wx.LEFT | wx.BOTTOM | wx.TOP, 10)

    repo_url = "https://github.com/mskomek/hpc-client-gui"
    repo_btn = wx.Button(panel, label=t("about.project"))

    def open_repo(_event):
        webbrowser.open(repo_url)

    repo_btn.Bind(wx.EVT_BUTTON, open_repo)
    root.Add(repo_btn, 0, wx.LEFT | wx.TOP, 10)

    license_path = _get_license_text_path()
    license_url = "https://github.com/mskomek/hpc-client-gui/blob/main/LICENSE"
    license_btn = wx.Button(panel, label=t("about.license"))

    def open_license(_event):
        _open_legal_file(wx, license_path, license_url)

    license_btn.Bind(wx.EVT_BUTTON, open_license)
    root.Add(license_btn, 0, wx.LEFT | wx.TOP, 10)

    notices_path = _get_notices_path()
    notices_url = "https://github.com/mskomek/hpc-client-gui/blob/main/THIRD_PARTY_NOTICES.md"
    notices_btn = wx.Button(panel, label=t("about.notices"))

    def open_notices(_event):
        _open_legal_file(wx, notices_path, notices_url)

    notices_btn.Bind(wx.EVT_BUTTON, open_notices)
    root.Add(notices_btn, 0, wx.LEFT | wx.TOP, 10)

    root.AddStretchSpacer(1)

    close_btn = wx.Button(panel, label=t("about.close"))

    def close_dialog(_event):
        dlg.EndModal(wx.ID_OK)

    close_btn.Bind(wx.EVT_BUTTON, close_dialog)
    root.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

    panel.SetSizer(root)
    dlg._wx_about_controls = {
        "version": ver_label, "repo": repo_btn, "license": license_btn,
        "notices": notices_btn, "close": close_btn,
    }
    dlg.Centre()
    return dlg


def show_about(parent=None) -> int:
    dlg = _create_about_dialog(parent)
    try:
        return dlg.ShowModal()
    finally:
        dlg.Destroy()


__all__ = ["show_about"]
