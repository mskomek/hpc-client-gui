"""Regress native Qt/wx collection order without importing either GUI toolkit."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import _imports_qt, pytest_collection_modifyitems

pytestmark = [pytest.mark.unit, pytest.mark.regression]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from PySide6.QtWidgets import QApplication\n", True),
        ("import PySide6.QtGui as Gui\n", True),
        ("import PySide6\n", True),
        ("from PySide6 import QtCore\n", True),
        ('TEXT = "from PySide6.QtWidgets import QWidget"\n', False),
        ("# import PySide6\nimport os\n", False),
        ("import not_PySide6\n", False),
        ("from os import path\n", False),
        ("def missing(:\n", False),
    ],
)
def test_qt_detection_uses_ast_import_nodes(tmp_path, source, expected):
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    _imports_qt.cache_clear()
    assert _imports_qt(str(path)) is expected


def test_collection_orders_true_qt_imports_and_fixtures_first(tmp_path):
    class Item:
        def __init__(self, name, source, *, marked=False, fixtures=()):
            path = tmp_path / (name + ".py")
            path.write_text(source, encoding="utf-8")
            self.name = name
            self.module = SimpleNamespace(__file__=str(path))
            self.fixturenames = list(fixtures)
            self.marked = marked

        def get_closest_marker(self, name):
            return object() if name == "qt" and self.marked else None

    items = [
        Item("wx_first", "import wx\n"),
        Item("real_qt", "from PySide6.QtWidgets import QApplication\n"),
        Item("string_only", 'TEXT = "import PySide6"\n'),
        Item("qt_fixture", "import os\n", fixtures=("qapp",)),
        Item("qt_marker", "import os\n", marked=True),
        Item("module_qt", "import PySide6.QtCore\n"),
    ]
    pytest_collection_modifyitems(items)
    assert [item.name for item in items] == [
        "real_qt",
        "qt_fixture",
        "qt_marker",
        "module_qt",
        "wx_first",
        "string_only",
    ]


def test_missing_module_does_not_break_collection(tmp_path):
    _imports_qt.cache_clear()
    assert _imports_qt(str(tmp_path / "missing.py")) is False
