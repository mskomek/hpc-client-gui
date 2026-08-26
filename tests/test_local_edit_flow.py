"""Wave 71: local "Düzelt" (Edit) action via the in-app editor.

Covers the EditorWidget local-document branch (open/save/reload without
a session) and the LocalDirPanel edit signal wiring. No real filesystem
interaction beyond tmp_path.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hpc_gui.ui.widgets.editor_widget import EditorWidget


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from hpc_gui.core.i18n import load_language

    load_language("en")
    yield app


class FakeBox:
    Information = 1

    @staticmethod
    def information(*args, **kwargs):
        pass

    @staticmethod
    def warning(*args, **kwargs):
        pass

    @staticmethod
    def question(*args, **kwargs):
        return None


def _make_editor():
    widget = EditorWidget()
    return widget


# ---------------------------------------------------------------------------
# EditorWidget local documents
# ---------------------------------------------------------------------------


def test_editor_local_open_save_roundtrip(qapp, tmp_path, monkeypatch):
    target = tmp_path / "case.jou"
    target.write_text("/display set\n", encoding="utf-8")
    monkeypatch.setattr("hpc_gui.ui.widgets.editor_widget.QMessageBox", FakeBox)

    widget = _make_editor()
    widget.open_local_file(str(target))
    assert widget.text.toPlainText() == "/display set\n"
    assert widget.path_in.text() == str(target)

    widget.text.setPlainText("/display set\n/exit yes\n")
    widget.save_path()
    assert target.read_text(encoding="utf-8") == "/display set\n/exit yes\n"


def test_editor_local_reload_reads_disk(qapp, tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("first\n", encoding="utf-8")

    widget = _make_editor()
    widget.open_local_file(str(target))
    target.write_text("second\n", encoding="utf-8")
    widget.load_path()
    assert widget.text.toPlainText() == "second\n"


def test_editor_remote_save_still_requires_session(qapp, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        "hpc_gui.ui.widgets.editor_widget.QMessageBox",
        type(
            "Box",
            (),
            {
                "warning": staticmethod(lambda *a, **k: warnings.append(a)),
                "information": staticmethod(lambda *a, **k: None),
                "question": staticmethod(lambda *a, **k: None),
            },
        ),
    )
    widget = _make_editor()
    widget.open_file("remote.jou", "x")
    widget.save_path()
    assert warnings, "remote save without a session must warn, not crash"


# ---------------------------------------------------------------------------
# LocalDirPanel edit signal
# ---------------------------------------------------------------------------


class _FakeTreeItem:
    def __init__(self, value: str):
        self._value = value

    def data(self, _role, *_args):
        return self._value


def test_local_panel_edit_signal_emission(qapp, tmp_path, monkeypatch):
    from hpc_gui.ui.widgets.local_dir_panel import LocalDirPanel

    panel = LocalDirPanel(str(tmp_path))
    captured = []
    panel.editRequested.connect(lambda path, new_window: captured.append((path, new_window)))
    monkeypatch.setattr(
        panel,
        "_selected_items",
        lambda: [_FakeTreeItem(str(tmp_path / "a.jou"))],
    )

    panel._edit_selected(new_window=False)
    panel._edit_selected(new_window=True)
    assert captured == [
        (str(tmp_path / "a.jou"), False),
        (str(tmp_path / "a.jou"), True),
    ]


def test_local_panel_edit_ignores_directories(qapp, tmp_path, monkeypatch):
    from hpc_gui.ui.widgets.local_dir_panel import LocalDirPanel

    panel = LocalDirPanel(str(tmp_path))
    captured = []
    panel.editRequested.connect(lambda path, new_window: captured.append((path, new_window)))
    monkeypatch.setattr(panel, "_selected_items", lambda: [_FakeTreeItem(str(tmp_path))])

    panel._edit_selected(new_window=False)
    assert captured == []
