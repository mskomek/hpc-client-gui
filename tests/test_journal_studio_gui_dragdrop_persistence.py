"""Journal Studio GUI coverage: file drop onto the Studio and state kept across reopen.

Drives the real JournalStudioWorkspace inside a hidden wx.Frame. Background
reads are delivered back through wx.CallAfter, so tests pump the wx event loop
until the expected page exists.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"
REGISTRY = {
    "product_id": "fluent",
    "version_id": "25.2",
    "commands": [
        {"command_path": "/solve/iterate", "category": "solve", "verification_status": "unverified", "mode_scope": "unknown", "parameters": []},
        {"command_path": "/file/read-case", "category": "file", "verification_status": "unverified", "mode_scope": "unknown", "parameters": []},
    ],
}


def make_plugin(root: Path):
    data = json.dumps(REGISTRY).encode("utf-8")
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "command_registry.json").write_bytes(data)
    record = SimpleNamespace(path="data/command_registry.json", size=len(data), sha256=hashlib.sha256(data).hexdigest())
    return SimpleNamespace(directory=str(root), manifest=SimpleNamespace(id=PLUGIN_ID, files=[record]))


def pump(wx, predicate, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        wx.Yield()
        if predicate():
            return True
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)


class _Event:
    def Skip(self):
        return None


@pytest.fixture(scope="module")
def wx_app():
    import wx

    app = wx.App.Get() or wx.App(False)  # keep a reference so the app is not collected
    yield app


@pytest.fixture
def studio(tmp_path, wx_app):
    import wx
    from hpc_gui.wx_journal_studio import JournalStudioWorkspace

    frame = wx.Frame(None, size=(1200, 800))
    frame.CreateStatusBar()
    notebook = wx.Notebook(frame)
    state = {"_embedded_main_notebook": notebook, "session": {}}
    workspace = JournalStudioWorkspace(frame, state, make_plugin(tmp_path / "plugin"))
    yield SimpleNamespace(wx=wx, frame=frame, notebook=notebook, state=state, ws=workspace, plugin=workspace.plugin)
    frame.Destroy()


def _write(path: Path, text: str) -> bytes:
    data = text.encode("utf-8")
    path.write_bytes(data)
    return data


def test_dropping_journal_files_opens_them_and_ignores_other_files(studio, tmp_path):
    first = tmp_path / "case.jou"
    second = tmp_path / "CASE2.JOU"
    other = tmp_path / "notes.txt"
    _write(first, "/solve/iterate 10\n")
    _write(second, "/solve/iterate 20\n")
    other.write_text("not a journal", encoding="utf-8")
    target = studio.ws.panel.GetDropTarget()
    assert target is not None

    assert target.OnDropFiles(0, 0, [str(other)]) is False
    assert studio.ws.documents.GetPageCount() == 0

    assert target.OnDropFiles(0, 0, [str(first), str(other), str(second)]) is True
    assert pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 2)
    paths = sorted(page.document.path for page in studio.ws._pages.values())
    assert paths == sorted([str(first), str(second)])
    assert all(not page.document.modified for page in studio.ws._pages.values())


def test_dropped_journal_opens_with_its_exact_bytes_and_crlf_newline(studio, tmp_path):
    path = tmp_path / "crlf.scm"
    data = b"; scheme\r\n(define x 1)\r\n"
    path.write_bytes(data)

    assert studio.ws.panel.GetDropTarget().OnDropFiles(0, 0, [str(path)]) is True
    assert pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 1)
    page = studio.ws._active_page()
    assert page.document.newline == "\r\n"
    assert page.document.to_bytes() == data


def test_reopening_studio_keeps_pages_unsaved_edits_and_splitter_layout(studio, tmp_path):
    from hpc_gui.wx_journal_studio import dispatch_journal_studio_action

    path = tmp_path / "run.jou"
    _write(path, "/solve/iterate 10\n")
    assert studio.ws.open_document(str(path), remote=False) is True
    assert pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 1)
    page = studio.ws._active_page()
    page.source.SetText("/solve/iterate 99\n")
    page._source_changed(_Event())
    studio.frame.Show()  # a hidden frame has no size, so the sash would clamp
    studio.wx.Yield()
    split = page.structure_panel.GetParent()
    split.SetSashPosition(260)
    studio.wx.Yield()

    assert studio.ws.dispatch("open") is True
    assert dispatch_journal_studio_action(studio.frame, studio.state, studio.plugin, "open") is True

    assert studio.state["_journal_studio_panel"] is studio.ws.panel
    assert studio.state["_journal_studio_controller"] is studio.ws
    assert studio.notebook.GetPageCount() == 1
    assert studio.ws.documents.GetPageCount() == 1
    assert studio.ws._active_page() is page
    assert page.document.modified is True
    assert page.document.text == "/solve/iterate 99\n"
    assert split.GetSashPosition() == 260
    assert studio.notebook.GetPage(studio.notebook.GetSelection()) is studio.ws.panel


def test_reopening_same_journal_selects_existing_page_instead_of_duplicating(studio, tmp_path):
    path = tmp_path / "once.jou"
    _write(path, "/solve/iterate 10\n")
    assert studio.ws.open_document(str(path), remote=False) is True
    assert pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 1)

    assert studio.ws.open_document(str(path), remote=False) is True
    studio.wx.Yield()

    assert studio.ws.documents.GetPageCount() == 1
