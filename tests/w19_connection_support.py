"""W19 Connection/session lifecycle and profile switching.

REQ: HPC-W05-CONN-001..020, HPC-W05-RECON-001..007
TODO: HPC-W05-TODO-SHELL-NAV-001/002, HPC-W05-TODO-SHELL-TABS-001/002,
      HPC-W05-TODO-006, HPC-W02-TODO-002, HPC-W05-TODO-007
DEF: DEF-W19-001 (mid-connect Cancel), DEF-W19-002 (off-thread modal),
     DEF-W19-003 (stale transport-loss callback), DEF-W19-004 (no Disconnect
     control / dead-session reuse), DEF-W19-005 (NAV detached instead of
     embedded page).
CON: behavioral assertions on live controller/model/panel/shell objects.
NEG: cancel/reject/failure/transport-loss/stale-callback paths.
Mock boundary: transport (FakeSsh/fake connect_fn) and dialog chrome only;
controller/i18n/panel/shell/session-state are real.
"""

import time

import pytest

wx = pytest.importorskip("wx")
from hpc_gui.wx_connection import build_connection_panel


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class FakeSsh:
    def __init__(self):
        self.closed = 0
        self.sent = []
        self._wx_output_subscribers = []

    def close(self):
        self.closed += 1

    def send_shell_input(self, payload):
        self.sent.append(payload)

    def resize_shell_pty(self, columns, rows):
        pass


def _attached_ssh(panel):
    """Renderer-agnostic attached transport (TextCtrl vs WebView panel)."""
    ssh = getattr(panel, "_terminal_ssh", None)
    if ssh is not None:
        return ssh
    return getattr(panel, "_ssh", None)


def _send_path(panel):
    model = getattr(panel, "_terminal_model", None)
    if model is not None and getattr(model, "_send_input", None) is not None:
        return model._send_input
    return getattr(panel, "_send_input", None)


def _fake_session(name="lab", ssh=None):
    ssh = ssh if ssh is not None else FakeSsh()
    return {
        "connected": True,
        "ssh": ssh,
        "profile_name": name,
        "profile": {"name": name, "id": f"id-{name}"},
    }


def _pump(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            window.Close()
        except Exception:
            pass
    for _ in range(5):
        try:
            wx.Yield()
        except Exception:
            app.ProcessPendingEvents()
    for window in wx.GetTopLevelWindows():
        try:
            if not window.IsBeingDeleted():
                window.Destroy()
        except Exception:
            pass
    for _ in range(5):
        try:
            wx.Yield()
        except Exception:
            app.ProcessPendingEvents()
    # NOTE: no app.Destroy() here on purpose. Destroying the shared wx.App
    # while shell frames with WebView-backed terminal panels are still
    # draining their deferred deletes crashes the interpreter on shutdown
    # (0xC0000374) after an otherwise green run. Windows are closed and
    # destroyed above; the process exit reclaims the app.


def _profiles():
    return [{"name": "lab", "host": "127.0.0.1", "port": 2222, "username": "tester"}]


def _build_panel(wx_app, monkeypatch, *, connect=None, on_connected=None, on_disconnected=None):
    monkeypatch.setattr("hpc_gui.wx_connection.load_profiles", lambda: _profiles())
    messages = []
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: messages.append(a) or wx.ID_OK)
    frame = wx.Frame(None, title="w19")
    host = build_connection_panel(
        frame,
        profiles=_profiles(),
        connect=connect,
        on_connected=on_connected,
        on_disconnected=on_disconnected,
    )
    controls = host._wx_connection_controls
    model = host._wx_connection_model
    controls["choices"].SetSelection(0)
    model.select("lab")
    return frame, host, controls, model, messages
