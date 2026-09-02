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
