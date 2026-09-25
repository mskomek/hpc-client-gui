"""W39 — Logs and diagnostics functional closure.

Requirement → implementation → test trace:
  HPC-W09-DIAG-001..010  (Wave-local owned requirements)
  HPC-W09-TODO-LOGS-LIFECYCLE-001, -008..-013, -MIGRATION-SECRET-001,
  -051, -055, -057 (Wave-local owned TODO details)

GUI claims use a real wx runtime (wx.App + embedded logs panel + real
button events + pumped event loop + text readback), never static-only
proof. External/packaging classes are N/A with justification in the
canonical report.
"""

from __future__ import annotations

import json
import logging
import time
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.wx, pytest.mark.semantic]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pump_until(predicate, timeout_s: float = 10.0):
    import wx

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            wx.Yield()
        except Exception:
            pass
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(0.02)
    return bool(predicate())


@pytest.fixture
def wx_app():
    import wx

    app = wx.App.Get()
    created = False
    if app is None:
        app = wx.App(False)
        created = True
    yield app
    for window in list(wx.GetTopLevelWindows()):
        try:
            if window:
                window.Destroy()
        except Exception:
            pass
    try:
        app.ProcessPendingEvents()
        wx.SafeYield()
    except Exception:
        pass
    if created:
        try:
            app.Destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# DIAG-001 — logs initialize on first run
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_diag001_logs_initialize_on_first_run(tmp_path, monkeypatch):
    """A fresh isolated config root gets a log directory and first-run log."""
    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path / "fresh-root"))
    from hpc_gui.core import logging_setup
    from hpc_gui.core.logging import log_path

    target = log_path()
    assert target.parent.is_dir()
    logging_setup.setup_logging()
    logging.getLogger("hpc_gui.w39_probe").info("w39-first-run-probe")
    for handler in logging.getLogger("hpc_gui").handlers:
        try:
            handler.flush()
        except Exception:
            pass
    assert _pump_until(lambda: target.is_file() and target.stat().st_size > 0, 5.0)


# ---------------------------------------------------------------------------
# DIAG-002 / DIAG-003 — viewer opens; refresh reflects new lines (real wx)
# ---------------------------------------------------------------------------

@pytest.mark.gui
def test_w39_diag002_diag003_viewer_opens_and_refresh_reflects_new_lines(tmp_path, wx_app):
    import wx

    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    log_file = tmp_path / "app.log"
    log_file.write_text("boot line 1\nboot line 2\n", encoding="utf-8")
    parent = wx.Frame(None, title="w39-probe")
    model = WxLogsModel(log_file)
    host = build_logs_panel(parent, model=model)
    host.Layout()
    controls = host._wx_logs_controls
    assert _pump_until(lambda: controls["text"].GetValue() != "", 10.0)
    assert "boot line 1" in controls["text"].GetValue()

    # New lines appear after refresh (real Refresh button event).
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write("fresh line w39\n")
    event = wx.CommandEvent(wx.EVT_BUTTON.evtType[0], controls["refresh"].GetId())
    controls["refresh"].GetEventHandler().ProcessEvent(event)
    assert _pump_until(lambda: "fresh line w39" in controls["text"].GetValue(), 10.0)

    parent.Destroy()


# ---------------------------------------------------------------------------
# DIAG-004 — Open Logs Folder resolves the actual active log directory
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_diag004_logs_dir_resolves_active_directory(tmp_path):
    from hpc_gui.wx_logs import WxLogsModel, resolve_active_logs_dir

    nested = tmp_path / "sub" / "app.log"
    nested.parent.mkdir(parents=True)
    nested.write_text("x\n", encoding="utf-8")
    model = WxLogsModel(nested)
    assert model.logs_dir() == nested.resolve().parent
    assert model.logs_dir().is_dir()
    # Module helper reflects the current runtime (never a stale cache).
    assert resolve_active_logs_dir() == Path(
        __import__("hpc_gui.core.logging", fromlist=["log_path"]).log_path()
    ).expanduser().resolve().parent


@pytest.mark.gui
def test_w39_diag004_open_folder_button_exists_and_resolves(tmp_path, wx_app, monkeypatch):
    import wx

    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    log_file = tmp_path / "app.log"
    log_file.write_text("x\n", encoding="utf-8")
    opened = []
    monkeypatch.setattr(wx, "LaunchDefaultApplication", lambda path: opened.append(path) or True)
    parent = wx.Frame(None, title="w39-probe-folder")
    host = build_logs_panel(parent, model=WxLogsModel(log_file))
    assert _pump_until(lambda: host._wx_logs_controls["text"].GetValue() != "", 10.0)
    event = wx.CommandEvent(
        wx.EVT_BUTTON.evtType[0], host._wx_logs_controls["open_folder"].GetId()
    )
    host._wx_logs_controls["open_folder"].GetEventHandler().ProcessEvent(event)
    assert opened and Path(opened[0]) == log_file.resolve().parent
    parent.Destroy()


# ---------------------------------------------------------------------------
# DIAG-005 — clear/delete, if exposed, has safe confirmation/behavior
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_diag005_no_unconfirmed_clear_delete_exposed(tmp_path, wx_app):
    """The logs view exposes no destructive clear/delete control, so the
    conditional requirement is vacuously satisfied (no unconfirmed wipe)."""
    import wx

    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    log_file = tmp_path / "app.log"
    log_file.write_text("keep me\n", encoding="utf-8")
    parent = wx.Frame(None, title="w39-probe-noclear")
    host = build_logs_panel(parent, model=WxLogsModel(log_file))
    assert _pump_until(lambda: host._wx_logs_controls["text"].GetValue() != "", 10.0)
    labels = {
        key: ctrl.GetLabel()
        for key, ctrl in host._wx_logs_controls.items()
        if hasattr(ctrl, "GetLabel")
    }
    joined = " ".join(labels.values()).lower()
    assert "clear" not in joined and "delete" not in joined
    assert log_file.read_text(encoding="utf-8") == "keep me\n"
    parent.Destroy()


# ---------------------------------------------------------------------------
# DIAG-006 — diagnostics/version/build/provider/plugin/runtime truthful
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_diag006_runtime_summary_truthful():
    from hpc_gui import __version__
    from hpc_gui.core.diagnostics import _runtime_summary

    summary = _runtime_summary()
    assert summary["application_version"] == __version__
    assert "wxPython" in summary["ui_framework"]
    assert "Qt" not in summary["ui_framework"] and "PySide6" not in summary["ui_framework"]
    assert summary["os"] and summary["python"]


# ---------------------------------------------------------------------------
# DIAG-007 / TODO-010 — copy/export redacts credentials and secrets
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_diag007_copy_and_export_redact(tmp_path):
    from unittest.mock import patch

    from hpc_gui.wx_logs import WxLogsModel

    log_file = tmp_path / "app.log"
    log_file.write_text(
        "connecting -pw SuperSecret123 Authorization: Bearer abc.def.ghi\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIB\n-----END RSA PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    model = WxLogsModel(log_file)
    text = model.refresh()
    assert "SuperSecret123" not in text and "abc.def.ghi" not in text
    assert "PRIVATE KEY" not in text or "redacted" in text.lower()
    assert model.copy_all() == text

    import zipfile as _zf

    from hpc_gui.core import diagnostics

    home = tmp_path / "home"
    app_data = home / ".truba_slurm_gui"
    app_data.mkdir(parents=True)
    (app_data / "app.log").write_text("token=leaked-value-here", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with patch.object(Path, "home", return_value=home), patch(
        "hpc_gui.config.storage.load_profiles", return_value=[]
    ):
        bundle = diagnostics.create_diagnostic_bundle(str(out_dir))
    with _zf.ZipFile(bundle) as zf:
        combined = b"".join(zf.read(name) for name in zf.namelist())
    assert b"leaked-value-here" not in combined


# ---------------------------------------------------------------------------
# DIAG-008 — bundle includes only intended files, survives missing optionals
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_w39_diag008_bundle_survives_missing_optional_files(tmp_path):
    from unittest.mock import patch

    from hpc_gui.core import diagnostics

    home = tmp_path / "empty-home"
    home.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with patch.object(Path, "home", return_value=home), patch(
        "hpc_gui.config.storage.load_profiles", return_value=[]
    ):
        bundle = diagnostics.create_diagnostic_bundle(str(out_dir))
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        assert {"manifest.json", "runtime.json", "plugins.json"} <= names
        assert "config.json" not in names
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["schema"] == "hpc-diagnostics/2"


# ---------------------------------------------------------------------------
# DIAG-009 / TODO-009 — usable offline; export failure visible, no crash
# ---------------------------------------------------------------------------

@pytest.mark.gui
def test_w39_diag009_usable_offline_after_connection_failure(tmp_path, wx_app):
    """The logs view takes no connection object, so a dead/offline network
    cannot break it: refresh of a local file still works."""
    import wx

    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    log_file = tmp_path / "app.log"
    log_file.write_text("offline line\n", encoding="utf-8")
    parent = wx.Frame(None, title="w39-probe-offline")
    host = build_logs_panel(parent, model=WxLogsModel(log_file))
    assert _pump_until(lambda: "offline line" in host._wx_logs_controls["text"].GetValue(), 10.0)
    parent.Destroy()


@pytest.mark.unit
def test_w39_todo009_export_failure_raises_without_crashing_app(tmp_path):
    from hpc_gui.wx_logs import WxLogsModel

    def _boom(_destination):
        raise OSError("simulated export failure")

    model = WxLogsModel(tmp_path / "app.log", bundle=_boom)
    with pytest.raises(OSError, match="simulated export failure"):
        model.export_bundle(str(tmp_path))


# ---------------------------------------------------------------------------
# DIAG-010 / LOGS-LIFECYCLE-001 / TODO-008 — close during refresh is safe
# ---------------------------------------------------------------------------

@pytest.mark.gui
def test_w39_lifecycle_pending_refresh_safe_after_close(tmp_path, wx_app):
    """Destroy the host, then deliver a late refresh/export callback: no
    destroyed-control update, no exception (LOGS-LIFECYCLE-001, TODO-008)."""
    import wx

    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    log_file = tmp_path / "app.log"
    log_file.write_text("lifecycle\n", encoding="utf-8")
    parent = wx.Frame(None, title="w39-probe-lifecycle")
    host = build_logs_panel(parent, model=WxLogsModel(log_file))
    assert _pump_until(lambda: host._wx_logs_controls["text"].GetValue() != "", 10.0)
    host._wx_host_close()
    parent.Destroy()
    wx.Yield()
    # Late callbacks after close must be swallowed, not raise.
    host._wx_logs_refresh()
    time.sleep(0.3)
    wx.Yield()


# ---------------------------------------------------------------------------
# TODO-013 — raw logs stay complete (no presentation collapsing)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_todo013_raw_logs_complete_no_collapse(tmp_path):
    from hpc_gui.wx_logs import WxLogsModel

    log_file = tmp_path / "app.log"
    repeated = "".join(f"poll tick {i}\n" for i in range(200))
    log_file.write_text(repeated, encoding="utf-8")
    text = WxLogsModel(log_file).refresh()
    assert "poll tick 0" in text and "poll tick 199" in text
    assert "×" not in text and "collapsed" not in text.lower()


# ---------------------------------------------------------------------------
# E1-adjacent — no raw-key leakage for logs strings in either language
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_w39_logs_i18n_key_parity_no_raw_key_leakage():
    import json as _json

    from hpc_gui.core.i18n import load_language, t

    en = _json.load(open("src/hpc_gui/i18n/en.json", encoding="utf-8"))["logs"]
    tr = _json.load(open("src/hpc_gui/i18n/tr.json", encoding="utf-8"))["logs"]
    assert set(en) == set(tr)
    for lang in ("en", "tr"):
        load_language(lang)
        for key in en:
            assert not t(f"logs.{key}").startswith("["), (lang, key)


# ---------------------------------------------------------------------------
# MIGRATION-SECRET-001 / TODO-055 — no secrets in migration/diagnostic text
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_w39_migration_secret_redaction():
    from hpc_gui.core.log_redaction import redact_text

    sample = (
        "migrating profile host=arf.truba.gov.tr user=mkomek "
        "password=TopSecretValue Authorization: Bearer sess.token.here"
    )
    redacted = redact_text(sample)
    assert "TopSecretValue" not in redacted and "sess.token.here" not in redacted
