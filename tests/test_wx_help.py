from hpc_gui.core.i18n import load_language, set_language
from hpc_gui.wx_help import WxHelpModel


def test_wx_help_uses_shared_search_palette_and_platform_display():
    model = WxHelpModel("macos", {"shortcut_preferences": {"FILE-FIND": ["Cmd+K"]}})
    assert model.search_help("ctrl z")
    assert model.palette_search("command")
    model.set_binding("FILE-FIND", "Cmd+L")
    assert model.shortcuts.bindings()[-1].binding == "Cmd+L"
    assert model.external_url_allowed("https://example.org/help", {"example.org"})
    assert not model.external_url_allowed("http://example.org/help", {"example.org"})


def test_wx_help_model_is_toolkit_free():
    source = open("src/hpc_gui/wx_help.py", encoding="utf-8").read()
    assert "from PySide6" not in source


def test_wx_help_model_uses_native_platform_shortcuts():
    model = WxHelpModel("macos")
    assert any(item.binding == "Cmd+," for item in model.shortcuts.bindings())


def test_help_center_navigation_and_shared_content():
    load_language("en")
    model = WxHelpModel("windows")
    assert [item.id for item in model.navigation()] == [topic.id for topic in model.catalog.topics()] + ["help.library.truba", "help.library.generic"]
    page = model.select_topic("help.keyboard-shortcuts")
    assert "Keyboard Shortcuts" in page and "Ctrl+" in page
    assert model.select_topic("help.library.generic")


def test_help_topic_survives_language_switch_and_titles_refresh():
    load_language("en")
    model = WxHelpModel("windows")
    model.select_topic("help.keyboard-shortcuts")
    set_language("tr")
    assert model.current_topic_id == "help.keyboard-shortcuts"
    assert "Klavye Kısayolları" in model.page()
    set_language("en")


def test_help_search_result_navigates_to_shared_topic():
    load_language("en")
    model = WxHelpModel("windows")
    result = model.search_help("middle click")[0]
    assert result.kind == "gesture"
    model.navigate_result(result)
    assert model.current_topic_id == "help.mouse-gestures"

    result = model.search_help("Ctrl+Z")[0]
    model.navigate_result(result)
    assert model.current_topic_id in {"help.keyboard-shortcuts", "help.editor", "help.files-transfers", "help.terminal"}
