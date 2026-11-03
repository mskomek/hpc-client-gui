"""Packaged native terminal is made visible through its real notebook page."""

from hpc_gui.wx_application import activate_terminal_for_packaged_smoke


class _Notebook:
    def __init__(self, pages):
        self.pages = pages
        self.selected = None

    def FindPage(self, page):
        try:
            return self.pages.index(page)
        except ValueError:
            return -1

    def SetSelection(self, index):
        self.selected = index


class _Frame:
    def __init__(self, controls):
        self._wx_shell_controls = controls


def test_packaged_activation_navigates_to_real_terminal_page():
    terminal = object()
    notebook = _Notebook([object(), terminal, object()])
    frame = _Frame({
        "notebook": notebook,
        "pages": {"NAV-TERMINAL": {"page": terminal}},
    })
    assert activate_terminal_for_packaged_smoke(frame)
    assert notebook.selected == 1


def test_packaged_activation_does_not_select_unavailable_tab():
    terminal = object()
    notebook = _Notebook([object()])
    frame = _Frame({
        "notebook": notebook,
        "pages": {"NAV-TERMINAL": {"page": terminal}},
    })
    assert not activate_terminal_for_packaged_smoke(frame)
    assert notebook.selected is None


def test_packaged_activation_handles_missing_controls():
    assert not activate_terminal_for_packaged_smoke(object())
