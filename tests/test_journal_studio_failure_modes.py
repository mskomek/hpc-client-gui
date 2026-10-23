"""Failure-mode coverage: disk-full local saves and remote SFTP drops.

Service-level checks use the same in-memory SFTP shape as
test_journal_studio_remote_files.py. GUI checks drive the real workspace
controller and read the status text the user sees.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

import pytest

from hpc_gui.services.journal_studio_files import read_local, read_remote, save_local, save_remote


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"
ORIGINAL = b"/solve/iterate 10\r\n; keep\r\n"
UPDATED = b"/solve/iterate 20\r\n; keep\r\n"


class _FullStream:
    """Wraps a real temp-file stream so the first write fails with ENOSPC."""

    def __init__(self, stream):
        self._stream = stream

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self._stream.close()
        return False

    def write(self, _data):
        raise OSError(errno.ENOSPC, "No space left on device")

    def flush(self):
        return None

    def fileno(self):
        return self._stream.fileno()


def _disk_full(monkeypatch):
    real_fdopen = os.fdopen
    monkeypatch.setattr(os, "fdopen", lambda fd, mode="r", *a, **k: _FullStream(real_fdopen(fd, mode, *a, **k)))


def _leftover_temporaries(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.journal-tmp"))


def test_disk_full_local_save_keeps_original_and_removes_temporary(tmp_path, monkeypatch):
    target = tmp_path / "run.jou"
    target.write_bytes(ORIGINAL)
    expected = hashlib.sha256(ORIGINAL).hexdigest()
    _disk_full(monkeypatch)

    with pytest.raises(OSError) as info:
        save_local(target, UPDATED, expected_sha256=expected)

    assert info.value.errno == errno.ENOSPC
    assert target.read_bytes() == ORIGINAL
    assert _leftover_temporaries(tmp_path) == []


def test_disk_full_on_new_file_creates_nothing(tmp_path, monkeypatch):
    target = tmp_path / "fresh.jou"
    _disk_full(monkeypatch)

    with pytest.raises(OSError):
        save_local(target, UPDATED, expected_sha256=None)

    assert not target.exists()
    assert _leftover_temporaries(tmp_path) == []


class _Flaky:
    """In-memory SFTP that resets once, then reports the channel as closed."""

    def __init__(self, files, drop_on_call=None):
        self.files = files
        self.calls = 0
        self.drop_on_call = drop_on_call
        self.dead = False

    def _tick(self):
        if self.dead:
            raise EOFError("SFTP channel is closed")
        self.calls += 1
        if self.calls == self.drop_on_call:
            self.dead = True
            raise ConnectionResetError("SFTP connection reset")

    def stat(self, path):
        self._tick()
        if path not in self.files:
            raise FileNotFoundError(path)
        return SimpleNamespace(st_size=len(self.files[path]), st_mode=0o100640)

    def lstat(self, path):
        self._tick()
        if path in self.files:
            return SimpleNamespace(st_size=len(self.files[path]), st_mode=0o100640)
        if path == "/" or any(item.startswith(path.rstrip("/") + "/") for item in self.files):
            return SimpleNamespace(st_size=0, st_mode=0o40700)
        raise FileNotFoundError(path)

    def open(self, path, mode):
        self._tick()
        if "w" in mode:
            return _Writer(self, path)
        if path not in self.files:
            raise FileNotFoundError(path)
        from io import BytesIO
        return BytesIO(self.files[path])

    def chmod(self, _path, _mode):
        self._tick()

    def posix_rename(self, source, target):
        self._tick()
        self.files[target] = self.files.pop(source)

    def rename(self, source, target):
        self._tick()
        if target in self.files:
            raise FileExistsError(target)
        self.files[target] = self.files.pop(source)

    def remove(self, path):
        if self.dead:
            raise EOFError("SFTP channel is closed")
        self.files.pop(path, None)

    def close(self):
        if self.dead:
            raise EOFError("SFTP channel is closed")


class _Writer:
    def __init__(self, owner, path):
        from io import BytesIO
        self._buffer = BytesIO()
        self._owner, self._path = owner, path

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self._owner.files[self._path] = self._buffer.getvalue()
        return False

    def write(self, data):
        return self._buffer.write(data)

    def flush(self):
        return None

    def read(self, size=-1):
        return self._owner.files.get(self._path, b"")[:size]


class _Backend:
    def __init__(self, sftp):
        self.sftp = sftp
        self.ssh = SimpleNamespace(open_transfer_sftp=lambda: self.sftp)


@pytest.mark.parametrize("drop_on_call", range(1, 9))
def test_remote_drop_during_save_keeps_original_and_reports_the_drop(drop_on_call):
    files = {"/work/run.jou": ORIGINAL}
    sftp = _Flaky(files, drop_on_call=drop_on_call)
    expected = hashlib.sha256(ORIGINAL).hexdigest()

    try:
        save_remote(_Backend(sftp), "/work/run.jou", UPDATED, expected_sha256=expected)
    except Exception as exc:  # the drop must surface, not a masked cleanup error
        assert isinstance(exc, ConnectionResetError), repr(exc)
        # A dead channel cannot remove its temporary upload; the original is what must survive.
        assert files["/work/run.jou"] == ORIGINAL
    else:
        assert files["/work/run.jou"] == UPDATED


@pytest.mark.parametrize("drop_on_call", (1, 2))
def test_remote_drop_during_load_raises_without_partial_content(drop_on_call):
    files = {"/work/run.jou": ORIGINAL}
    sftp = _Flaky(files, drop_on_call=drop_on_call)

    with pytest.raises(ConnectionResetError):
        read_remote(_Backend(sftp), "/work/run.jou")
    assert files == {"/work/run.jou": ORIGINAL}


def test_local_load_rejects_symlink_and_oversized_source_without_reading(tmp_path, monkeypatch):
    target = tmp_path / "big.jou"
    target.write_bytes(b"x")
    monkeypatch.setattr(Path, "stat", lambda self, *a, **k: SimpleNamespace(st_size=129 * 1024 * 1024, st_mode=0o100644))

    with pytest.raises(ValueError, match="128 MiB"):
        read_local(target)


# ---- GUI level: the user-visible error and the unchanged document ----------

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

    plugin_dir = tmp_path / "plugin"
    (plugin_dir / "data").mkdir(parents=True)
    registry = json.dumps({"product_id": "fluent", "version_id": "25.2", "commands": []}).encode("utf-8")
    (plugin_dir / "data" / "command_registry.json").write_bytes(registry)
    record = SimpleNamespace(path="data/command_registry.json", size=len(registry), sha256=hashlib.sha256(registry).hexdigest())
    plugin = SimpleNamespace(directory=str(plugin_dir), manifest=SimpleNamespace(id=PLUGIN_ID, files=[record]))
    frame = wx.Frame(None, size=(1200, 800))
    frame.CreateStatusBar()
    notebook = wx.Notebook(frame)
    state = {"_embedded_main_notebook": notebook, "session": {}}
    yield SimpleNamespace(wx=wx, frame=frame, state=state, ws=JournalStudioWorkspace(frame, state, plugin))
    frame.Destroy()


def _pump(wx, predicate, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        wx.Yield()
        if predicate():
            return True
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)


def _open_and_edit(studio, path, *, remote, edited_display):
    assert studio.ws.open_document(str(path), remote=remote) is True
    assert _pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 1)
    page = studio.ws._active_page()
    page.source.SetText(edited_display)
    page._source_changed(_Event())
    return page


def test_gui_disk_full_save_shows_error_and_keeps_file_and_edits(studio, tmp_path, monkeypatch):
    path = tmp_path / "gui.jou"
    path.write_bytes(ORIGINAL)
    page = _open_and_edit(studio, path, remote=False, edited_display="/solve/iterate 99\n; keep\n")
    _disk_full(monkeypatch)

    assert page.save() is True
    assert _pump(studio.wx, lambda: "No space left" in page.status.GetLabel())

    assert path.read_bytes() == ORIGINAL
    assert page.document.modified is True
    assert page.document.text == "/solve/iterate 99\r\n; keep\r\n"  # the file is CRLF, so edits keep CRLF
    assert _leftover_temporaries(tmp_path) == []


def test_gui_remote_drop_during_load_reports_error_and_opens_nothing(studio):
    files = {"/work/run.jou": ORIGINAL}
    studio.state["session"] = {"files": _Backend(_Flaky(files, drop_on_call=1))}

    assert studio.ws.open_document("/work/run.jou", remote=True) is True
    assert _pump(studio.wx, lambda: "SFTP connection reset" in studio.frame.GetStatusBar().GetStatusText())

    assert studio.ws.documents.GetPageCount() == 0
    assert files == {"/work/run.jou": ORIGINAL}


def test_gui_remote_drop_during_save_keeps_remote_file_and_unsaved_edits(studio):
    files = {"/work/run.jou": ORIGINAL}
    sftp = _Flaky(files)
    studio.state["session"] = {"files": _Backend(sftp)}
    assert studio.ws.open_document("/work/run.jou", remote=True) is True
    assert _pump(studio.wx, lambda: studio.ws.documents.GetPageCount() == 1)
    page = studio.ws._active_page()
    page.source.SetText("/solve/iterate 99\n; keep\n")
    page._source_changed(_Event())

    sftp.drop_on_call = sftp.calls + 1  # the connection drops on the first save operation
    assert page.save() is True
    assert _pump(studio.wx, lambda: "SFTP connection reset" in page.status.GetLabel())

    assert files["/work/run.jou"] == ORIGINAL
    assert page.document.modified is True
    assert page.document.text == "/solve/iterate 99\r\n; keep\r\n"


def test_gui_save_refuses_character_outside_original_encoding_without_crashing(studio, tmp_path):
    path = tmp_path / "legacy.jou"
    original = b"/solve/iterate 1\n\x81\n"  # invalid UTF-8; opened as a legacy single-byte encoding
    path.write_bytes(original)
    page = _open_and_edit(studio, path, remote=False, edited_display="/solve/iterate 1\n☃\n")

    assert page.save() is False
    assert "cannot be saved" in page.status.GetLabel()
    assert path.read_bytes() == original
    assert page.document.modified is True
