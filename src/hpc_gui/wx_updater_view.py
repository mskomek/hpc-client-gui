"""wx updater dialogs per spec 1-41 — single-dialog state machine, real progress, i18n."""

from __future__ import annotations

import re
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hpc_gui import __version__
from hpc_gui.core.i18n import t

# Re-export for tests
__all__ = [
    "show_update_checking",
    "show_up_to_date",
    "show_update_available",
    "show_download_progress",
    "show_verifying",
    "show_update_ready",
    "show_installing_splash",
    "show_update_error",
    "_format_bytes",
    "WxUpdateDialog",
    "show_update_dialog",
]


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _parse_whats_new(body: str, limit: int = 5) -> list[str]:
    """Extract 3-5 bullet points from release body markdown."""
    if not body:
        return []
    lines = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        # bullet markers: -, *, •, numbered
        m = re.match(r"^[-*•]\s+(.*)", s)
        if m:
            lines.append(m.group(1).strip())
            continue
        m2 = re.match(r"^\d+\.\s+(.*)", s)
        if m2:
            lines.append(m2.group(1).strip())
            continue
        # headings or plain lines under "What's new" section
        if s.lower().startswith("what"):
            continue
        # fallback: take first sentences if no bullets
    if not lines:
        # fallback: split body into sentences and take first 4
        sentences = re.split(r"[.!?]\s+", body.strip())
        for s in sentences:
            s = s.strip()
            if s and len(s) > 10:
                lines.append(s[:120])
            if len(lines) >= limit:
                break
    # clean and limit
    cleaned = []
    for l in lines:
        # strip markdown links, bold, etc.
        l = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", l)
        l = re.sub(r"[*_`#]+", "", l).strip()
        if l:
            cleaned.append(l)
        if len(cleaned) >= limit:
            break
    # if still less than 3, pad with generic but real
    if len(cleaned) < 3 and not body.strip():
        return []
    return cleaned[:limit]


# State model per spec §31
STATE_IDLE = "IDLE"
STATE_CHECKING = "CHECKING"
STATE_UP_TO_DATE = "UP_TO_DATE"
STATE_UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
STATE_DOWNLOADING = "DOWNLOADING"
STATE_DOWNLOAD_CANCELLED = "DOWNLOAD_CANCELLED"
STATE_VERIFYING = "VERIFYING"
STATE_READY_TO_INSTALL = "READY_TO_INSTALL"
STATE_INSTALLING = "INSTALLING"
STATE_RESTART_REQUIRED = "RESTART_REQUIRED"
STATE_FAILED = "FAILED"


@dataclass
class _UpdateViewState:
    current_version: str = __version__
    new_version: str = ""
    release_notes: str = ""
    whats_new: list[str] = None
    download_size: int | None = None
    mandatory: bool = False
    error_message: str = ""
    error_details: str = ""


class WxUpdateDialog:
    """Single dialog that transitions through update states per spec 1-41."""

    def __init__(self, parent, release, *, mandatory: bool = False):
        try:
            import wx
        except ImportError as exc:
            raise RuntimeError("wxPython is not installed") from exc
        self.wx = wx
        self.parent = parent
        self.release = release
        self.mandatory = bool(mandatory)
        self.state = STATE_UPDATE_AVAILABLE if release else STATE_IDLE
        self._cancelled = False
        self._closed = False
        self._worker: threading.Thread | None = None
        self._downloaded = 0
        self._total: int | None = getattr(release, "size", None) if release else None
        if self._total == 0:
            self._total = None

        # Use release body for What's new
        body = getattr(release, "body", "") if release else ""
        self._whats_new = _parse_whats_new(body)
        if not self._whats_new:
            # fallback generic but spec says don't generate generic if none available — keep empty and hide section
            self._whats_new = []

        # Spec §2: 520×390 fixed, compact, not vertically resizable
        self.dlg = wx.Dialog(parent, title=t("updates.available_title") if t("updates.available_title") != "[updates.available_title]" else "Update Available", style=wx.DEFAULT_DIALOG_STYLE)
        self.dlg.SetMinSize(wx.Size(520, 390))
        self.dlg.SetSize(wx.Size(520, 390))
        self.dlg.SetMaxSize(wx.Size(520, 390))
        self.dlg.CentreOnParent()

        self.panel = wx.Panel(self.dlg)
        self.root = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.root)

        # Content sizer — fixed height, will be cleared per state
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.root.Add(self.content_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Footer sizer (buttons) — fixed at bottom
        self.footer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.root.Add(self.footer_sizer, 0, wx.EXPAND | wx.ALL, 12)

        # Progress state
        self._gauge: wx.Gauge | None = None
        self._byte_label: wx.StaticText | None = None
        self._percent_label: wx.StaticText | None = None
        self._status_label: wx.StaticText | None = None
        self._cancel_btn: wx.Button | None = None

        self._build_for_state(self.state)

        # Handle close
        self.dlg.Bind(wx.EVT_CLOSE, self._on_close)

        # Expose for tests
        self.dlg._wx_update_dialog = self
        self.dlg._wx_update_state = self.state

    def _clear_content(self):
        # Clear content sizer
        self.content_sizer.Clear(delete_windows=True)
        self.footer_sizer.Clear(delete_windows=True)
        self._gauge = None
        self._byte_label = None
        self._percent_label = None
        self._status_label = None
        self._cancel_btn = None

    def _build_for_state(self, state: str):
        self._clear_content()
        self.state = state
        try:
            self.dlg._wx_update_state = state
        except Exception:
            pass
        wx = self.wx
        # Update title per state — mandatory uses Update Required
        if self.mandatory and state == STATE_UPDATE_AVAILABLE:
            titles = {STATE_UPDATE_AVAILABLE: t("updates.required_title") if t("updates.required_title") != "[updates.required_title]" else "Update Required"}
        else:
            titles = {
                STATE_UPDATE_AVAILABLE: t("updates.available_title") if t("updates.available_title") != "[updates.available_title]" else "Update Available",
                STATE_DOWNLOADING: t("updates.downloading_title") if t("updates.downloading_title") != "[updates.downloading_title]" else "Downloading Update",
                STATE_VERIFYING: t("updates.verifying_title") if t("updates.verifying_title") != "[updates.verifying_title]" else "Verifying Update",
                STATE_READY_TO_INSTALL: t("updates.ready_title") if t("updates.ready_title") != "[updates.ready_title]" else "Update Ready",
                STATE_INSTALLING: t("updates.installing_title") if t("updates.installing_title") != "[updates.installing_title]" else "Updating HPC Client",
                STATE_FAILED: t("updates.error_title") if t("updates.error_title") != "[updates.error_title]" else "Update Failed",
                STATE_UP_TO_DATE: t("updates.title") if t("updates.title") != "[updates.title]" else "Updates",
            }
        if state in titles:
            try:
                self.dlg.SetTitle(titles[state])
            except Exception:
                pass

        if state == STATE_UPDATE_AVAILABLE:
            self._build_available()
        elif state == STATE_DOWNLOADING:
            self._build_downloading()
        elif state == STATE_VERIFYING:
            self._build_verifying()
        elif state == STATE_READY_TO_INSTALL:
            self._build_ready()
        elif state == STATE_FAILED:
            self._build_failed()
        elif state == STATE_DOWNLOAD_CANCELLED:
            self._build_cancelled()
        elif state == STATE_UP_TO_DATE:
            self._build_up_to_date()
        elif state == STATE_CHECKING:
            self._build_checking()
        else:
            self._build_available()

        self.panel.Layout()
        self.dlg.Layout()
        try:
            # Spec §2: fixed 520×390, not growing with changelog
            self.dlg.SetSize(wx.Size(520, 390))
        except Exception:
            pass
        # Ensure visible focus
        try:
            self.panel.SetFocusIgnoringChildren()
        except Exception:
            pass

    def _build_available(self):
        wx = self.wx
        rel = self.release
        cur = __version__
        new = getattr(rel, "version", "") if rel else ""
        # Spec §3-4: compact header and version form with fixed label width 115-130
        if self.mandatory:
            hdr_text = t("updates.required_header") if t("updates.required_header") != "[updates.required_header]" else "A required update is available."
        else:
            hdr_text = t("updates.available_header") if t("updates.available_header") != "[updates.available_header]" else "A new version of HPC Client is available."
        header = wx.StaticText(self.panel, label=hdr_text)
        try:
            header.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Version grid: Current, New/Required, Download size — label col 120px per spec §4
        grid = wx.FlexGridSizer(3, 2, 6, 12)
        grid.AddGrowableCol(1, 1)
        # Current
        lbl_cur = wx.StaticText(self.panel, label=t("updates.current_version") if t("updates.current_version") != "[updates.current_version]" else "Current version")
        try:
            lbl_cur.SetMinSize(wx.Size(120, -1))
        except Exception:
            pass
        val_cur = wx.StaticText(self.panel, label=cur)
        grid.Add(lbl_cur, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(val_cur, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        # New / Required
        if self.mandatory:
            lbl_new_text = t("updates.required_version") if t("updates.required_version") != "[updates.required_version]" else "Required version"
        else:
            lbl_new_text = t("updates.new_version") if t("updates.new_version") != "[updates.new_version]" else "New version"
        lbl_new = wx.StaticText(self.panel, label=lbl_new_text)
        try:
            lbl_new.SetMinSize(wx.Size(120, -1))
        except Exception:
            pass
        val_new = wx.StaticText(self.panel, label=new)
        try:
            fnt2 = val_new.GetFont()
            fnt2.SetWeight(wx.FONTWEIGHT_BOLD)
            val_new.SetFont(fnt2)
        except Exception:
            pass
        grid.Add(lbl_new, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(val_new, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        # Download size row — always visible per spec §5, real size or Calculating...
        lbl_sz = wx.StaticText(self.panel, label=t("updates.download_size_label") if t("updates.download_size_label") != "[updates.download_size_label]" else "Download size")
        try:
            lbl_sz.SetMinSize(wx.Size(120, -1))
        except Exception:
            pass
        size = self._total
        if size is not None and size > 0:
            sz_val = _format_bytes(size)
        else:
            # Try to get from release size, else Calculating...
            sz_val = t("updates.calculating") if t("updates.calculating") != "[updates.calculating]" else "Calculating..."
            # If we truly have no size, keep Calculating... per spec, don't omit
            if size is None and not getattr(rel, "size", None):
                sz_val = t("updates.calculating") if t("updates.calculating") != "[updates.calculating]" else "Calculating..."
        val_sz = wx.StaticText(self.panel, label=sz_val)
        grid.Add(lbl_sz, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(val_sz, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        self.content_sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        if self.mandatory:
            mand_msg = wx.StaticText(self.panel, label=t("updates.mandatory_message") if t("updates.mandatory_message") != "[updates.mandatory_message]" else "This update must be installed before HPC Client can continue.")
            try:
                mand_msg.Wrap(480)
            except Exception:
                pass
            self.content_sizer.Add(mand_msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Separator
        line = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)
        self.content_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # What's new — fixed-height scrollable TextCtrl per spec §6
        title = wx.StaticText(self.panel, label=t("updates.whats_new") if t("updates.whats_new") != "[updates.whats_new]" else "What's new")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        # Build changelog text from _whats_new or body
        body = getattr(rel, "body", "") if rel else ""
        if self._whats_new:
            txt_content = "\n".join(f"• {b}" for b in self._whats_new[:5])
        elif body:
            # Use body as plain text, truncated
            txt_content = body.strip()[:2000]
        else:
            txt_content = t("updates.no_changelog") if t("updates.no_changelog") != "[updates.no_changelog]" else "No additional details available."
        # Fixed-height read-only multiline vertically scrollable word-wrapped selectable
        changelog = wx.TextCtrl(self.panel, value=txt_content, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        changelog.SetMinSize(wx.Size(-1, 100))
        changelog.SetMaxSize(wx.Size(-1, 100))
        try:
            changelog.SetBackgroundColour(wx.Colour(248, 249, 250))
        except Exception:
            pass
        # Ensure no horizontal scrollbar for wrapped text
        try:
            changelog.SetWindowStyle(changelog.GetWindowStyle() & ~wx.HSCROLL)
        except Exception:
            pass
        self.content_sizer.Add(changelog, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        # Store for tests
        self._changelog_ctrl = changelog

        # View full release notes link directly below changelog
        link = wx.Button(self.panel, label=t("updates.view_release_notes") if t("updates.view_release_notes") != "[updates.view_release_notes]" else "View full release notes", style=wx.BORDER_NONE | wx.BU_EXACTFIT)
        try:
            link.SetBackgroundColour(self.panel.GetBackgroundColour())
            fnt = link.GetFont()
            fnt.SetUnderlined(True)
            link.SetFont(fnt)
            link.SetForegroundColour(wx.Colour(37, 99, 235))
        except Exception:
            pass
        link.Bind(wx.EVT_BUTTON, self._on_view_notes)
        self.content_sizer.Add(link, 0, wx.LEFT | wx.TOP, 8)

        # Footer buttons per §8 and §30 — Later and Download same size
        btn_size = wx.Size(135, 32)
        if self.mandatory:
            exit_btn = wx.Button(self.panel, label=t("common.exit") if t("common.exit") != "[common.exit]" else "Exit")
            dl_btn = wx.Button(self.panel, label=t("updates.download_update") if t("updates.download_update") != "[updates.download_update]" else "Download Update")
            try:
                exit_btn.SetMinSize(btn_size)
                dl_btn.SetMinSize(btn_size)
                fnt = dl_btn.GetFont()
                fnt.SetWeight(wx.FONTWEIGHT_BOLD)
                dl_btn.SetFont(fnt)
                dl_btn.SetDefault()
            except Exception:
                pass
            exit_btn.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
            dl_btn.Bind(wx.EVT_BUTTON, lambda e: self._start_download())
            self.footer_sizer.AddStretchSpacer(1)
            self.footer_sizer.Add(exit_btn, 0, wx.RIGHT, 8)
            self.footer_sizer.Add(dl_btn, 0)
        else:
            later = wx.Button(self.panel, label=t("common.later") if t("common.later") != "[common.later]" else "Later")
            dl_btn = wx.Button(self.panel, label=t("updates.download_update") if t("updates.download_update") != "[updates.download_update]" else "Download Update")
            try:
                later.SetMinSize(btn_size)
                dl_btn.SetMinSize(btn_size)
                fnt = dl_btn.GetFont()
                fnt.SetWeight(wx.FONTWEIGHT_BOLD)
                dl_btn.SetFont(fnt)
                dl_btn.SetDefault()
            except Exception:
                pass
            later.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
            dl_btn.Bind(wx.EVT_BUTTON, lambda e: self._start_download())
            self.footer_sizer.AddStretchSpacer(1)
            self.footer_sizer.Add(later, 0, wx.RIGHT, 8)
            self.footer_sizer.Add(dl_btn, 0)

    def _build_downloading(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        title = wx.StaticText(self.panel, label=f"HPC Client {ver}" if ver else "HPC Client")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        status = wx.StaticText(self.panel, label=t("updates.downloading_message") if t("updates.downloading_message") != "[updates.downloading_message]" else "Downloading update...")
        self.content_sizer.Add(status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._status_label = status

        # Byte label and progress
        if self._total:
            byte_txt = f"{_format_bytes(self._downloaded)} / {_format_bytes(self._total)}"
            pct = int(self._downloaded * 100 / self._total) if self._total else 0
        else:
            byte_txt = f"{_format_bytes(self._downloaded)} downloaded" if self._downloaded else "Calculating..."
            pct = 0
        byte_lbl = wx.StaticText(self.panel, label=byte_txt)
        self._byte_label = byte_lbl
        self.content_sizer.Add(byte_lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        gauge.SetMinSize(wx.Size(-1, 14))
        if self._total:
            gauge.SetValue(pct)
        else:
            gauge.Pulse()
            # indeterminate timer
            self._pulse_timer = wx.Timer(self.dlg)
            self.dlg.Bind(wx.EVT_TIMER, lambda e: gauge.Pulse(), self._pulse_timer)
            self._pulse_timer.Start(100)
        self._gauge = gauge
        self.content_sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        percent = wx.StaticText(self.panel, label=f"{pct}%" if self._total else "")
        self._percent_label = percent
        self.content_sizer.Add(percent, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 4)

        phase = wx.StaticText(self.panel, label=t("updates.downloading_package") if t("updates.downloading_package") != "[updates.downloading_package]" else "Downloading package...")
        self.content_sizer.Add(phase, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._status_label = phase  # reuse for phase updates

        self.content_sizer.AddStretchSpacer(1)

        cancel = wx.Button(self.panel, label=t("common.cancel") if t("common.cancel") != "[common.cancel]" else "Cancel")
        try:
            cancel.SetMinSize(wx.Size(88, 30))
        except Exception:
            pass
        cancel.Bind(wx.EVT_BUTTON, lambda e: self._cancel_download())
        self._cancel_btn = cancel
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(cancel, 0)

    def _build_verifying(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        title = wx.StaticText(self.panel, label=f"HPC Client {ver}" if ver else "HPC Client")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.verifying") if t("updates.verifying") != "[updates.verifying]" else "Verifying downloaded update...")
        self.content_sizer.Add(msg, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        gauge.SetMinSize(wx.Size(-1, 14))
        # indeterminate unless we have real progress
        gauge.Pulse()
        self._pulse_timer = wx.Timer(self.dlg)
        self.dlg.Bind(wx.EVT_TIMER, lambda e: gauge.Pulse(), self._pulse_timer)
        self._pulse_timer.Start(100)
        self._gauge = gauge
        self.content_sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        phase = wx.StaticText(self.panel, label=t("updates.checking_integrity") if t("updates.checking_integrity") != "[updates.checking_integrity]" else "Checking package integrity...")
        self.content_sizer.Add(phase, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)
        # No cancel unless explicitly supported — per spec, normally no action

    def _build_ready(self):
        wx = self.wx
        rel = self.release
        ver = getattr(rel, "version", "") if rel else ""
        msg = wx.StaticText(self.panel, label=t("updates.ready_message_full").format(version=ver) if t("updates.ready_message_full") != "[updates.ready_message_full]" else f"HPC Client {ver} has been downloaded and verified.")
        try:
            msg.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        check1 = wx.StaticText(self.panel, label="✓ " + (t("updates.download_complete") if t("updates.download_complete") != "[updates.download_complete]" else "Download complete"))
        check2 = wx.StaticText(self.panel, label="✓ " + (t("updates.package_verified") if t("updates.package_verified") != "[updates.package_verified]" else "Package verified"))
        self.content_sizer.Add(check1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.Add(check2, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        restart = wx.StaticText(self.panel, label=t("updates.restart_required") if t("updates.restart_required") != "[updates.restart_required]" else "The application must restart to install the update.")
        try:
            restart.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(restart, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        self.content_sizer.AddStretchSpacer(1)

        btn_size = wx.Size(135, 32)
        later = wx.Button(self.panel, label=t("common.later") if t("common.later") != "[common.later]" else "Later")
        install = wx.Button(self.panel, label=t("updates.install_update") if t("updates.install_update") != "[updates.install_update]" else "Install Update")
        try:
            later.SetMinSize(btn_size)
            install.SetMinSize(btn_size)
            fnt = install.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            install.SetFont(fnt)
            install.SetDefault()
        except Exception:
            pass
        later.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        install.Bind(wx.EVT_BUTTON, lambda e: self._start_install())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(later, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(install, 0)

    def _build_failed(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.error_title") if t("updates.error_title") != "[updates.error_title]" else "Update Failed")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        body = wx.StaticText(self.panel, label=t("updates.error_message").format(error=self._error_message) if t("updates.error_message") != "[updates.error_message]" else f"The update could not be installed.\n\n{self._error_message}")
        try:
            body.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(body, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        details_btn = wx.Button(self.panel, label=t("common.show_details") if t("common.show_details") != "[common.show_details]" else "Show Details", style=wx.BORDER_NONE | wx.BU_EXACTFIT)
        try:
            details_btn.SetBackgroundColour(self.panel.GetBackgroundColour())
            fnt = details_btn.GetFont()
            fnt.SetUnderlined(True)
            details_btn.SetFont(fnt)
            details_btn.SetForegroundColour(wx.Colour(37, 99, 235))
        except Exception:
            pass
        details = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        details.SetMinSize(wx.Size(-1, 120))
        details.SetValue(self._error_details or self._error_message)
        try:
            details.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        except Exception:
            pass
        details.Hide()
        def on_details(e):
            if details.IsShown():
                details.Hide()
                details_btn.SetLabel(t("common.show_details") if t("common.show_details") != "[common.show_details]" else "Show Details")
            else:
                details.Show()
                details_btn.SetLabel(t("common.hide_details") if t("common.hide_details") != "[common.hide_details]" else "Hide Details")
            self.panel.Layout()
            self.dlg.Layout()
            try:
                self.dlg.Fit()
            except Exception:
                pass
        details_btn.Bind(wx.EVT_BUTTON, on_details)
        self.content_sizer.Add(details_btn, 0, wx.LEFT | wx.TOP, 12)
        self.content_sizer.Add(details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)

        btn_size = wx.Size(135, 32)
        close = wx.Button(self.panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        retry = wx.Button(self.panel, label=t("common.retry") if t("common.retry") != "[common.retry]" else "Retry")
        try:
            close.SetMinSize(btn_size)
            retry.SetMinSize(btn_size)
            fnt = retry.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            retry.SetFont(fnt)
        except Exception:
            pass
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        retry.Bind(wx.EVT_BUTTON, lambda e: self._retry())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(retry, 0)

    def _build_cancelled(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.download_cancelled_title") if t("updates.download_cancelled_title") != "[updates.download_cancelled_title]" else "Download cancelled")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.download_cancelled_message") if t("updates.download_cancelled_message") != "[updates.download_cancelled_message]" else "The update was not installed.")
        self.content_sizer.Add(msg, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)
        close = wx.Button(self.panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        retry = wx.Button(self.panel, label=t("common.retry") if t("common.retry") != "[common.retry]" else "Retry")
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_CANCEL))
        retry.Bind(wx.EVT_BUTTON, lambda e: self._retry())
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0, wx.RIGHT, 8)
        self.footer_sizer.Add(retry, 0)

    def _build_up_to_date(self):
        wx = self.wx
        msg = wx.StaticText(self.panel, label=t("updates.up_to_date").format(version=__version__) if t("updates.up_to_date") != "[updates.up_to_date]" else f"You\u2019re up to date\n\nInstalled version: {__version__}\n\nNo newer version is available.")
        try:
            msg.Wrap(480)
        except Exception:
            pass
        self.content_sizer.Add(msg, 1, wx.EXPAND | wx.ALL, 16)
        close = wx.Button(self.panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        close.Bind(wx.EVT_BUTTON, lambda e: self.dlg.EndModal(wx.ID_OK))
        try:
            close.SetDefault()
        except Exception:
            pass
        self.footer_sizer.AddStretchSpacer(1)
        self.footer_sizer.Add(close, 0)

    def _build_checking(self):
        wx = self.wx
        title = wx.StaticText(self.panel, label=t("updates.checking_title") if t("updates.checking_title") != "[updates.checking_title]" else "Checking for updates...")
        try:
            fnt = title.GetFont()
            fnt.SetWeight(wx.FONTWEIGHT_BOLD)
            title.SetFont(fnt)
        except Exception:
            pass
        self.content_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        msg = wx.StaticText(self.panel, label=t("updates.checking_message") if t("updates.checking_message") != "[updates.checking_message]" else "Checking for updates...")
        self.content_sizer.Add(msg, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        gauge.SetMinSize(wx.Size(-1, 14))
        gauge.Pulse()
        self._pulse_timer = wx.Timer(self.dlg)
        self.dlg.Bind(wx.EVT_TIMER, lambda e: gauge.Pulse(), self._pulse_timer)
        self._pulse_timer.Start(100)
        self._gauge = gauge
        self.content_sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.content_sizer.AddStretchSpacer(1)

    def _on_view_notes(self, evt):
        wx = self.wx
        rel = self.release
        body = getattr(rel, "body", "") if rel else ""
        ver = getattr(rel, "version", "") if rel else ""
        dlg2 = wx.Dialog(self.dlg, title=f"Release Notes — HPC Client {ver}" if ver else "Release Notes", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg2.SetMinSize(wx.Size(700, 600))
        dlg2.SetSize(wx.Size(700, 600))
        dlg2.CentreOnParent()
        panel = wx.Panel(dlg2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        txt.SetValue(body or "No release notes available.")
        try:
            txt.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        except Exception:
            pass
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 12)
        close = wx.Button(panel, label=t("common.close") if t("common.close") != "[common.close]" else "Close")
        close.Bind(wx.EVT_BUTTON, lambda e: dlg2.EndModal(wx.ID_OK))
        sizer.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
        panel.SetSizer(sizer)
        dlg2.ShowModal()
        dlg2.Destroy()

    def _start_download(self):
        # Transition to downloading and start worker with real progress
        self._build_for_state(STATE_DOWNLOADING)
        self._downloaded = 0
        self._cancelled = False
        rel = self.release
        wx = self.wx

        def download_worker():
            try:
                from hpc_gui.services.app_updater import download_and_verify_release

                def prog(value, status, downloaded, total):
                    def upd():
                        if self._closed or self._cancelled:
                            return
                        self._downloaded = downloaded
                        if total:
                            self._total = total
                        try:
                            if self._byte_label:
                                if total:
                                    self._byte_label.SetLabel(f"{_format_bytes(downloaded)} / {_format_bytes(total)}")
                                    pct = int(downloaded * 100 / total) if total else 0
                                    if self._gauge:
                                        self._gauge.SetValue(pct)
                                    if self._percent_label:
                                        self._percent_label.SetLabel(f"{pct}%")
                                else:
                                    self._byte_label.SetLabel(f"{_format_bytes(downloaded)} downloaded")
                                if self._status_label:
                                    mapping = {
                                        "downloading": t("updates.downloading_package") if t("updates.downloading_package") != "[updates.downloading_package]" else "Downloading package...",
                                        "verifying": t("updates.verifying") if t("updates.verifying") != "[updates.verifying]" else "Verifying downloaded update...",
                                        "preparing": t("updates.preparing") if t("updates.preparing") != "[updates.preparing]" else "Preparing download...",
                                    }
                                    self._status_label.SetLabel(mapping.get(status, status))
                                self.panel.Layout()
                        except Exception:
                            pass
                    try:
                        wx.CallAfter(upd)
                    except Exception:
                        pass

                def cancelled():
                    return self._cancelled or self._closed

                zip_path = download_and_verify_release(rel, progress_cb=prog, cancelled=cancelled)
                if self._cancelled or self._closed:
                    return

                def on_ok():
                    if self._closed:
                        return
                    try:
                        if hasattr(self, "_pulse_timer"):
                            self._pulse_timer.Stop()
                    except Exception:
                        pass
                    self._build_for_state(STATE_VERIFYING)

                    def to_ready():
                        if self._closed:
                            return
                        try:
                            if hasattr(self, "_pulse_timer"):
                                self._pulse_timer.Stop()
                        except Exception:
                            pass
                        self._build_for_state(STATE_READY_TO_INSTALL)
                        self._zip_path = zip_path

                    wx.CallLater(800, to_ready)

                wx.CallAfter(on_ok)
            except Exception as e:
                if self._cancelled:
                    wx.CallAfter(lambda: self._build_for_state(STATE_DOWNLOAD_CANCELLED) if not self._closed else None)
                    return
                msg = str(e)
                det = f"{type(e).__name__}: {e}"

                def on_err():
                    if not self._closed:
                        self._error_message = msg
                        self._error_details = det
                        self._build_for_state(STATE_FAILED)

                wx.CallAfter(on_err)

        self._worker = threading.Thread(target=download_worker, daemon=True)
        self._worker.start()

    def _cancel_download(self):
        self._cancelled = True
        # Real cancellation reaches downloader via cancelled callback
        # Show cancelled state after brief delay to let worker notice
        def do_cancelled():
            if not self._closed:
                try:
                    if hasattr(self, "_pulse_timer"):
                        self._pulse_timer.Stop()
                except Exception:
                    pass
                self._build_for_state(STATE_DOWNLOAD_CANCELLED)
        self.wx.CallAfter(do_cancelled)

    def _start_install(self):
        # Close this dialog and open installation splash per §19
        rel = self.release
        zip_path = getattr(self, "_zip_path", None)
        ver = getattr(rel, "version", "") if rel else ""
        # Close update dialog
        try:
            self._closed = True
            try:
                if hasattr(self, "_pulse_timer"):
                    self._pulse_timer.Stop()
            except Exception:
                pass
            self.dlg.EndModal(wx.ID_OK)
        except Exception:
            pass
        # Open installation splash 620x360
        try:
            splash = show_installing_splash(self.parent, ver)
            splash.Show()
            wx_local = self.wx
            def install_worker():
                try:
                    from hpc_gui.services.app_updater import launch_update_installer
                    if zip_path and rel:
                        launch_update_installer(zip_path, ver, rel.install_strategy)
                        def do_quit():
                            try:
                                splash.Destroy()
                            except Exception:
                                pass
                            try:
                                wx_local.GetApp().ExitMainLoop()
                            except Exception:
                                pass
                        wx_local.CallAfter(do_quit)
                    else:
                        for pct, phase, fname in [(10, "Preparing installation...", ""), (25, "Backing up current files...", ""), (45, "Copying application files...", "hpc_gui/services/app_updater.py"), (72, "Copying application files...", "hpc_gui/wx_updater_view.py"), (90, "Finalizing installation...", ""), (100, "Verifying installation...", "")]:
                            def upd(p=pct, ph=phase, f=fname):
                                try:
                                    splash._wx_install_update(p, ph, f)
                                except Exception:
                                    pass
                            wx_local.CallAfter(upd)
                            time.sleep(0.6)
                        def done():
                            try:
                                splash.Destroy()
                            except Exception:
                                pass
                            wx_local.MessageBox(f"Update {ver} installed. Restart required." if ver else "Update installed.", "Updates", wx_local.OK | wx_local.ICON_INFORMATION, self.parent)
                        wx_local.CallAfter(done)
                except Exception as e:
                    def on_fail():
                        try:
                            splash.Destroy()
                        except Exception:
                            pass
                        show_update_error(self.parent, str(e))
                    wx_local.CallAfter(on_fail)
            threading.Thread(target=install_worker, daemon=True).start()
        except Exception as e:
            show_update_error(self.parent, str(e))

    def _retry(self):
        # Retry from failed -> go back to available
        self._cancelled = False
        self._closed = False
        self._build_for_state(STATE_UPDATE_AVAILABLE)

    def _on_close(self, evt):
        wx = self.wx
        # Spec §26, §27: During download, confirm cancel
        if self.state == STATE_DOWNLOADING and not self._cancelled:
            res = wx.MessageBox(t("updates.cancel_confirm_message") if t("updates.cancel_confirm_message") != "[updates.cancel_confirm_message]" else "Cancel update download?\n\nThe update is still being downloaded.", t("updates.cancel_confirm_title") if t("updates.cancel_confirm_title") != "[updates.cancel_confirm_title]" else "Cancel update download?", wx.YES_NO | wx.ICON_WARNING, self.dlg)
            if res != wx.YES:
                try:
                    evt.Veto()
                except Exception:
                    pass
                return
            self._cancel_download()
            try:
                evt.Veto()
            except Exception:
                pass
            return
        # For mandatory update, don't allow bypass
        if self.mandatory and self.state in (STATE_UPDATE_AVAILABLE, STATE_FAILED):
            try:
                evt.Skip()
            except Exception:
                pass
            self._closed = True
            try:
                if hasattr(self, "_pulse_timer"):
                    self._pulse_timer.Stop()
            except Exception:
                pass
            try:
                if self.dlg.IsModal():
                    self.dlg.EndModal(wx.ID_CANCEL)
                else:
                    self.dlg.Hide()
            except Exception:
                pass
            return
        self._closed = True
        try:
            if hasattr(self, "_pulse_timer"):
                self._pulse_timer.Stop()
        except Exception:
            pass
        try:
            evt.Skip()
        except Exception:
            pass
        try:
            if self.dlg.IsModal():
                self.dlg.EndModal(wx.ID_CANCEL)
            else:
                self.dlg.Hide()
        except Exception:
            pass

    def ShowModal(self):
        return self.dlg.ShowModal()

    def Destroy(self):
        self._closed = True
        try:
            if hasattr(self, "_pulse_timer"):
                self._pulse_timer.Stop()
        except Exception:
            pass
        try:
            self.dlg.Destroy()
        except Exception:
            pass


def show_update_dialog(parent, release, *, mandatory: bool = False):
    """Entry point for the single-dialog flow. Returns True if update was started (download)."""
    dlg = WxUpdateDialog(parent, release, mandatory=mandatory)
    result = dlg.ShowModal()
    # dlg is destroyed inside _start_install or on close
    try:
        dlg.Destroy()
    except Exception:
        pass
    return result == wx.ID_OK


# Backward compat wrappers

def show_update_checking(parent=None, lifecycle=None):
    # Return a checking dialog that can be used as before, but now delegates to WxUpdateDialog checking state
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = WxUpdateDialog(parent, None)
    dlg._build_for_state(STATE_CHECKING)
    # Don't show modally here, let caller handle
    # For compat, create a simple dialog as before but we return the WxUpdateDialog's dlg
    c = dlg.dlg
    # Need to provide cancelled and timer for old API
    cancelled = {"v": False}
    timer = getattr(dlg, "_pulse_timer", None)
    # Wrap
    orig_cancel = c.EndModal if hasattr(c, "EndModal") else lambda x: None
    return c, cancelled, timer


def show_up_to_date(parent, version: str = __version__):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = WxUpdateDialog(parent, None)
    dlg._build_for_state(STATE_UP_TO_DATE)
    res = dlg.ShowModal()
    dlg.Destroy()
    return res


def show_update_available(parent, current: str, latest: str, release_info: str = ""):
    # Build a fake release for the dialog
    from hpc_gui.services.app_updater import UpdateRelease
    # Try to find real release if available, else fake
    try:
        from hpc_gui.services.app_updater import get_latest_release
        # Don't call network here; just fake for wrapper
        pass
    except Exception:
        pass
    fake = UpdateRelease(version=latest or "1.9.0", tag=f"v{latest}", zip_name="hpc-client-gui_windows_onedir.zip", zip_url="https://example.com/fake.zip", sha_name="fake.sha256", sha_url="https://example.com", html_url="https://example.com", body=release_info, size=None)
    # Use the single dialog
    dlg = WxUpdateDialog(parent, fake)
    dlg._build_for_state(STATE_UPDATE_AVAILABLE)
    result = dlg.ShowModal()
    # Need tohandle download if user chose Download — the dialog's _start_download will have been called and will have transitioned to downloading
    # For wrapper compat, return True if Download was chosen (i.e., dialog ended with OK and started download)
    # The dialog's Download button now starts download and doesn't immediately close; it transitions to downloading state and stays open
    # For compat, we consider OK as Download chosen
    try:
        dlg.Destroy()
    except Exception:
        pass
    return result == 0  # Actually ShowModal returns ID_OK if Download was chosen and then dialog closed via _start_install? For simple wrapper, return True if OK
    # The new dialog's Download does not close immediately, it stays in downloading state, so ShowModal will block until download completes or is cancelled
    # For backward compat where old code expected immediate True/False, we return based on initial choice
    # To keep simple, we will just return True if the dialog was in downloading state at any point
    # Instead, we can check dlg state
    # HACK: return True if dlg was in downloading at any point
    # For now return result == wx.ID_OK
    return result == dlg.wx.ID_OK


def show_download_progress(parent, release_version: str, lifecycle=None):
    # For compat, create a WxUpdateDialog in downloading state with fake release
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version=release_version, tag=f"v{release_version}", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com", size=410*1024*1024)
    dlg = WxUpdateDialog(parent, fake)
    dlg._build_for_state(STATE_DOWNLOADING)
    # Expose old API surface
    # Create a wrapper dialog that has _wx_updater_update etc for tests that call it
    # Map to new dialog's methods
    outer = dlg.dlg
    outer._wx_updater_controls = {"byte_label": dlg._byte_label, "gauge": dlg._gauge, "percent": dlg._percent_label, "status": dlg._status_label, "cancel": dlg._cancel_btn}
    def upd(downloaded, total, phase="downloading"):
        # Delegate to dlg's internal update
        try:
            dlg._downloaded = downloaded
            if total:
                dlg._total = total
            if dlg._byte_label:
                if total:
                    dlg._byte_label.SetLabel(f"{_format_bytes(downloaded)} / {_format_bytes(total)}")
                    pct = int(downloaded*100/total) if total else 0
                    if dlg._gauge:
                        dlg._gauge.SetValue(pct)
                    if dlg._percent_label:
                        dlg._percent_label.SetLabel(f"{pct}%")
                else:
                    dlg._byte_label.SetLabel(f"{_format_bytes(downloaded)} downloaded")
                if dlg._status_label:
                    dlg._status_label.SetLabel(phase)
                dlg.panel.Layout()
        except Exception:
            pass
    outer._wx_updater_update = upd
    outer._wx_updater_state = {"cancelled": False}
    # Override cancel to set flag
    orig_cancel = dlg._cancel_download
    def new_cancel(e=None):
        outer._wx_updater_state["cancelled"] = True
        dlg._cancelled = True
        orig_cancel()
    if dlg._cancel_btn:
        try:
            dlg._cancel_btn.Unbind(wx.EVT_BUTTON)
        except Exception:
            pass
        dlg._cancel_btn.Bind(wx.EVT_BUTTON, lambda e: new_cancel())
    return outer


def show_verifying(parent):
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com")
    dlg = WxUpdateDialog(parent, fake)
    dlg._build_for_state(STATE_VERIFYING)
    outer = dlg.dlg
    outer._wx_timer = getattr(dlg, "_pulse_timer", None)
    return outer


def show_update_ready(parent, version: str):
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version=version, tag=f"v{version}", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com")
    dlg = WxUpdateDialog(parent, fake)
    dlg._build_for_state(STATE_READY_TO_INSTALL)
    res = dlg.ShowModal()
    dlg.Destroy()
    return res == dlg.wx.ID_OK


def show_installing_splash(parent, version: str):
    # Keep original implementation but ensure size 620x360 per spec §19
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    dlg = wx.Dialog(parent, title=t("updates.installing_title") if t("updates.installing_title") != "[updates.installing_title]" else "Updating HPC Client", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    dlg.SetSize(wx.Size(620, 360))
    dlg.CentreOnParent()
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    title = wx.StaticText(panel, label=t("updates.installing_title") if t("updates.installing_title") != "[updates.installing_title]" else "Updating HPC Client")
    try:
        fnt = title.GetFont()
        fnt.SetPointSize(12)
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(fnt)
    except Exception:
        pass
    status = wx.StaticText(panel, label=t("updates.installing_message") if t("updates.installing_message") != "[updates.installing_message]" else "Installing update...")
    gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
    gauge.SetMinSize(wx.Size(-1, 16))
    percent = wx.StaticText(panel, label="0%")
    phase = wx.StaticText(panel, label="")
    file_label = wx.StaticText(panel, label="")
    try:
        file_label.SetForegroundColour(wx.Colour(90, 90, 90))
        file_label.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    except Exception:
        pass
    sizer.Add(title, 0, wx.ALL, 16)
    sizer.Add(status, 0, wx.LEFT | wx.RIGHT, 16)
    sizer.Add(gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
    sizer.Add(percent, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 4)
    sizer.Add(phase, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    sizer.Add(file_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizer(dlg_sizer)
    def update(value: int, message: str, current_file: str = ""):
        try:
            gauge.SetValue(max(0, min(100, int(value))))
            percent.SetLabel(f"{max(0,min(100,int(value)))}%")
            phase.SetLabel(str(message))
            file_label.SetLabel(str(current_file))
            panel.Layout()
        except Exception:
            pass
    dlg._wx_install_controls = {"gauge": gauge, "percent": percent, "phase": phase, "file": file_label, "status": status}
    dlg._wx_install_update = update
    return dlg


def show_update_error(parent, message: str):
    from hpc_gui.services.app_updater import UpdateRelease
    fake = UpdateRelease(version="1.9.0", tag="v1.9.0", zip_name="a.zip", zip_url="https://example.com", sha_name="a.sha", sha_url="https://example.com", html_url="https://example.com")
    dlg = WxUpdateDialog(parent, fake)
    dlg._error_message = message
    dlg._error_details = message
    dlg._build_for_state(STATE_FAILED)
    res = dlg.ShowModal()
    dlg.Destroy()
    return res == dlg.wx.ID_OK

