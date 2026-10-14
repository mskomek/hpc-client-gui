from types import SimpleNamespace

from hpc_gui.wx_shell_layout import center_splitter_on_first_layout


class _Splitter:
    def __init__(self, width):
        self.width = width
        self.positions = []
        self.handlers = {}

    def GetClientSize(self):
        return SimpleNamespace(width=self.width)

    def IsSplit(self):
        return True

    def GetMinimumPaneSize(self):
        return 300

    def SetSashPosition(self, position):
        self.positions.append(position)
        self.position = position

    def GetSashPosition(self):
        return getattr(self, "position", -1)

    def Bind(self, event_type, handler):
        self.handlers[event_type] = handler

    def Unbind(self, event_type, handler):
        if self.handlers.get(event_type) is handler:
            self.handlers.pop(event_type)


def test_splitter_stays_centered_as_its_real_width_changes():
    event_type = object()
    wx = SimpleNamespace(EVT_SIZE=event_type, CallAfter=lambda callback: callback())
    splitter = _Splitter(1200)

    center_splitter_on_first_layout(wx, splitter)

    assert splitter.positions == [600]
    assert event_type in splitter.handlers

    splitter.width = 1500
    splitter.handlers[event_type](SimpleNamespace(Skip=lambda: None))

    assert splitter.positions == [600, 750]
