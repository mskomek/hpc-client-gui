from pathlib import Path
import re

from PySide6.QtCore import Qt

from hpc_gui.ui.widgets.login_widget import LoginWidget


class _KeyEvent:
    def __init__(self, key, text, modifiers=Qt.KeyboardModifier.NoModifier):
        self._key = key
        self._text = text
        self._modifiers = modifiers

    def key(self):
        return self._key

    def text(self):
        return self._text

    def modifiers(self):
        return self._modifiers


def test_terminal_control_and_navigation_sequences_are_stable():
    ctrl = Qt.KeyboardModifier.ControlModifier
    assert LoginWidget._terminal_key_sequence(None, _KeyEvent(Qt.Key.Key_C, "c", ctrl)) == "\x03"
    assert LoginWidget._terminal_key_sequence(None, _KeyEvent(Qt.Key.Key_Left, "")) == "\x1b[D"
    assert LoginWidget._terminal_key_sequence(None, _KeyEvent(Qt.Key.Key_Delete, "")) == "\x1b[3~"


def test_keyboard_contract_ids_are_unique_and_map_to_baseline():
    root = Path(__file__).parents[1]
    contract = (root / "docs" / "v2" / "GUI_KEYBOARD_INTERACTION_CONTRACT.md").read_text(encoding="utf-8")
    baseline = (root / "docs" / "v2" / "GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8")
    ids = re.findall(r"\bGUI-[A-Z]+-\d{3}\b", contract)
    baseline_ids = set(re.findall(r"\bGUI-[A-Z]+-\d{3}\b", baseline))
    assert len(ids) == len(set(ids))
    assert all(item.rsplit("-", 1)[0] + "-001" in baseline_ids for item in ids)
