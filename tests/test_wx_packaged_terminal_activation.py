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


def test_ready_bridge_gets_one_bounded_functional_window():
    from types import SimpleNamespace
    from hpc_gui.wx_shell_smoke_readiness import observe_terminal_readiness

    state = {"phase": 0, "deadline": 10.0}
    panel = SimpleNamespace(_ready=True, _is_parity=True)
    session = {"_embedded_terminal_panel": panel}
    assert observe_terminal_readiness(state, session, 10.5) is panel
    assert state["deadline"] == 35.5
    assert state["terminal_ready_budget_granted"] is True
    observe_terminal_readiness(state, session, 33.0)
    assert state["deadline"] == 35.5


def test_failed_or_unready_terminal_cannot_extend_deadline():
    from types import SimpleNamespace
    from hpc_gui.wx_shell_smoke_readiness import observe_terminal_readiness

    for panel in (
        None, SimpleNamespace(_ready=False, _is_parity=True),
        SimpleNamespace(_ready=True, _is_parity=False),
    ):
        state = {"phase": 0, "deadline": 10.0}
        observe_terminal_readiness(
            state, {"_embedded_terminal_panel": panel}, 12.0,
        )
        assert state["deadline"] == 10.0
        assert "terminal_ready_budget_granted" not in state


def test_later_smoke_phase_cannot_extend_deadline():
    from types import SimpleNamespace
    from hpc_gui.wx_shell_smoke_readiness import observe_terminal_readiness

    state = {"phase": 1, "deadline": 10.0}
    panel = SimpleNamespace(_ready=True, _is_parity=True)
    observe_terminal_readiness(state, {"_embedded_terminal_panel": panel}, 12.0)
    assert state["deadline"] == 10.0
