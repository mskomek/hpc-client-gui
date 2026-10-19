"""Stage indicator widgets and labels for the startup splash."""

from __future__ import annotations

from hpc_gui.core.i18n import t


STAGES = ("updates", "preferences", "helpers")
STAGE_LABELS = {
    "updates": "Updates",
    "preferences": "Preferences",
    "helpers": "Helpers",
}

STATE_PENDING = "pending"
STATE_ACTIVE = "active"
STATE_COMPLETE = "complete"
STATE_FAILED = "failed"


def _stage_icon(state: str) -> str:
    return {"pending": "○", "active": "●", "complete": "✓", "failed": "!"}.get(state, "○")


def create_stage_indicators(wx, panel):
    """Build the stage row and return its sizer and label controls."""
    stage_sizer = wx.BoxSizer(wx.HORIZONTAL)
    stage_controls = {}
    for stage_id in STAGES:
        key = f"splash.stage_{stage_id}"
        label = t(key) if t(key) != f"[{key}]" else STAGE_LABELS[stage_id]
        control = wx.StaticText(panel, label=f"{_stage_icon(STATE_PENDING)}  {label}")
        try:
            control.SetMinSize(wx.Size(110, -1))
        except Exception:
            pass
        stage_controls[stage_id] = control
        stage_sizer.Add(control, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    return stage_sizer, stage_controls


def refresh_stage_indicators(wx, controls, stages) -> None:
    """Update labels and emphasize the active startup stage."""
    for stage_id, control in controls.items():
        current = stages.get(stage_id, STATE_PENDING)
        key = f"splash.stage_{stage_id}"
        label = t(key) if t(key) != f"[{key}]" else STAGE_LABELS[stage_id]
        try:
            control.SetLabel(f"{_stage_icon(current)}  {label}")
            font = control.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD if current == STATE_ACTIVE else wx.FONTWEIGHT_NORMAL)
            control.SetFont(font)
        except Exception:
            pass
