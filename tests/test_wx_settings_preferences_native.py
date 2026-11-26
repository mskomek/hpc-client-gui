from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]


@pytest.fixture
def app():
    instance = wx.App.Get() or wx.App(False)
    yield instance


def _pump(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not predicate():
        app.Yield(True)
        time.sleep(0.01)
    assert predicate(), "wx event loop did not reach expected state"


def test_settings_apply_persists_global_preferences_and_graphics_reset(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    monkeypatch.setattr(storage, "load_settings", lambda: {
        "terminal_graphics_mode": "accelerated",
        "terminal_graphics_auto_compatibility": True,
    })
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    updates = []
    snapshots = []
    shown = []
    monkeypatch.setattr(storage, "update_settings", lambda patch: updates.append(dict(patch)) or dict(patch))
    monkeypatch.setattr(settings_model, "persist_model_snapshot", lambda snapshot: snapshots.append(snapshot))
    monkeypatch.setattr(storage, "set_transfer_checksum_verification_enabled", lambda _value: False)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: shown.append(args[0]) or wx.OK)

    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel())
    preferences = host._wx_settings_preference_controls
    preferences["jobs_outputs_refresh_interval_seconds"].SetValue(29)
    preferences["live_tracking_warning_interval_seconds"].SetValue(90)
    preferences["squeue_auto_refresh_enabled"].SetValue(False)
    ftp_choice, _ftp_values = preferences["ftp_transfer_type"]
    ftp_choice.SetSelection(2)
    follow_choice, _follow_values = preferences["sbatch_follow_mode"]
    follow_choice.SetSelection(0)
    graphics_choice, _graphics_values = preferences["terminal_graphics_mode"]
    graphics_choice.SetSelection(2)
    host._wx_settings_controls["reset_terminal_graphics"].Command(
        wx.CommandEvent(
            wx.wxEVT_BUTTON,
            host._wx_settings_controls["reset_terminal_graphics"].GetId(),
        )
    )
    host._wx_settings_controls["apply"].Command(
        wx.CommandEvent(wx.wxEVT_BUTTON, host._wx_settings_controls["apply"].GetId())
    )
    _pump(app, lambda: bool(shown))

    assert snapshots[0].global_settings["jobs_outputs_refresh_interval"] == 29
    assert updates[-1]["live_tracking_warning_interval_seconds"] == 90
    assert updates[-1]["squeue_auto_refresh_enabled"] is False
    assert updates[-1]["ftp_transfer_type"] == "ascii"
    assert updates[-1]["sbatch_follow_mode"] == "none"
    assert updates[-1]["terminal_graphics_mode"] == "auto"
    assert updates[-1]["terminal_graphics_auto_compatibility"] is False
    host.Destroy()
    frame.Destroy()


def test_settings_preferences_labels_follow_runtime_language(app, monkeypatch, tmp_path):
    import hpc_gui.config.storage as storage
    from hpc_gui.core.i18n import set_language, t
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    monkeypatch.setattr(storage, "load_settings", lambda: {})
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    monkeypatch.setattr("hpc_gui.core.i18n.app_data_dir", lambda: tmp_path)
    set_language("en")
    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel())
    choice, _values = host._wx_settings_preference_controls["terminal_graphics_mode"]
    set_language("tr")
    assert choice.GetString(0) == t("settings.terminal_graphics_mode_auto")
    assert host._wx_settings_controls["file_association_clear"].IsEnabled() is False
    host.Destroy()
    frame.Destroy()
    set_language("en")


def test_settings_remote_directory_cache_button_invalidates_wx_model(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    monkeypatch.setattr(storage, "load_settings", lambda: {})
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    invalidated = []
    shown = []
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: shown.append(args[0]) or wx.OK)
    state = {"_embedded_remote_files_panel": type("RemotePanel", (), {
        "_wx_remote_controls": {"invalidate_cache": lambda: invalidated.append(True)}
    })()}
    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel(), session_state=state)
    button = host._wx_settings_controls["clear_remote_cache"]
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
    assert invalidated == [True]
    assert shown
    host.Destroy()
    frame.Destroy()


def test_settings_profile_paths_are_applied_without_losing_profile_fields(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    profile = {
        "name": "lab",
        "system": {"scratch_dir": "/old/scratch", "home_dir": "/old/home", "partition": "gpu"},
        "plugin_settings": {"scheduler": "slurm"},
    }
    monkeypatch.setattr(storage, "load_settings", lambda: {})
    monkeypatch.setattr(storage, "load_profiles", lambda: [dict(profile)])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    monkeypatch.setattr(storage, "set_transfer_checksum_verification_enabled", lambda _value: False)
    monkeypatch.setattr(settings_model, "persist_model_snapshot", lambda _snapshot: None)
    writes = []
    monkeypatch.setattr(storage, "update_settings", lambda patch: writes.append(dict(patch)) or dict(patch))
    monkeypatch.setattr(storage, "upsert_profile", lambda value: writes.append(dict(value)))
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: wx.OK)
    state = {"session": {"connected": True, "profile_name": "lab", "profile": profile}}

    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel(), session_state=state)
    controls = host._wx_settings_preference_controls
    controls["profile_scratch_dir"].SetValue("/new/scratch")
    controls["profile_home_dir"].SetValue("/new/home")
    button = host._wx_settings_controls["apply"]
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
    _pump(app, lambda: len(writes) >= 2)

    updated = next(value for value in writes if value.get("name") == "lab")
    assert updated["system"] == {
        "scratch_dir": "/new/scratch", "home_dir": "/new/home", "partition": "gpu"
    }
    assert updated["plugin_settings"] == {"scheduler": "slurm"}
    host.Destroy()
    frame.Destroy()


def test_settings_cancel_does_not_persist_staged_preferences(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    monkeypatch.setattr(storage, "load_settings", lambda: {})
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    writes = []
    monkeypatch.setattr(storage, "update_settings", lambda patch: writes.append(dict(patch)) or dict(patch))
    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel())
    host._wx_settings_preference_controls["live_tracking_warning_interval_seconds"].SetValue(123)
    host._wx_settings_controls["close"].Command(
        wx.CommandEvent(wx.wxEVT_BUTTON, host._wx_settings_controls["close"].GetId())
    )
    app.Yield(True)
    assert writes == []
    frame.Destroy()
