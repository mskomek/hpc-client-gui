"""Journal Studio -> Slurm draft dialog.

Collects draft inputs, runs the pure ``build_slurm_draft`` facade and shows the
generated script read-only. The only side effect is the explicit hand-off, which
opens the draft in the existing remote editor for review. This module never
submits, uploads or contacts a host.
"""

from __future__ import annotations

from dataclasses import MISSING, fields
import re
from pathlib import Path, PurePosixPath

from hpc_gui.core.i18n import t
from hpc_gui.journal_studio.slurm_draft import SlurmDraft, build_slurm_draft
from hpc_gui.journal_studio.slurm_draft_inputs import SlurmDraftError, SlurmDraftRequest


_JOB_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,62}")
_DEFAULT_JOB_NAME = "journal_studio"
_DEFAULTS = {f.name: f.default for f in fields(SlurmDraftRequest) if f.default is not MISSING}
_FIELDS = (
    ("partition", "journal_studio.slurm_partition"),
    ("account", "journal_studio.slurm_account"),
    ("job_name", "journal_studio.slurm_job_name"),
    ("cpus_per_task", "journal_studio.slurm_cpus"),
    ("walltime", "journal_studio.slurm_walltime"),
    ("fluent_version", "journal_studio.slurm_fluent_version"),
    ("dimension", "journal_studio.slurm_dimension"),
    ("precision", "journal_studio.slurm_precision"),
    ("workdir", "journal_studio.slurm_workdir"),
    ("journal_path", "journal_studio.slurm_journal_path"),
)


def prefill_values(document, profile) -> dict[str, str]:
    """Best-effort starting values; every field stays editable and is re-validated."""
    profile = profile if isinstance(profile, dict) else {}
    path = str(document.path or "")
    if document.remote:
        remote = PurePosixPath(path)
        workdir, journal = str(remote.parent), remote.name
    else:
        workdir, journal = "", Path(path).name
    stem = Path(path).stem
    values = {name: str(value) for name, value in _DEFAULTS.items()}
    values.update(
        partition=str(profile.get("partition") or ""),
        account=str(profile.get("account") or ""),
        job_name=stem if _JOB_NAME_RE.fullmatch(stem) else _DEFAULT_JOB_NAME,
        workdir=workdir,
        journal_path=journal,
    )
    return values


def open_draft_in_editor(session_state, script_path: str, script_text: str) -> bool:
    """Open the reviewed draft in the existing remote editor; the user saves and submits there."""
    manager = session_state.get("editor_manager")
    if manager is None:
        return False
    manager.open_new_window(script_path, script_text, is_local=False)
    return True


class SlurmDraftDialog:
    def __init__(self, parent, document, profile, on_handoff):
        import wx

        self.wx = wx
        self.document = document
        self.on_handoff = on_handoff
        self.draft: SlurmDraft | None = None
        self.handed_off = False
        self.dialog = wx.Dialog(parent, title=t("journal_studio.slurm_dialog_title"), size=(680, 640), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        values = prefill_values(document, profile)
        self.fields: dict[str, wx.TextCtrl] = {}
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1, 1)
        for name, label_key in _FIELDS:
            grid.Add(wx.StaticText(self.dialog, label=t(label_key)), 0, wx.ALIGN_CENTER_VERTICAL)
            self.fields[name] = wx.TextCtrl(self.dialog, value=values.get(name, ""))
            grid.Add(self.fields[name], 1, wx.EXPAND)
        self.errors = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 70))
        self.script = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP, size=(-1, 220))
        self.status = wx.StaticText(self.dialog, label="")
        self.btn_generate = wx.Button(self.dialog, label=t("journal_studio.slurm_generate"))
        self.btn_handoff = wx.Button(self.dialog, label=t("journal_studio.slurm_handoff"))
        self.btn_handoff.Enable(False)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for button in (self.btn_generate, self.btn_handoff, wx.Button(self.dialog, id=wx.ID_CANCEL)):
            buttons.Add(button, 0, wx.ALL, 4)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        root.Add(self.errors, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(wx.StaticText(self.dialog, label=t("journal_studio.slurm_script_heading")), 0, wx.LEFT | wx.TOP, 8)
        root.Add(self.script, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(self.status, 0, wx.LEFT, 8)
        root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.dialog.SetSizer(root)
        self.btn_generate.Bind(wx.EVT_BUTTON, lambda _event: self.generate())
        self.btn_handoff.Bind(wx.EVT_BUTTON, lambda _event: self.hand_off())

    def request(self) -> SlurmDraftRequest:
        return SlurmDraftRequest(**{name: ctrl.GetValue() for name, ctrl in self.fields.items()})

    def generate(self) -> SlurmDraft | None:
        if self.handed_off:
            return self.draft
        try:
            draft = build_slurm_draft(self.document, self.request())
        except SlurmDraftError as error:
            self.draft = None
            self.btn_handoff.Enable(False)
            self.script.SetValue("")
            self._show_errors(error.errors)
            return None
        self.draft = draft
        self._show_errors(())
        self.script.SetValue("\n".join((draft.script_text, *draft.notes)))
        self.btn_handoff.Enable(True)
        self.status.SetLabel("")
        return draft

    def hand_off(self) -> bool:
        if self.draft is None or self.handed_off:
            return False
        self.handed_off = True
        self.btn_handoff.Enable(False)
        self.btn_generate.Enable(False)
        opened = bool(self.on_handoff(self.draft.script_path, self.draft.script_text))
        if opened:
            self.status.SetLabel(t("journal_studio.slurm_handed_off"))
        else:
            self.handed_off = False
            self.btn_handoff.Enable(True)
            self.btn_generate.Enable(True)
            self.status.SetLabel(t("journal_studio.slurm_handoff_unavailable"))
        return opened

    def show_modal(self) -> None:
        try:
            self.dialog.ShowModal()
        finally:
            self.dialog.Destroy()

    def _show_errors(self, errors) -> None:
        lines = [t("journal_studio.slurm_errors"), *(f"- {error}" for error in errors)] if errors else []
        self.errors.SetValue("\n".join(lines))
