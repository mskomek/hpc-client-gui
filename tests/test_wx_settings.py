from hpc_gui.wx_settings import LEGACY_IGNORED_KEYS, WxSettingsModel


def test_settings_round_trip_and_global_profile_boundaries():
    applied = []
    model = WxSettingsModel({"jobs_outputs_refresh_interval": 20, "transfer_parallelism": 3}, apply=applied.append)
    model.set_global("remote_directory_cache", False)
    model.set_profile("x11_enabled", True)
    snapshot = model.apply()
    assert snapshot.global_settings["remote_directory_cache"] is False
    assert snapshot.profile_settings["x11_enabled"] is True and applied == [snapshot]
    serialized = model.serialized()
    assert serialized["transfer_parallelism"] == 3 and "shortcut_preferences" in serialized


def test_shortcut_changes_and_legacy_qt_setting_ignored():
    model = WxSettingsModel({"qt_webengine_gpu": False})
    model.shortcuts.set_binding("APP-HELP", "Ctrl+Alt+H")
    assert any(item.binding == "Ctrl+Alt+H" for item in model.shortcuts.bindings())
    assert "qt_webengine_gpu" in LEGACY_IGNORED_KEYS and "qt_webengine_gpu" not in model.serialized()


def test_settings_use_native_macos_shortcuts():
    model = WxSettingsModel(platform="macos")
    assert any(item.binding == "Cmd+," for item in model.shortcuts.bindings())
