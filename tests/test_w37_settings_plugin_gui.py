"""W37 plugin settings, migrations, and wx settings-view acceptance."""

from __future__ import annotations

import time
import pytest

from hpc_gui.config import storage
from hpc_gui.wx_settings import (
    build_model_from_storage,
    load_persisted_snapshot,
    plugin_settings_survive_absence,
)


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: config_path)
    return config_path

# UPD-060 / PLUGINSET-001/002 / UPD-074 absent-plugin safety (UPD-048)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_absent_plugin_settings_fall_back_to_defaults(tmp_path):
    spec = {"refresh_seconds": {"type": int, "default": 15}}
    assert plugin_settings_survive_absence(tmp_path, "org.w37.absent", spec) == {
        "refresh_seconds": 15
    }


@pytest.mark.contract
def test_w37_plugin_settings_namespaced_core_protected(tmp_path):
    from hpc_gui.plugins import settings as plugin_settings

    assert plugin_settings.namespaced_key("org.w37.demo", "refresh") == (
        "plugins.org.w37.demo.refresh"
    )
    cleaned, errors = plugin_settings.validate_plugin_settings(
        "org.w37.demo", {"squeue_command": "evil"}, {"squeue_command": {"type": str}}
    )
    assert errors  # core-key collision diagnosed...
    refused, refused_errors = plugin_settings.save_plugin_settings(
        tmp_path, "org.w37.demo", {"squeue_command": "evil"},
        {"squeue_command": {"type": str}},
    )
    assert refused == {} and refused_errors  # ...and fail-closed: nothing written
    merged, errors = plugin_settings.save_plugin_settings(
        tmp_path, "org.w37.demo", {"refresh": 5},
        {"refresh": {"type": int, "default": 10}},
    )
    assert errors == [] and merged == {"refresh": 5}
    # Reinstall/upgrade path: newer spec defaults merge over stored values.
    assert plugin_settings.load_plugin_settings(
        tmp_path, "org.w37.demo", {"refresh": {"type": int, "default": 10},
                                   "extra": {"type": bool, "default": True}}
    ) == {"refresh": 5, "extra": True}
    # Secrets never export (PROV-007 via W37 bridge owner).
    safe = plugin_settings.export_safe_settings(
        {"token": "abc", "refresh": 5}, {"token": {"type": str, "secret": True}}
    )
    assert safe == {"refresh": 5}


# ---------------------------------------------------------------------------
# MIGRATION-SETTINGS-001 / MIGRATION-QUOTA-001 / MIGRATION-TERMINAL-001
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_migration_global_settings_idempotent():
    cfg = {"settings": {"transfer_parallelism": 4},
           "profiles": [{"name": "a"}, {"name": "b", "transfer_parallelism": 7}]}
    assert storage.migrate_legacy_transfer_parallelism(cfg) is True
    by_name = {p["name"]: p for p in cfg["profiles"]}
    assert by_name["a"]["transfer_parallelism"] == 4
    assert by_name["b"]["transfer_parallelism"] == 7
    assert storage.migrate_legacy_transfer_parallelism(cfg) is False


@pytest.mark.contract
def test_w37_migration_quota_optional_legacy_bool_source_only(isolated_config):
    storage.update_settings({"focus_jobs_outputs_after_submission_enabled": False})
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_NONE
    storage.update_settings({"sbatch_follow_mode": storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED})
    storage.update_settings({"focus_jobs_outputs_after_submission_enabled": False})
    assert storage.get_sbatch_follow_mode() == storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED


@pytest.mark.contract
def test_w37_migration_terminal_scope_is_deliberate():
    # MIGRATION-TERMINAL-001: terminal history is intentionally outside V2
    # migration scope — no terminal-history migration exists by decision,
    # not by omission.
    import hpc_gui.config.storage as storage_module
    import inspect

    source = inspect.getsource(storage_module)
    assert "terminal_history" not in source
    assert "migrate_legacy_transfer_parallelism" in source


# ---------------------------------------------------------------------------
# ARCH-BOUNDARY-001 no duplicated settings logic in GUI handlers
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w37_settings_logic_lives_behind_services_not_handlers():
    import inspect

    import hpc_gui.wx_settings as wx_settings_module

    assert "plugins.settings" in inspect.getsource(
        wx_settings_module.plugin_settings_survive_absence
    )


# ---------------------------------------------------------------------------
# GUI FULL: real wx event -> model -> storage -> readback
# ---------------------------------------------------------------------------


def _pump(wx, seconds: float = 0.05) -> None:
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass
    time.sleep(seconds)
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass


def _wait_until(predicate, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            import wx as _wx

            try:
                _wx.YieldIfNeeded()
            except Exception:
                pass
        except Exception:
            pass
        if predicate():
            return True
        time.sleep(0.05)
    return bool(predicate())


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w37_wx_apply_event_persists_to_storage(isolated_config, monkeypatch):
    """GUI FULL: checkbox event -> Apply click -> config.json -> readback."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_settings_view import build_settings_panel

    storage.set_transfer_checksum_verification_enabled(False)
    storage.set_remote_directory_cache_enabled(True)
    calls = {"ok": 0}
    monkeypatch.setattr(
        wx, "MessageBox", lambda *args, **kwargs: calls.__setitem__("ok", 1) or 0
    )
    app = wx.App.Get() or wx.App(False)
    assert app is wx.GetApp()
    frame = wx.Frame(None, title="w37-apply-probe")
    try:
        model = build_model_from_storage()
        panel = build_settings_panel(frame, model)
        controls = panel._wx_settings_controls
        assert controls["checksum"].GetValue() is False
        controls["checksum"].SetValue(True)
        click = wx.CommandEvent(wx.EVT_BUTTON.typeId, controls["apply"].GetId())
        controls["apply"].GetEventHandler().ProcessEvent(click)
        ok = _wait_until(
            lambda: storage.get_transfer_checksum_verification_enabled() is True,
            timeout=8.0,
        )
        assert ok, "Apply event never persisted transfer_checksum to storage"
        for _ in range(5):
            _pump(wx)
        assert calls["ok"] == 1  # success dialog only on the persisted path
        reopened = load_persisted_snapshot()
        assert reopened.global_settings["transfer_checksum"] is True
        try:
            panel.Destroy()
        except Exception:
            pass
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w37_wx_failed_persist_shows_error_never_false_ok(
    isolated_config, monkeypatch
):
    """GUI FULL negative: write failure -> visible error, no OK dialog."""
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_settings_view import build_settings_panel

    from unittest.mock import patch as mock_patch

    with mock_patch.object(
        storage, "save_config", side_effect=OSError("read-only location")
    ):
        seen = {"ok": 0, "error": []}
        monkeypatch.setattr(
            wx, "MessageBox", lambda *args, **kwargs: seen.__setitem__("ok", 1) or 0
        )
        import hpc_gui.core.wx_errors as wx_errors_module

        monkeypatch.setattr(
            wx_errors_module, "report_wx_action_error",
            lambda *args, **kwargs: seen["error"].append(kwargs.get("exc", args)),
        )
        app = wx.App.Get() or wx.App(False)
        assert app is wx.GetApp()
        frame = wx.Frame(None, title="w37-apply-fail-probe")
        try:
            model = build_model_from_storage()
            panel = build_settings_panel(frame, model)
            controls = panel._wx_settings_controls
            click = wx.CommandEvent(wx.EVT_BUTTON.typeId, controls["apply"].GetId())
            controls["apply"].GetEventHandler().ProcessEvent(click)
            ok = _wait_until(lambda: seen["ok"] == 1 or seen["error"], timeout=8.0)
            assert ok, "neither success nor error surfaced"
            assert seen["ok"] == 0, "false-success OK shown despite failed write"
            assert seen["error"], "persistence failure must be visible and attributable"
            try:
                panel.Destroy()
            except Exception:
                pass
        finally:
            try:
                frame.Destroy()
            except Exception:
                pass
