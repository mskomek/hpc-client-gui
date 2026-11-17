"""Regression coverage for native wxGTK notebook page redraws."""

from types import SimpleNamespace

from hpc_gui.wx_shell_events import bind_notebook_native_repaint


class _Window:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls
        self.deleted = False

    def IsBeingDeleted(self):
        return self.deleted

    def Refresh(self, erase_background):
        self.calls.append((self.name, "refresh", erase_background))

    def Update(self):
        self.calls.append((self.name, "update"))


class _Notebook(_Window):
    def __init__(self, calls, page, frame):
        super().__init__("notebook", calls)
        self.page = page
        self.frame = frame
        self.handler = None

    def Bind(self, event_type, handler):
        self.handler = handler

    def GetCurrentPage(self):
        return self.page

    def GetTopLevelParent(self):
        return self.frame


class _Event:
    def __init__(self):
        self.skipped = False

    def Skip(self):
        self.skipped = True


def test_page_change_flushes_native_paint_after_event_dispatch():
    calls = []
    pending = []
    page = _Window("page", calls)
    frame = _Window("frame", calls)
    notebook = _Notebook(calls, page, frame)
    wx = SimpleNamespace(
        EVT_NOTEBOOK_PAGE_CHANGED=object(),
        CallAfter=lambda callback: pending.append(callback),
    )

    bind_notebook_native_repaint(wx, notebook)
    event = _Event()
    notebook.handler(event)

    assert event.skipped
    assert calls == []
    assert len(pending) == 1
    pending.pop()()

    assert calls == [
        ("notebook", "refresh", False),
        ("page", "refresh", False),
        ("frame", "refresh", False),
        ("notebook", "update"),
        ("page", "update"),
        ("frame", "update"),
    ]
