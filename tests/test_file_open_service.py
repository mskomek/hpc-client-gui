from pathlib import Path
import time

import pytest

from hpc_gui.services.file_open import (
    decode_text,
    detect_file_type,
    remember_smart_open,
    reset_smart_open_preferences,
    smart_open_preferences,
)


def _destroy_wx_app(wx, app):
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    app.Destroy()


@pytest.mark.unit
def test_classifies_common_text_and_special_files_without_running_scripts():
    assert detect_file_type("job.sh").category == "text"
    assert detect_file_type("job.sh").executable
    assert detect_file_type("plot.PNG", b"\x89PNG\r\n\x1a\n").category == "image"
    assert detect_file_type("report.pdf", b"%PDF-1.7").category == "document"
    assert detect_file_type("result.npy").category == "data"
    assert detect_file_type("table.csv").category == "data"
    assert detect_file_type("table.csv").editable
    assert detect_file_type("bundle.tar.gz").category == "archive"
    assert detect_file_type("unknown.sample").category == "unknown"


@pytest.mark.unit
def test_binary_named_as_text_is_not_decoded_and_text_encodings_are_supported():
    with pytest.raises(ValueError, match="binary"):
        decode_text(b"\x89PNG\r\n\x1a\n\x00", name="misnamed.txt")
    assert decode_text(b"\xef\xbb\xbfhello") == "hello"
    assert decode_text("café".encode("cp1252")) == "café"
    assert decode_text("hello".encode("utf-16")) == "hello"


@pytest.mark.unit
def test_smart_open_preferences_persist_and_reset(monkeypatch, tmp_path: Path):
    from hpc_gui.config import storage

    monkeypatch.setattr(storage, "_config_path", lambda: tmp_path / "config.json")
    remember_smart_open("PNG", "system")
    assert smart_open_preferences() == {".png": "system"}
    reset_smart_open_preferences()
    assert smart_open_preferences() == {}


@pytest.mark.unit
def test_remote_mock_text_reader_rejects_binary_payload():
    from hpc_gui.services.files_mock import MockFilesBackend

    backend = MockFilesBackend()
    backend._files["/broken.txt"] = b"\x89PNG\r\n\x1a\n"
    with pytest.raises(ValueError, match="binary"):
        backend.read_text_document("/broken.txt")


@pytest.mark.unit
def test_mock_remote_document_preserves_legacy_encoding_on_save():
    from hpc_gui.services.files_mock import MockFilesBackend

    backend = MockFilesBackend()
    backend._files["/legacy.txt"] = "café".encode("cp1252")
    content, encoding = backend.read_text_document("/legacy.txt")
    assert (content, encoding) == ("café", "cp1252")
    backend.write_text_document("/legacy.txt", "résumé", encoding)
    assert backend._files["/legacy.txt"] == "résumé".encode("cp1252")


@pytest.mark.unit
def test_executable_local_file_waits_for_user_action(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from hpc_gui import wx_smart_file_open

    target = tmp_path / "unsafe.exe"
    target.write_bytes(b"MZ\x00\x01")
    choices = []
    opened = []
    monkeypatch.setattr(wx_smart_file_open, "choose_smart_open", lambda *_a, **_k: choices.append(True))
    monkeypatch.setattr(wx_smart_file_open, "_open_system", lambda *_a: opened.append(True))
    wx = SimpleNamespace(MessageBox=lambda *_a, **_k: 0, OK=1, ICON_ERROR=2, YES=1)
    wx_smart_file_open.open_local_file(wx, None, target, lambda *_a: opened.append("editor"))
    assert choices == [True]
    assert opened == []


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.parametrize(
    ("name", "payload"),
    (("plot.png", b"\x89PNG\r\n\x1a\n"), ("report.pdf", b"%PDF-1.7")),
)
def test_local_binary_double_click_uses_smart_choice_without_editor(tmp_path, monkeypatch, name, payload):
    wx = pytest.importorskip("wx")

    from hpc_gui.core.i18n import load_language
    from hpc_gui import wx_smart_file_open
    from hpc_gui.wx_local_files import show_local_files

    load_language("en")
    wx_app = wx.App.Get() or wx.App(False)
    target = tmp_path / name
    target.write_bytes(payload + b"x" * 16)
    opened_editor = []
    opened_system = []
    monkeypatch.setattr(wx_smart_file_open, "choose_smart_open", lambda *_a, **_k: "system")
    monkeypatch.setattr(wx_smart_file_open, "_open_system", lambda _wx, _parent, path: opened_system.append(path))
    show_local_files(path=tmp_path, open_editor=opened_editor.append)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        wx_app.ProcessPendingEvents()
        listing = frame._wx_local_controls["listing"]
        row = next((index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == target.name), None)
        if row is not None:
            break
        wx.MilliSleep(5)
    assert row is not None
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, listing.GetId())
    event.SetIndex(row)
    listing.ProcessEvent(event)
    assert opened_editor == []
    assert opened_system == [target.resolve()]
    _destroy_wx_app(wx, wx_app)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.parametrize("name", ("notes.txt", "config.json"))
def test_local_text_double_click_opens_editor(name, tmp_path):
    wx = pytest.importorskip("wx")

    from hpc_gui.core.i18n import load_language
    from hpc_gui.wx_local_files import show_local_files

    load_language("en")
    wx_app = wx.App.Get() or wx.App(False)
    target = tmp_path / name
    target.write_text("text", encoding="utf-8")
    opened = []
    show_local_files(path=tmp_path, open_editor=opened.append)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        wx_app.ProcessPendingEvents()
        listing = frame._wx_local_controls["listing"]
        row = next((index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == name), None)
        if row is not None:
            break
        wx.MilliSleep(5)
    assert row is not None
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, listing.GetId())
    event.SetIndex(row)
    listing.ProcessEvent(event)
    assert opened == [str(target.resolve())]
    _destroy_wx_app(wx, wx_app)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.parametrize("name", ("notes.txt", "config.json"))
def test_remote_text_double_click_uses_internal_editor(name):
    wx = pytest.importorskip("wx")

    from hpc_gui.core.i18n import load_language
    from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
    from hpc_gui.wx_remote_files_view import show_remote_files

    load_language("en")
    wx_app = wx.App.Get() or wx.App(False)
    target = f"/work/{name}"
    content = "{\"status\": \"ok\"}" if name.endswith(".json") else "remote text"
    opened = []
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=lambda _path: [RemoteEntry(target, name=name, size=len(content))],
        operation=lambda *_args: None,
        read_text=lambda _path: content,
        read_text_document=lambda _path: (content, "utf-8"),
        open_editor=lambda path, text: opened.append((path, text)),
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        wx_app.ProcessPendingEvents()
        listing = frame._wx_remote_controls["listing"]
        row = next((index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == name), None)
        if row is not None:
            break
        wx.MilliSleep(5)
    assert row is not None
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, listing.GetId())
    event.SetIndex(row)
    listing.ProcessEvent(event)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and not opened:
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(5)
    assert opened == [(target, content)]
    _destroy_wx_app(wx, wx_app)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "payload"),
    (("plot.png", b"\x89PNG\r\n\x1a\n"), ("report.pdf", b"%PDF-1.7")),
)
def test_remote_external_open_uses_unique_copy_and_cleans_cancelled_download(monkeypatch, name, payload):
    from types import SimpleNamespace

    from hpc_gui import wx_smart_file_open

    opened = []
    monkeypatch.setattr(wx_smart_file_open, "_open_system", lambda _wx, _parent, path: opened.append(path))
    state = {"cancel": False}

    class Progress:
        def __init__(self, *_args, **_kwargs):
            pass

        def Update(self, *_args):
            return (not state["cancel"], False)

        def Destroy(self):
            pass

    wx = SimpleNamespace(
        ProgressDialog=Progress,
        PD_APP_MODAL=1,
        PD_CAN_ABORT=2,
        PD_AUTO_HIDE=4,
        YES=1,
        MessageBox=lambda *_a, **_k: 1,
        YieldIfNeeded=lambda: None,
        OK=1,
        ICON_INFORMATION=2,
        ICON_ERROR=4,
    )

    def download(_remote, local_path, progress_cb):
        if state["cancel"]:
            time.sleep(0.03)
        Path(local_path).write_bytes(payload + b"copy")
        if not progress_cb(len(payload) + 4, len(payload) + 4):
            raise InterruptedError("download cancelled")

    wx_smart_file_open.open_remote_with_system(wx, None, f"/remote/{name}", len(payload) + 4, download)
    assert len(opened) == 1
    assert opened[0].read_bytes() == payload + b"copy"

    opened.clear()
    state["cancel"] = True
    wx_smart_file_open.open_remote_with_system(wx, None, f"/remote/{name}", len(payload) + 4, download)
    assert opened == []
