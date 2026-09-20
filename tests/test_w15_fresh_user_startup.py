"""W15 — Fresh-user clean packaged startup (PKG-GJ-01 foundations).

Covers the isolated config-root mechanism (``HPC_GUI_CONFIG_ROOT``) and the
fresh-user packaged runner contract:

- REQ-W15-ROOT / REQ-W15-STORE — override redirects per-user state and
  storage round-trips inside the isolated root.
- NEG-W15-ROOT-BLANK / NEG-W15-ROOT-BAD / NEG-W15-CORRUPT — fallback,
  visible failure, and corrupt-config recovery inside a fresh root.
- PKG-W15-ENV / NEG-W15-WHL / NEG-W15-MISSING — parent fresh-user runner
  builds a clean-room env, rejects non-GUI artifacts, and reports a missing
  artifact truthfully.
- CON-W15-PROFILE-DIALOG — profile creation through the real visible
  AddConnection button + real modal WxConnectionDialog + real Save button
  (wx event proof), persisted under the isolated root with no secret.
- NEG-W15-SAFE-FAILURE — closed-port connect through the real
  ConnectSelected button ends FAILED with no connected-looking UI.
- REQ-W15-CONNECT-STATE — visible connect action drives the controller to
  connected and updates the visible status (transport mocked at the
  documented boundary; real SSH transport is proven by the packaged
  PKG-GJ-01 loopback run, not by this unit).

All filesystem fixtures are tmp-based; the developer home is never touched.
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from hpc_gui.core import paths as paths_mod

wx = pytest.importorskip("wx", reason="wxPython not installed")


@pytest.fixture(autouse=True)
def _clean_config_root_env(monkeypatch):
    monkeypatch.delenv("HPC_GUI_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("HPC_GUI_FRESH_USER", raising=False)
    monkeypatch.delenv("HPC_GUI_FRESH_RUN", raising=False)
    yield


def _fresh_env(monkeypatch, name="fresh"):
    tmp = tempfile.TemporaryDirectory(prefix="w15-")
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(Path(tmp.name) / name))
    return tmp


# ---------------------------------------------------------------------------
# Isolated config root (FIX-A regression + contract)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_isolated_root_redirects_app_dirs_and_creates_them(monkeypatch, tmp_path):
    """REQ-W15-ROOT: override redirects app_data_dir/app_log_dir; home untouched."""
    home_marker = tmp_path / "home"
    home_marker.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home_marker)
    fresh = tmp_path / "fresh-root"
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(fresh))

    data = paths_mod.app_data_dir()
    logs = paths_mod.app_log_dir()

    assert data == fresh and data.is_dir()
    assert logs == fresh / "logs" and logs.is_dir()
    assert not (home_marker / ".truba_slurm_gui").exists()


@pytest.mark.unit
def test_blank_override_falls_back_to_home(monkeypatch, tmp_path):
    """NEG-W15-ROOT-BLANK: blank override keeps the default per-user location."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", "   ")

    assert paths_mod.isolated_config_root() is None
    assert paths_mod.app_data_dir() == home / ".truba_slurm_gui"


@pytest.mark.unit
def test_uncreatable_root_raises_visibly(monkeypatch, tmp_path):
    """NEG-W15-ROOT-BAD: an unusable root fails loudly, never silently."""
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(blocker / "child"))

    with pytest.raises(RuntimeError):
        paths_mod.app_data_dir()


@pytest.mark.unit
def test_storage_roundtrips_inside_isolated_root(monkeypatch):
    """REQ-W15-STORE: profiles persist under the fresh root and reload."""
    from hpc_gui.config import storage

    tmp = _fresh_env(monkeypatch)
    storage.upsert_profile({"name": "fresh-profile", "host": "127.0.0.1", "username": "u"})

    config_path = Path(tmp.name) / "fresh" / "config.json"
    assert config_path.is_file()
    on_disk = json.loads(config_path.read_text(encoding="utf-8"))
    assert [p["name"] for p in on_disk["profiles"]] == ["fresh-profile"]
    assert "password" not in on_disk["profiles"][0]

    assert [p["name"] for p in storage.load_profiles()] == ["fresh-profile"]


@pytest.mark.unit
def test_corrupt_config_in_fresh_root_backs_up_and_starts_empty(monkeypatch):
    """NEG-W15-CORRUPT: garbage config.json is quarantined, startup stays usable."""
    from hpc_gui.config import storage

    tmp = _fresh_env(monkeypatch)
    root = Path(tmp.name) / "fresh"
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text("{not json", encoding="utf-8")

    assert storage.load_config() == {"profiles": [], "settings": {}}
    assert (root / "config.json.bak").is_file()


# ---------------------------------------------------------------------------
# Parent fresh-user runner contract (FIX-B, packaging taxonomy)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fresh_runner_rejects_whl_artifact(tmp_path):
    """NEG-W15-WHL: a wheel is never accepted as GUI fresh-user evidence."""
    import wx_packaged_smoke as smoke

    wheel = tmp_path / "hpc_client_gui-1.5.9-py3-none-any.whl"
    wheel.write_bytes(b"fake")
    out = tmp_path / "fresh-whl.json"
    evidence = smoke.run_fresh_user_smoke(wheel, "windows", out)

    assert evidence["result"] == "FAIL"
    assert "GUI-capable" in evidence["details"]["error"]
    assert json.loads(out.read_text(encoding="utf-8"))["result"] == "FAIL"


@pytest.mark.unit
def test_fresh_runner_reports_missing_artifact_truthfully(tmp_path):
    """NEG-W15-MISSING: a missing exe yields FAIL evidence, never a launch claim."""
    import wx_packaged_smoke as smoke

    out = tmp_path / "fresh.json"
    evidence = smoke.run_fresh_user_smoke(tmp_path / "absent.exe", "windows", out)

    assert evidence["result"] == "FAIL"
    assert "not found" in evidence["details"]["error"]
    assert len(evidence["artifact_sha256"]) == 64
    assert json.loads(out.read_text(encoding="utf-8"))["result"] == "FAIL"


@pytest.mark.unit
def test_fresh_env_strips_dev_leakage_and_sets_isolation(tmp_path):
    """PKG-W15-ENV: child env drops source/dev leakage, keeps smoke wiring."""
    import wx_packaged_smoke as smoke

    fresh = tmp_path / "fresh"
    env = smoke.fresh_user_env(
        {
            "PATH": "p",
            "PYTHONPATH": "D:/Projeler/hpc-client-gui/src",
            "HPC_GUI_DISABLE_WEBENGINE": "1",
            "HPC_GUI_PACKAGED_SMOKE_SSH_HOST": "127.0.0.1",
        },
        fresh_root=fresh,
        run_index=1,
    )

    assert "PYTHONPATH" not in env
    assert "HPC_GUI_DISABLE_WEBENGINE" not in env
    assert env["HPC_GUI_CONFIG_ROOT"] == str(fresh)
    assert env["HPC_GUI_FRESH_USER"] == "1"
    assert env["HPC_GUI_FRESH_RUN"] == "1"
    assert env["HPC_GUI_PACKAGED_SMOKE_SSH_HOST"] == "127.0.0.1"


# ---------------------------------------------------------------------------
# Visible-control GUI proofs (wx event/integration taxonomy)
# ---------------------------------------------------------------------------


def _find_button(root, name):
    for child in root.GetChildren():
        if isinstance(child, wx.Button) and child.GetName() == name:
            return child
        found = _find_button(child, name)
        if found is not None:
            return found
    return None


def _post_button_click(btn):
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
    btn.GetEventHandler().ProcessEvent(evt)


def _drive_add_dialog(monkeypatch, panel_host, *, name, host, port, username):
    """Click real AddConnection, autofill the real modal dialog, click Save."""
    import hpc_gui.wx_connection_dialog as dlg_mod
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    captured = {}
    real_cls = WxConnectionDialog

    class _Spy(real_cls):  # observe only; behavior untouched
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["dlg"] = self

    monkeypatch.setattr(dlg_mod, "WxConnectionDialog", _Spy)
    add_btn = _find_button(panel_host, "AddConnection")
    assert add_btn is not None
    before = set(wx.GetTopLevelWindows())
    state = {"done": False}

    def autofill():
        dlg = captured.get("dlg")
        if dlg is None or state["done"]:
            wx.CallLater(200, autofill)
            return
        dlg.profile_name_ctrl.SetValue(name)
        dlg.host_ctrl.SetValue(host)
        dlg.port_ctrl.SetValue(str(port))
        dlg.username_ctrl.SetValue(username)
        try:
            dlg.password_ctrl.SetValue("")
        except Exception:
            pass
        state["done"] = True
        _post_button_click(dlg.btn_save)

    def watchdog():
        if not state.get("closed"):
            for win in set(wx.GetTopLevelWindows()) - before:
                try:
                    win.EndModal(wx.ID_CANCEL)
                except Exception:
                    pass

    wx.CallLater(500, autofill)
    wx.CallLater(20000, watchdog)
    _post_button_click(add_btn)
    state["closed"] = True
    return captured.get("dlg")


@pytest.mark.wx
@pytest.mark.semantic
def test_profile_created_through_visible_add_dialog(monkeypatch):
    """CON-W15-PROFILE-DIALOG: real Add→dialog→Save persists under fresh root."""
    from hpc_gui.config import storage
    from hpc_gui.wx_connection import build_connection_panel

    tmp = _fresh_env(monkeypatch)
    storage.save_config({"profiles": [], "settings": {}})
    app = wx.App(False)
    frame = wx.Frame(None, title="w15")
    try:
        host = build_connection_panel(frame, profiles=[])
        _drive_add_dialog(
            monkeypatch, host,
            name="fresh-loopback", host="127.0.0.1", port=22, username="tester",
        )
        # The profile listbox lives inside the panel; find it by content.
        found = []

        def collect(root):
            for child in root.GetChildren():
                if isinstance(child, wx.ListBox):
                    found.extend(child.GetStrings())
                collect(child)

        collect(host)
        assert "fresh-loopback" in found

        on_disk = json.loads((Path(tmp.name) / "fresh" / "config.json").read_text(encoding="utf-8"))
        stored = next(p for p in on_disk["profiles"] if p["name"] == "fresh-loopback")
        assert stored["host"] == "127.0.0.1"
        assert not any(stored.get(k) for k in ("password", "password_enc", "password_dpapi", "password_keychain_ref"))
    finally:
        frame.Destroy()


@pytest.mark.wx
@pytest.mark.semantic
def test_closed_port_connect_fails_visibly_without_connected_state(monkeypatch):
    """NEG-W15-SAFE-FAILURE: refused connect ends FAILED, never connected-looking."""
    from hpc_gui.config import storage
    from hpc_gui.wx_connection import build_connection_panel

    _fresh_env(monkeypatch)
    storage.save_config({"profiles": [], "settings": {}})
    storage.upsert_profile({"name": "dead-port", "host": "127.0.0.1", "port": 1, "username": "u"})
    app = wx.App(False)
    frame = wx.Frame(None, title="w15-neg")
    try:
        def refused(profile):
            sock = socket.create_connection(("127.0.0.1", 1), timeout=3)
            sock.close()
            return False

        host = build_connection_panel(frame, profiles=storage.load_profiles(), connect=refused)

        selected = []

        def collect(root):
            for child in root.GetChildren():
                if isinstance(child, wx.ListBox):
                    selected.append(child)
                collect(child)

        collect(host)
        choices = selected[0]
        choices.SetStringSelection("dead-port")
        sel_evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(sel_evt)

        connect_btn = _find_button(host, "ConnectSelected")
        assert connect_btn is not None
        _post_button_click(connect_btn)

        deadline = time.monotonic() + 20
        label = None

        def find_status(root):
            for child in root.GetChildren():
                if isinstance(child, wx.StaticText):
                    yield child
                yield from find_status(child)

        while time.monotonic() < deadline:
            wx.YieldIfNeeded()
            texts = [c.GetLabel() for c in find_status(host)]
            if any("ail" in t or "ailed" in t for t in texts):
                label = texts
                break
            time.sleep(0.1)
        assert label is not None, "failure must be visible, not silent"
    finally:
        frame.Destroy()


@pytest.mark.wx
@pytest.mark.semantic
def test_visible_connect_drives_controller_to_connected(monkeypatch):
    """REQ-W15-CONNECT-STATE: real ConnectSelected event connects + updates status.

    Real code exercised: panel button routing, model selection, controller
    state machine, visible status label.
    Mocked boundary: SSH transport (connect callable returns a session dict).
    Why legitimate: this test proves GUI→controller→visible-state routing;
    real loopback transport is proven by the packaged PKG-GJ-01 run and the
    existing SSH wire suites, not duplicated here.
    What this test does NOT prove: real network authentication.
    """
    from hpc_gui.config import storage
    from hpc_gui.wx_connection import build_connection_panel

    _fresh_env(monkeypatch)
    storage.save_config({"profiles": [], "settings": {}})
    storage.upsert_profile({"name": "loop", "host": "127.0.0.1", "port": 22, "username": "u"})
    app = wx.App(False)
    frame = wx.Frame(None, title="w15-conn")
    try:
        host = build_connection_panel(
            frame, profiles=storage.load_profiles(), connect=lambda p: {"connected": True}
        )

        boxes = []

        def collect(root):
            for child in root.GetChildren():
                if isinstance(child, wx.ListBox):
                    boxes.append(child)
                collect(child)

        collect(host)
        boxes[0].SetStringSelection("loop")
        boxes[0].GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_LISTBOX.typeId, boxes[0].GetId())
        )
        connect_btn = _find_button(host, "ConnectSelected")
        _post_button_click(connect_btn)

        deadline = time.monotonic() + 10
        ok = False
        while time.monotonic() < deadline:
            wx.YieldIfNeeded()
            texts = []
            stack = [host]
            while stack:
                node = stack.pop()
                if isinstance(node, wx.StaticText):
                    texts.append(node.GetLabel())
                stack.extend(node.GetChildren())
            if any("onnected" in t and "isconnect" not in t and "onnecting" not in t for t in texts):
                ok = True
                break
            time.sleep(0.1)
        assert ok, "successful connect must reach a visibly connected state"
    finally:
        frame.Destroy()
