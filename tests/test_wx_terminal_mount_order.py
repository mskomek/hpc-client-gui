"""Windows WebView2 native mount ordering and closed-parent guards."""

from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel


class _PanelSeam:
    def __init__(self, *, closed=False, being_deleted=False):
        self._closed = closed
        self._being_deleted = being_deleted
        self.calls = []

    def IsBeingDeleted(self):
        return self._being_deleted

    def _mount_webview(self, root):
        self.calls.append(("mount", root))

    def Layout(self):
        self.calls.append(("layout",))


def test_webview_mount_occurs_after_parent_layout_callback():
    panel = _PanelSeam()
    assert panel.calls == []
    WxTerminalWebViewPanel._mount_after_parent_layout(panel, "sizer")
    assert panel.calls == [("mount", "sizer"), ("layout",)]


def test_closed_terminal_cannot_create_native_controller():
    panel = _PanelSeam(closed=True)
    WxTerminalWebViewPanel._mount_after_parent_layout(panel, "sizer")
    assert panel.calls == []


def test_parent_in_teardown_cannot_create_native_controller():
    panel = _PanelSeam(being_deleted=True)
    WxTerminalWebViewPanel._mount_after_parent_layout(panel, "sizer")
    assert panel.calls == []
