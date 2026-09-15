"""Native wx About dialog – authoritative version, no network required."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.core.paths import is_frozen_exe


def _get_license_text_path() -> Path | None:
    candidates: list[Path] = []
    candidates.append(Path(__file__).resolve().parent.parent / "LICENSE")
    candidates.append(Path(__file__).resolve().parent / "LICENSE")
    if is_frozen_exe():
        try:
            base = Path(sys.executable).resolve().parent
            candidates.append(base / "LICENSE")
            candidates.append(base / "_internal" / "LICENSE")
        except Exception:
            pass
    for p in candidates:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None


def _get_notices_path() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent / "THIRD_PARTY_NOTICES.md",
        Path(__file__).resolve().parent / "THIRD_PARTY_NOTICES.md",
    ]
    for p in candidates:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None


def show_about(parent=None) -> int:
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

    desc_text = t("about.description") if t("about.description") != "[about.description]" else "SSH · Slurm · X11 workflow manager for HPC clusters."
    desc = wx.StaticText(panel, label=desc_text)
    desc.Wrap(440)
    root.Add(desc, 0, wx.LEFT | wx.BOTTOM | wx.TOP, 10)

    repo_url = "https://github.com/mskomek/hpc-client-gui"
    repo_btn = wx.Button(panel, label=t("about.project") if t("about.project") != "[about.project]" else "Project Repository")

    def open_repo(_event):
        webbrowser.open(repo_url)

    repo_btn.Bind(wx.EVT_BUTTON, open_repo)
    root.Add(repo_btn, 0, wx.LEFT | wx.TOP, 10)

    license_path = _get_license_text_path()
    license_url = "https://github.com/mskomek/hpc-client-gui/blob/main/LICENSE"
    license_btn = wx.Button(panel, label=t("about.license") if t("about.license") != "[about.license]" else "License")

    def open_license(_event):
        if license_path and license_path.is_file():
            try:
                if sys.platform == "win32":
                    import os
                    os.startfile(str(license_path))
                    return
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.run(["open", str(license_path)], check=False)
                    return
            except Exception:
                pass
        webbrowser.open(license_url)

    license_btn.Bind(wx.EVT_BUTTON, open_license)
    root.Add(license_btn, 0, wx.LEFT | wx.TOP, 10)

    notices_path = _get_notices_path()
    notices_url = "https://github.com/mskomek/hpc-client-gui/blob/main/THIRD_PARTY_NOTICES.md"
    notices_btn = wx.Button(panel, label=t("about.notices") if t("about.notices") != "[about.notices]" else "Third-Party Notices")

    def open_notices(_event):
        if notices_path and notices_path.is_file():
            try:
                if sys.platform == "win32":
                    import os
                    os.startfile(str(notices_path))
                    return
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.run(["open", str(notices_path)], check=False)
                    return
            except Exception:
                pass
        webbrowser.open(notices_url)

    notices_btn.Bind(wx.EVT_BUTTON, open_notices)
    root.Add(notices_btn, 0, wx.LEFT | wx.TOP, 10)

    root.AddStretchSpacer(1)

    close_btn = wx.Button(panel, label=t("about.close") if t("about.close") != "[about.close]" else t("common.close"))

    def close_dialog(_event):
        dlg.EndModal(wx.ID_OK)

    close_btn.Bind(wx.EVT_BUTTON, close_dialog)
    root.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

    panel.SetSizer(root)
    dlg.Centre()
    dlg.ShowModal()
    dlg.Destroy()
    return wx.ID_OK


__all__ = ["show_about"]
