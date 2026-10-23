"""Journal Studio editor coverage: parameter edit round trip and 10k+ line journals.

Time budgets are stated in the constants below. They are generous enough for a
loaded Windows VM and tight enough to catch an accidental quadratic parse or a
blocking file read on the wx UI thread.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.journal_studio import JournalDocument, parse_journal
from hpc_gui.services.journal_studio_files import read_local


PARSE_BUDGET_SECONDS = 3.0
UI_GAP_BUDGET_SECONDS = 3.0
OPEN_BUDGET_SECONDS = 20.0
REFRESH_BUDGET_SECONDS = 2.0
LARGE_LINE_COUNT = 12_000
PLUGIN_ID = "org.hpcclient.ansysjournalstudio"
REGISTRY = {
    "product_id": "fluent",
    "version_id": "25.2",
    "commands": [
        {"command_path": "/solve/iterate", "category": "solve", "verification_status": "unverified", "mode_scope": "unknown", "parameters": []},
    ],
}


def make_plugin(root: Path):
    data = json.dumps(REGISTRY).encode("utf-8")
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "command_registry.json").write_bytes(data)
    record = SimpleNamespace(path="data/command_registry.json", size=len(data), sha256=hashlib.sha256(data).hexdigest())
    return SimpleNamespace(directory=str(root), manifest=SimpleNamespace(id=PLUGIN_ID, files=[record]))


def pump(wx, predicate, timeout: float = 30.0, on_tick=None) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        wx.Yield()
        if on_tick is not None:
            on_tick()
        if predicate():
            return True
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)


class _Event:
    def Skip(self):
        return None


def large_journal_text(lines: int = LARGE_LINE_COUNT) -> str:
    rows = []
    for index in range(lines):
        rows.append((
            f"/solve/iterate {index}",
            f"(define v{index} (+ {index} 1))",
            f"; step {index}",
            f"raw token {index}",
        )[index % 4])
    return "\n".join(rows) + "\n"


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
    yield SimpleNamespace(wx=wx, frame=frame, state=state, ws=workspace)
    frame.Destroy()


def _open(studio, path: Path):
    assert studio.ws.open_document(str(path), remote=False) is True
    assert pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 1)
    return studio.ws._active_page()


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"], ids=["lf", "crlf"])
def test_parameter_edit_save_reload_round_trip_changes_only_the_edited_bytes(studio, tmp_path, newline):
    original = newline.join([
        b"; parameters",
        b"/solve/iterate 100",
        b"(define tolerance 1e-4)",
        b'/file/write-case "out.cas"',
        b"",
    ])
    path = tmp_path / "params.jou"
    path.write_bytes(original)
    page = _open(studio, path)

    edited_display = page.source.GetText().replace("/solve/iterate 100", "/solve/iterate 250")
    page.source.SetText(edited_display)
    page._source_changed(_Event())
    page._refresh_after_edit()
    assert page.document.modified is True
    assert "/solve/iterate 250" in page.preview.GetValue()

    assert page.save() is True
    assert pump(studio.wx, lambda: not page.document.modified)

    expected = original.replace(b"/solve/iterate 100", b"/solve/iterate 250")
    assert path.read_bytes() == expected
    reloaded = JournalDocument.from_bytes(read_local(path), path=str(path))
    assert reloaded.to_bytes() == expected
    assert reloaded.newline == ("\r\n" if newline == b"\r\n" else "\n")
    assert "/solve/iterate 250" in reloaded.text and "/solve/iterate 100" not in reloaded.text


def test_parameter_edit_keeps_document_unsaved_when_save_is_refused_locally(studio, tmp_path):
    path = tmp_path / "readonly.jou"
    original = b"/solve/iterate 10\n"
    path.write_bytes(original)
    page = _open(studio, path)
    page.source.SetText("/solve/iterate 11\n")
    page._source_changed(_Event())
    path.write_bytes(b"external change\n")

    assert page.save() is True
    assert pump(studio.wx, lambda: "changed after it was opened" in page.status.GetLabel())

    assert path.read_bytes() == b"external change\n"
    assert page.document.modified is True


def test_twelve_thousand_line_journal_parses_and_round_trips_within_budget():
    text = large_journal_text()
    data = text.encode("utf-8")
    assert text.count("\n") >= 10_000

    started = time.perf_counter()
    document = JournalDocument.from_bytes(data, path="large.jou")
    parsed = parse_journal(document.text)
    elapsed = time.perf_counter() - started

    assert elapsed < PARSE_BUDGET_SECONDS, f"parse took {elapsed:.2f}s"
    assert document.to_bytes() == data
    assert parsed.reorder(tuple(range(len(parsed.blocks)))) == text
    assert len(parsed.blocks) >= LARGE_LINE_COUNT // 4


def test_twelve_thousand_line_journal_opens_without_blocking_the_ui_thread(studio, tmp_path, monkeypatch):
    import wx
    from hpc_gui import wx_journal_studio

    path = tmp_path / "large.jou"
    data = large_journal_text().encode("utf-8")
    path.write_bytes(data)
    real_read = wx_journal_studio.read_local

    def slow_read(target):
        time.sleep(1.0)  # stands in for slow disk or network I/O
        return real_read(target)

    monkeypatch.setattr(wx_journal_studio, "read_local", slow_read)
    started = time.perf_counter()
    assert studio.ws.open_document(str(path), remote=False) is True
    assert time.perf_counter() - started < 0.5, "open_document blocked the caller"

    beats = [time.perf_counter()]
    gaps: list[float] = []

    def beat():
        now = time.perf_counter()
        gaps.append(now - beats[-1])
        beats[-1] = now
        return studio.ws.documents.GetPageCount() == 1

    assert pump(wx, beat, timeout=OPEN_BUDGET_SECONDS, on_tick=None)
    total = time.perf_counter() - started
    page = studio.ws._active_page()
    assert total < OPEN_BUDGET_SECONDS, f"open took {total:.2f}s"
    assert page.document.to_bytes() == data
    assert page.structure.GetCount() == 0
    assert "over 10,000 lines" in page.problems.GetValue()
    assert max(gaps) < UI_GAP_BUDGET_SECONDS, f"longest UI gap {max(gaps):.2f}s"


def test_twelve_thousand_line_edit_refresh_stays_within_budget(studio, tmp_path):
    path = tmp_path / "large-edit.jou"
    path.write_bytes(large_journal_text().encode("utf-8"))
    page = _open(studio, path)
    assert len(page.document.text) <= 256 * 1024, "diff preview would be paused; use a smaller fixture"

    page.source.SetText(page.source.GetText().replace("/solve/iterate 0\n", "/solve/iterate 0 edited\n", 1))
    page._source_changed(_Event())
    started = time.perf_counter()
    page._refresh_after_edit()
    elapsed = time.perf_counter() - started

    assert elapsed < REFRESH_BUDGET_SECONDS, f"edit refresh took {elapsed:.2f}s"
    assert "edited" in page.diff.GetValue()
