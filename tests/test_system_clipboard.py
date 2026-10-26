from hpc_gui.services.system_clipboard import get_text, set_text


class Clipboard:
    def __init__(self, opens):
        self.opens = iter(opens)
        self.values = []
        self.close_count = 0

    def Open(self):
        return next(self.opens, True)

    def SetData(self, value):
        self.values.append(value)
        return True

    def Close(self):
        self.close_count += 1


def test_system_clipboard_retries_a_transient_lock_and_closes_after_write():
    clipboard = Clipboard([False, True])
    sleeps = []

    result = set_text(
        clipboard, lambda value: value, "remote path",
        retry_delay=0.01, sleep=sleeps.append,
    )

    assert result is True
    assert clipboard.values == ["remote path"]
    assert clipboard.close_count == 1
    assert sleeps == [0.01]


def test_system_clipboard_closes_when_write_fails_and_returns_false():
    class FailedClipboard(Clipboard):
        def SetData(self, value):
            self.values.append(value)
            return False

    clipboard = FailedClipboard([True, True])
    result = set_text(
        clipboard, lambda value: value, "remote path",
        attempts=2, retry_delay=0, sleep=lambda _delay: None,
    )

    assert result is False
    assert clipboard.values == ["remote path", "remote path"]
    assert clipboard.close_count == 2


def test_system_clipboard_retries_a_transient_read_lock_and_closes():
    class TextData:
        def __init__(self):
            self.value = ""

        def GetText(self):
            return self.value

    class ReadClipboard(Clipboard):
        def __init__(self):
            super().__init__([False, True])

        def GetData(self, data):
            data.value = "copied log"
            return True

    clipboard = ReadClipboard()
    sleeps = []
    result = get_text(
        clipboard, TextData, retry_delay=0.01, sleep=sleeps.append,
    )

    assert result == "copied log"
    assert clipboard.close_count == 1
    assert sleeps == [0.01]
