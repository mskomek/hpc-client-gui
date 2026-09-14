import ast
from pathlib import Path

import pytest

from hpc_gui.services.remote_directory_controller import RemoteDirectoryController
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController


@pytest.mark.unit
@pytest.mark.semantic
def test_transfer_queue_conflict_checksum_and_status():
    session = TransferSessionController([TransferItem("upload", "a", "b")], lambda item, progress: None)
    assert session.status().queued == 1
    session.set_conflict_policy("skip")
    session.set_checksum_enabled(True)
    assert session.conflict_policy == "skip" and session.checksum_enabled


@pytest.mark.unit
@pytest.mark.semantic
def test_remote_navigation_favorites_and_stale_listing():
    controller = RemoteDirectoryController()
    first = controller.navigate("/one")
    second = controller.navigate("/two")
    assert not controller.is_current(first) and controller.is_current(second)
    assert controller.toggle_favorite("/two")
    assert not controller.toggle_favorite("/two")
    assert controller.back() is not None


@pytest.mark.audit
@pytest.mark.qt
def test_controllers_have_no_qt_imports():
    qt_roots = {"PySide", "PySide2", "PySide6", "PyQt5", "PyQt6", "shiboken6"}

    def imported_qt_roots(source):
        found = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".", 1)[0])
        return found & qt_roots

    assert imported_qt_roots("import PySide6.QtWidgets as widgets") == {"PySide6"}
    assert imported_qt_roots("from PyQt6.QtCore import QObject") == {"PyQt6"}

    source_root = Path(__file__).parents[1] / "src" / "hpc_gui" / "services"
    for filename in ("transfer_session_controller.py", "remote_directory_controller.py"):
        source = (source_root / filename).read_text(encoding="utf-8")
        assert not imported_qt_roots(source), filename
