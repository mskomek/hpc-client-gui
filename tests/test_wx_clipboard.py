from hpc_gui.wx_clipboard import write_text


class _Clipboard:
    def __init__(self, open_results, set_results=None):
        self.open_results = iter(open_results)
        self.set_results = iter(set_results or [True])
        self.opened = False
        self.closed = 0
        self.value = None

    def Open(self):
        self.opened = next(self.open_results)
        return self.opened

    def SetData(self, data):
        self.value = data.value
        return next(self.set_results)

    def Close(self):
        self.closed += 1
        self.opened = False


class _Wx:
    def __init__(self, results, set_results=None):
        self.TheClipboard = _Clipboard(results, set_results)
        self.LogNull = lambda: object()
        self.TextDataObject = lambda value: type("Text", (), {"value": value})()


def test_write_text_retries_transient_lock_and_closes_clipboard():
    wx = _Wx([False, False, True])
    assert write_text(wx, "/work/a.txt", attempts=3, delay=0) is True
    assert wx.TheClipboard.value == "/work/a.txt"
    assert wx.TheClipboard.closed == 1


def test_write_text_returns_false_when_clipboard_stays_locked():
    wx = _Wx([False, False])
    assert write_text(wx, "path", attempts=2, delay=0) is False
    assert wx.TheClipboard.closed == 0


def test_write_text_retries_when_native_write_is_rejected():
    wx = _Wx([True, True], [False, True])
    assert write_text(wx, "path", attempts=2, delay=0) is True
    assert wx.TheClipboard.closed == 2
