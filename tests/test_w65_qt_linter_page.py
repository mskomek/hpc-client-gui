"""Interactive-level Qt page checks for the API 3 OpenFOAM Linter surface."""

from __future__ import annotations

import stat
import time
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
)

from hpc_gui.core.i18n import t
from hpc_gui.plugin_engines.openfoam_lint.qt_page import create_qt_page

pytestmark = pytest.mark.qt


@pytest.fixture(scope="module", autouse=True)
def _finish_qt_workers():
    yield
    assert QThreadPool.globalInstance().waitForDone(5000)
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _application():
    return QApplication.instance() or QApplication([])


def _wait_for(predicate, timeout=5):
    loop = QEventLoop()
    timer = QTimer()
    deadline = time.monotonic() + timeout

    def poll():
        if predicate() or time.monotonic() >= deadline:
            loop.quit()

    timer.timeout.connect(poll)
    timer.start(10)
    poll()
    loop.exec()
    timer.stop()
    assert predicate()


class _RemoteFiles:
    def __init__(self, content: bytes, *, started=None, release=None):
        self.content = content
        self.started = started
        self.release = release
        self.downloaded = False

    def lstat_entry(self, path):
        if path == "/case/system/controlDict":
            return SimpleNamespace(mode=stat.S_IFREG | 0o644, size=len(self.content))
        if path in {"/", "/case", "/case/system"}:
            return SimpleNamespace(mode=stat.S_IFDIR | 0o755, size=0)
        raise FileNotFoundError(path)

    stat_entry = lstat_entry

    def stat(self, path):
        if path != "/case/system/controlDict":
            raise FileNotFoundError(path)
        return len(self.content), 0

    def listdir_entries(self, path):
        entries = {
            "/case": ["system"],
            "/case/system": ["controlDict"],
        }
        return [SimpleNamespace(name=name) for name in entries.get(path, [])]

    def download(self, remote, local):
        if remote != "/case/system/controlDict":
            raise FileNotFoundError(remote)
        if self.started is not None:
            self.started.set()
        if self.release is not None and not self.release.wait(3):
            raise TimeoutError("test download release timed out")
        Path(local).write_bytes(self.content)
        self.downloaded = True


class _Host:
    def __init__(self):
        self.opened = []
        self.editor = SimpleNamespace(go_to_line=self.opened.append)

    def open_local_in_editor(self, path):
        self.opened.append(path)

    def open_in_editor(self, path, content):
        self.opened.append((path, content))


def test_qt_linter_runs_and_marks_local_findings_stale(tmp_path):
    _application()
    case = tmp_path / "case"
    source = case / "system" / "controlDict"
    source.parent.mkdir(parents=True)
    source.write_text("application simpleFoam;\n", encoding="utf-8")
    page = create_qt_page(initial_paths=[str(case)])
    status = page.findChild(QLabel)
    table = page.findChild(QTableWidget)
    run = page.findChildren(QPushButton)[2]
    _wait_for(lambda: run.isEnabled())
    initial_status = status.text()
    initial_rows = table.rowCount()
    source.write_text("application simpleFoam\n", encoding="utf-8")
    _wait_for(lambda: status.text() != initial_status)
    assert table.rowCount() == initial_rows
    page.close()


def test_qt_linter_selected_release_reaches_result(tmp_path):
    _application()
    case = tmp_path / "case"
    system = case / "system"
    system.mkdir(parents=True)
    (system / "controlDict").write_text(
        "application simpleFoam;\n", encoding="utf-8",
    )
    page = create_qt_page()
    selector = page.findChild(QComboBox)
    assert selector is not None
    assert [selector.itemText(i) for i in range(selector.count())] == ["v2312", "v1912"]
    selector.setCurrentText("v1912")
    page.findChild(QListWidget).addItem(str(case))
    page.findChildren(QPushButton)[2].click()
    status = page.findChildren(QLabel)[0]
    _wait_for(lambda: "v1912" in status.text())
    assert "v1912" in status.text()
    page.close()


def test_qt_linter_routes_remote_case_and_opens_finding_at_source(tmp_path):
    _application()
    files = _RemoteFiles(b"#codeStream\n{\ncode \"unsafe\";\n}\n")
    host = _Host()
    page = create_qt_page(
        initial_paths=["/case/system/controlDict"],
        session_state={"session": {"files": files}},
        host_window=host,
    )
    table = page.findChild(QTableWidget)
    _wait_for(lambda: table.rowCount() > 0)
    assert files.downloaded
    location = table.item(0, 2).text()
    assert location.startswith("/case/")
    table.itemDoubleClicked.emit(table.item(0, 0))
    assert host.opened[0][0] == location
    assert "#codeStream" in host.opened[0][1]
    assert host.opened[-1] == 1
    page.close()


def test_qt_linter_disables_remote_path_without_authenticated_session():
    _application()
    page = create_qt_page(
        initial_paths=["/remote/case/system/controlDict"],
        session_state={"remote": True, "session": None},
    )
    run = page.findChildren(QPushButton)[2]
    status = page.findChild(QLabel)
    assert not run.isEnabled()
    assert status.text() == t("openfoam.remote_session_missing")
    page.close()


def test_qt_linter_cancel_stops_at_sftp_file_boundary():
    _application()
    started, release = Event(), Event()
    files = _RemoteFiles(b"application simpleFoam;\n", started=started, release=release)
    page = create_qt_page(
        initial_paths=["/case/system/controlDict"],
        session_state={"session": {"files": files}},
    )
    buttons = page.findChildren(QPushButton)
    cancel = next(button for button in buttons if button.text() == t("openfoam.cancel"))
    status = page.findChild(QLabel)
    assert started.wait(2)
    cancel.click()
    release.set()
    _wait_for(lambda: status.text() == t("openfoam.cancelled"))
    assert files.downloaded
    page.close()
