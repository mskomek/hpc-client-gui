from hpc_gui.wx_connection import HostKeyRequest, KeyboardInteractiveRequest, WxConnectionModel


def test_profile_management_and_mock_connect():
    profiles = [{"name": "cluster", "host": "hpc.example", "username": "user", "password": "secret", "system": {"provider": "generic"}}]
    connected = []
    model = WxConnectionModel(profiles, connect=connected.append)
    assert model.summaries()[0].host == "hpc.example"
    assert "password" not in model.summaries()[0].__dict__
    assert model.select("cluster") and model.connect_selected()
    assert connected[0]["host"] == "hpc.example"
    assert model.controller.state.value == "connecting"


def test_unknown_profile_and_optional_wx_import():
    model = WxConnectionModel([])
    assert not model.select("missing") and not model.connect_selected()
    source = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "from PySide6" not in source and "import wx" in source


def test_wx_connection_view_has_async_selection_and_double_click_connect():
    source = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "EVT_LISTBOX_DCLICK" in source
    assert "Thread(target=worker" in source and "wx.CallAfter(done" in source
    assert "subscribe_language_change(refresh_labels)" in source
    assert "host_key_prompt_message" in source and "mfa_dialog" in source


def test_connection_security_callbacks_fail_closed_and_do_not_store_mfa():
    request = HostKeyRequest("hpc.example", "aa:bb")
    mfa = KeyboardInteractiveRequest("MFA", "code", ("Response:",))
    model = WxConnectionModel([], keyboard_interactive=lambda _request: ["one-time"])
    assert model.decide_host_key(request) == "reject"
    assert model.answer_keyboard_interactive(mfa) == ["one-time"]
    assert not hasattr(model, "one-time")
