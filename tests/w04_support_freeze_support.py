from __future__ import annotations

import pathlib



import types

import pytest

wx = pytest.importorskip("wx")


FREEZE_MD = pathlib.Path("artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md")

CLOSED_VOCABULARY = frozenset(
    {
        "SUPPORTED",
        "EXPERIMENTAL",
        "REQUIRES_EXTERNAL_VALIDATION",
        "HIDDEN",
        "UNSUPPORTED",
        "DEPRECATED",
        "NOT-IN-V2",
    }
)

FROZEN_COUNTS = {
    "SUPPORTED": 24,
    "EXPERIMENTAL": 17,
    "REQUIRES_EXTERNAL_VALIDATION": 11,
    "DEPRECATED": 2,
    "NOT-IN-V2": 2,
    "HIDDEN": 0,
    "UNSUPPORTED": 0,
}

REQUIRED_COLUMNS = [
    "ID",
    "Surface",
    "Action",
    "UI owner",
    "Service/provider",
    "Config",
    "Implementation owner",
    "Verification owner Wave",
    "Required evidence class",
    "Current evidence class",
    "Support disposition",
    "Open gap",
    "Evidence IDs",
]

def _close_shell(frame):
    """Controlled teardown: Close + yields + conditional Destroy (W02 pattern:
    an abrupt Destroy() of the full shell frame corrupts the heap)."""
    try:
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()

class _MessageBoxCapture:
    """Stand-in for ``wx.MessageBox`` that records instead of blocking."""

    def __init__(self, monkeypatch, result=None):
        self.calls = []
        self.result = wx.OK if result is None else result
        monkeypatch.setattr(wx, "MessageBox", self)

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result

    @property
    def texts(self):
        return [args[0] for args, _ in self.calls]

def _auto_cancel_native_selectors(monkeypatch):
    """Auto-cancel native file/dir selectors at the OS-modal boundary.

    ``wx.FileDialog`` / ``wx.DirDialog`` ``ShowModal()`` runs a native modal
    loop that cannot be driven headlessly and never terminates without a user
    (DEF-W04-002). The stand-in records each invocation and returns
    ``wx.ID_CANCEL`` so no transfer starts; real button events, real panels
    and the real ``run_action`` routing under test are untouched.
    """
    calls = []

    def _cancel_factory(*args, **kwargs):
        calls.append((args, kwargs))
        dialog = types.SimpleNamespace()
        dialog.ShowModal = lambda: wx.ID_CANCEL
        dialog.Destroy = lambda: True
        dialog.GetPaths = lambda: []
        dialog.GetPath = lambda: ""
        return dialog

    monkeypatch.setattr(wx, "FileDialog", _cancel_factory)
    monkeypatch.setattr(wx, "DirDialog", _cancel_factory)
    return calls

def _parse_freeze_matrix():
    """Parse the frozen-matrix section only (excludes verdict/findings tables)."""
    text = FREEZE_MD.read_text(encoding="utf-8")
    section = text.split("## Frozen matrix", 1)[1].split("## Exact freeze totals", 1)[0]
    header = None
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] == "ID":
            header = cells
            continue
        if line.startswith("| ---") or not cells[0].startswith("`"):
            continue
        assert len(cells) == len(header) == 14, f"row has {len(cells)} cells: {cells[0]}"
        rows.append(dict(zip(header, cells)))
    return header, rows

def _menu_labels(menu):
    """Recursively collect visible labels of a wx.Menu (real widget state)."""
    labels = []
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        sub = item.GetSubMenu()
        if sub is not None:
            labels.append(item.GetItemLabelText())
            labels.extend(_menu_labels(sub))
        else:
            labels.append(item.GetItemLabelText())
    return labels

def _shell_menu_labels(frame):
    menubar = frame.GetMenuBar()
    labels = []
    for index in range(menubar.GetMenuCount()):
        labels.extend(_menu_labels(menubar.GetMenu(index)))
    return labels

def _fire_menu(frame, item):
    frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
    wx.Yield()

def _fake_plugin(plugin_id="w04-fake", capabilities=()):
    manifest = types.SimpleNamespace(id=plugin_id, capabilities=tuple(capabilities))
    return types.SimpleNamespace(manifest=manifest)

def _collect_about_labels():
    """Build the real About dialog with the modal loop intercepted (real
    construction + real labels, no blocking event loop)."""
    import hpc_gui.wx_about as about_view
    from hpc_gui import __version__

    seen = {}

    def _fake_show_modal(self):
        texts = []
        buttons = []

        def _walk(window):
            for child in window.GetChildren():
                if isinstance(child, wx.StaticText):
                    texts.append(child.GetLabel())
                elif isinstance(child, wx.Button):
                    buttons.append(child.GetLabel())
                _walk(child)

        _walk(self)
        seen["texts"] = texts
        seen["buttons"] = buttons
        # No modal loop is running under interception, so EndModal would
        # assert; returning ID_OK models the Close-button dismissal.
        return wx.ID_OK

    original = wx.Dialog.ShowModal
    wx.Dialog.ShowModal = _fake_show_modal
    try:
        assert about_view.show_about(None) == wx.ID_OK
    finally:
        wx.Dialog.ShowModal = original
    assert seen, "ShowModal interception must observe the real dialog"
    return seen, __version__

def _collect_about_labels_with(show_fn):
    seen = {}

    def _fake_show_modal(self):
        seen["observed"] = True
        self.EndModal(wx.ID_OK)
        return wx.ID_OK

    original = wx.Dialog.ShowModal
    wx.Dialog.ShowModal = _fake_show_modal
    try:
        show_fn(None)
    finally:
        wx.Dialog.ShowModal = original
    assert seen.get("observed"), "legacy MessageBox impl builds no dialog: contract fails"


__all__ = [name for name in globals() if not name.startswith("__")]
