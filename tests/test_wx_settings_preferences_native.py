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
    preflight = []
    monkeypatch.setattr(storage, "set_upload_preflight_confirmation_enabled", lambda value: preflight.append(value) or value)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: shown.append(args[0]) or wx.OK)

    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel())
    preferences = host._wx_settings_preference_controls
    preferences["jobs_outputs_refresh_interval_seconds"].SetValue(29)
    preferences["live_tracking_warning_interval_seconds"].SetValue(90)
    preferences["squeue_auto_refresh_enabled"].SetValue(False)
    ftp_choice, ftp_values = preferences["ftp_transfer_type"]
    assert ftp_values == ("auto", "binary", "ascii")
    assert ftp_choice.GetSelection() == 0
    ftp_choice.SetSelection(2)
    follow_choice, follow_values = preferences["sbatch_follow_mode"]
    assert set(follow_values) == {
        "none", "outputs_tab", "new_tabs_split", "new_window_combined", "new_windows_split"
    }
    follow_choice.SetSelection(0)
    graphics_choice, _graphics_values = preferences["terminal_graphics_mode"]
    graphics_choice.SetSelection(2)
    host._wx_settings_controls["upload_preflight"].SetValue(False)
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
    assert snapshots[0].global_settings["upload_preflight_confirmation"] is False
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
    preflight = []
    monkeypatch.setattr(storage, "set_upload_preflight_confirmation_enabled", lambda value: preflight.append(value) or value)
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


def test_settings_profile_paths_require_profile_and_reset_to_generic_defaults(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view
    from hpc_gui.config.system_profile import hpc_default_remote_paths

    monkeypatch.setattr(storage, "load_settings", lambda: {})
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    frame = wx.Frame(None)
    empty = view.build_settings_panel(frame, settings_model.WxSettingsModel())
    controls = empty._wx_settings_preference_controls
    assert not controls["profile_scratch_dir"].IsEnabled()
    assert not controls["profile_home_dir"].IsEnabled()
    assert not empty._wx_settings_controls["reset_remote_defaults"].IsEnabled()
    empty.Destroy()

    profile = {
        "name": "lab",
        "system": {"scratch_dir": "/custom/scratch", "home_dir": "/custom/home"},
    }
    writes = []
    monkeypatch.setattr(storage, "load_profiles", lambda: [dict(profile)])
    monkeypatch.setattr(storage, "get_last_profile_name", lambda: "lab")
    monkeypatch.setattr(storage, "upsert_profile", lambda value: writes.append(dict(value)))
    monkeypatch.setattr(storage, "set_transfer_checksum_verification_enabled", lambda _value: False)
    preflight = []
    monkeypatch.setattr(storage, "set_upload_preflight_confirmation_enabled", lambda value: preflight.append(value) or value)
    monkeypatch.setattr(settings_model, "persist_model_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(storage, "update_settings", lambda patch: dict(patch))
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: wx.OK)
    host = view.build_settings_panel(
        frame, settings_model.WxSettingsModel(),
        session_state={"session": {"connected": True, "profile_name": "lab", "profile": profile}},
    )
    fields = host._wx_settings_preference_controls
    assert fields["profile_scratch_dir"].IsEnabled()
    reset = host._wx_settings_controls["reset_remote_defaults"]
    reset.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, reset.GetId()))
    defaults = hpc_default_remote_paths()
    assert fields["profile_scratch_dir"].GetValue() == defaults["scratch_dir"]
    assert fields["profile_home_dir"].GetValue() == defaults["home_dir"]
    apply = host._wx_settings_controls["apply"]
    apply.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, apply.GetId()))
    _pump(app, lambda: bool(writes))
    assert writes[-1]["system"] == defaults
    host.Destroy()
    frame.Destroy()


def test_macos_settings_hide_vcxsrv_exit_option(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    monkeypatch.setattr(wx, "GetOsDescription", lambda: "macOS")
    monkeypatch.setattr(storage, "load_settings", lambda: {})
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    frame = wx.Frame(None)
    host = view.build_settings_panel(frame, settings_model.WxSettingsModel())
    assert not host._wx_settings_preference_controls["close_vcxsrv_on_exit"].IsShown()
    host.Destroy()
    frame.Destroy()


def test_settings_shortcut_editor_changes_resets_and_persists_bindings(app, monkeypatch):
    import hpc_gui.config.storage as storage
    import hpc_gui.wx_settings as settings_model
    import hpc_gui.wx_settings_view as view

    monkeypatch.setattr(storage, "load_settings", lambda: {"shortcut_preferences": {}})
    monkeypatch.setattr(storage, "load_profiles", lambda: [])
    monkeypatch.setattr(storage, "get_file_associations", lambda: {})
    monkeypatch.setattr(storage, "set_transfer_checksum_verification_enabled", lambda _value: False)
    preflight = []
    monkeypatch.setattr(storage, "set_upload_preflight_confirmation_enabled", lambda value: preflight.append(value) or value)
    snapshots = []
    updates = []
    original_persist = settings_model.persist_model_snapshot
    def capture_persist(snapshot):
        snapshots.append(snapshot)
        return original_persist(snapshot)
    monkeypatch.setattr(settings_model, "persist_model_snapshot", capture_persist)
    monkeypatch.setattr(storage, "set_remote_directory_cache_enabled", lambda value: value)
    monkeypatch.setattr(storage, "set_upload_preflight_confirmation_enabled", lambda value: value)
    monkeypatch.setattr(storage, "set_jobs_outputs_refresh_interval_seconds", lambda value: value)
    monkeypatch.setattr(storage, "set_ssh_connection_attempts", lambda value: value)
    monkeypatch.setattr(storage, "load_profiles", lambda: [{"name": "lab", "system": {}}])
    monkeypatch.setattr(storage, "get_last_profile_name", lambda: "lab")
    monkeypatch.setattr(storage, "upsert_profile", lambda value: updates.append(dict(value)))
    monkeypatch.setattr(storage, "update_settings", lambda patch: updates.append(dict(patch)) or dict(patch))
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: wx.OK)
    errors = []
    import hpc_gui.core.wx_errors as wx_errors
    monkeypatch.setattr(wx_errors, "report_wx_action_error", lambda *args, **kwargs: errors.append(kwargs.get("exc")))
    refreshed = []

    class TextEntry:
        def __init__(self, *_args, **_kwargs):
            self.value = "Ctrl+F3"

        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return self.value

        def Destroy(self):
            pass

    monkeypatch.setattr(wx, "TextEntryDialog", TextEntry)
    frame = wx.Frame(None)
    frame._wx_shell_refresh_shortcuts = lambda: refreshed.append(True)
    model = settings_model.WxSettingsModel({"shortcut_preferences": {}})
    host = view.build_settings_panel(
        frame, model,
        session_state={"session": {"profile_name": "lab", "profile": {"name": "lab"}}},
    )
    controls = host._wx_settings_shortcut_controls
    assert controls["change"].IsEnabled() is False
    index = next(
        i for i in range(controls["list"].GetCount())
        if controls["list"].GetClientData(i) == "APP-HELP"
    )
    controls["list"].SetSelection(index)
    assert controls["list"].GetClientData(controls["list"].GetSelection()) == "APP-HELP"
    controls["list"].GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_LISTBOX, controls["list"].GetId()))
    assert controls["change"].IsEnabled()
    controls["change"].GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["change"].GetId()))
    assert not errors, errors
    assert next(item.binding for item in model.shortcuts.bindings() if item.command_id == "APP-HELP") == "Ctrl+F3"
    controls["reset_all"].Command(wx.CommandEvent(wx.wxEVT_BUTTON, controls["reset_all"].GetId()))
    assert next(item.binding for item in model.shortcuts.bindings() if item.command_id == "APP-HELP") == "F1"
    controls["change"].Command(wx.CommandEvent(wx.wxEVT_BUTTON, controls["change"].GetId()))
    button = host._wx_settings_controls["apply"]
    button.Command(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
    _pump(app, lambda: (len(updates) >= 2 or bool(errors)) and bool(refreshed))
    app.Yield(True)
    assert not errors, errors
    assert refreshed

    stored = snapshots[0].global_settings["shortcut_preferences"]
    assert stored["bindings"]["APP-HELP"] == ["Ctrl+F3"]
    assert next(patch["shortcut_preferences"] for patch in updates if "shortcut_preferences" in patch) == stored
    host.Destroy()
    frame.Destroy()


def test_shell_shortcut_refresh_rebuilds_native_accelerator_table(app, monkeypatch):
    import hpc_gui.wx_shortcuts as shortcuts

    frame = wx.Frame(None)
    accelerator_ids = {101: 0, 102: "help", 103: "settings"}
    accelerator_spec = [
        (int(wx.ACCEL_CTRL), ord("1"), 101),
        (int(wx.ACCEL_NORMAL), int(wx.WXK_F1), 102),
        (int(wx.ACCEL_NORMAL), int(wx.WXK_F2), 103),
    ]
    monkeypatch.setattr(
        shortcuts, "shell_bindings",
        lambda _platform: [("APP-HELP", "Ctrl+F3"), ("APP-SETTINGS", "F2")],
    )

    shortcuts.refresh_shell_accelerators(
        wx, frame, accelerator_ids, accelerator_spec,
        lambda _command: (lambda _event: None),
    )

    assert accelerator_spec == [
        (int(wx.ACCEL_CTRL), ord("1"), 101),
        (int(wx.ACCEL_CTRL), int(wx.WXK_F3), 102),
        (int(wx.ACCEL_NORMAL), int(wx.WXK_F2), 103),
    ]
    frame.Destroy()
