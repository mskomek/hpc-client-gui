from pathlib import Path

from hpc_gui.wx_terminal_clipboard import (
    CLIPBOARD_COPY_PREFIX,
    CLIPBOARD_ESCAPE_PREFIX,
    CLIPBOARD_PASTE_REQUEST,
    install_terminal_clipboard_shortcuts,
)


class _Clipboard:
    def __init__(self):
        self.value = ""
        self.open = False

    def Open(self):
        self.open = True
        return True

    def SetData(self, data):
        self.value = data.GetText()
        return True

    def GetData(self, data):
        data.value = self.value
        return True

    def Close(self):
        self.open = False


class _TextData:
    def __init__(self, value=""):
        self.value = value

    def GetText(self):
        return self.value


def test_clipboard_requests_are_local_and_normal_input_reaches_ssh():
    clipboard = _Clipboard()
    wx_module = type("Wx", (), {"TheClipboard": clipboard, "TextDataObject": _TextData})
    sent, pasted = [], []
    panel = type("Panel", (), {
        "_handle_input": lambda _self, data: sent.append(data) or True,
        "hpc_paste": lambda _self, data: pasted.append(data) or True,
    })()
    install_terminal_clipboard_shortcuts(panel, wx_module)

    assert panel._handle_input(CLIPBOARD_COPY_PREFIX + "selected output")
    assert clipboard.value == "selected output" and sent == []
    clipboard.value = "pasted command\n"
    assert panel._handle_input(CLIPBOARD_PASTE_REQUEST)
    assert pasted == ["pasted command\n"] and sent == []
    assert panel._handle_input("echo ready\r")
    assert sent == ["echo ready\r"]
    assert panel._handle_input(CLIPBOARD_ESCAPE_PREFIX + CLIPBOARD_PASTE_REQUEST)
    assert sent[-1] == CLIPBOARD_PASTE_REQUEST
    assert not clipboard.open


def test_webview_bridge_registers_windows_and_macos_clipboard_shortcuts():
    bridge = Path("src/hpc_gui/assets/terminal/wx_bridge.js").read_text(encoding="utf-8")
    assert "attachCustomKeyEventHandler" in bridge
    assert "event.ctrlKey" in bridge and "event.metaKey" in bridge
    assert "clipboardCopyPrefix" in bridge and "clipboardPasteRequest" in bridge
