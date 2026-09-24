"""W25 focused tests: transfer retry state, SHA-256 verify hook, disconnect
invalidation, embedded-panel retry rows, and editor Save As/external-change.

Requirement map:
- HPC-W06-XFER-010: retry creates a new clear operation state (engine
  re-announces queued; embedded panel evicts stale failed/completed rows).
- HPC-W06-XFER-012: concurrent transfers keep isolated UI rows.
- HPC-W06-XFER-013: disconnect cancels in-flight transfer sessions.
- HPC-W06-XFER-017: local save detects external modification/deletion.
- HPC-W06-XFER-019: Save As to an existing target prompts; cancel is safe.
- HPC-W06-TODO-043: opt-in SHA-256 verification (verified/failed/unsupported).
"""

from __future__ import annotations

import time

import pytest

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController


def test_engine_retry_failed_reannounces_queued() -> None:
    events: list[tuple[str, str]] = []
    attempts = 0

    def run(item, progress):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary")
        progress(1, 1)

    item = TransferItem("upload", "a", "/remote/a")
    controller = TransferSessionController(
        [item], run, on_queue=lambda event, it: events.append((event, it.src))
    )
    controller.engine.start()
    assert controller.engine.wait(2)
    assert len(controller.engine.failed) == 1
    assert controller.engine.retry_failed() == 1
    assert controller.engine.failed == []
    assert controller.engine.pending == [item]
    assert ("queued", "a") in events
    controller.engine.start()
    assert controller.engine.wait(2)
    assert controller.engine.completed == [item]


@pytest.mark.unit
def test_session_verify_mismatch_fails_transfer() -> None:
    def run(item, progress):
        progress(1, 1)

    def verify(item):
        raise RuntimeError("SHA-256 verification failed for /remote/a: local=x, remote=y")

    item = TransferItem("upload", "a", "/remote/a")
    controller = TransferSessionController([item], run, verify=verify)
    controller.set_checksum_enabled(True)
    controller.engine.start()
    assert controller.engine.wait(2)
    assert controller.engine.completed == []
    assert len(controller.engine.failed) == 1
    assert "SHA-256" in controller.engine.failed[0][1]


@pytest.mark.unit
def test_session_verify_unsupported_passes_and_disabled_skips() -> None:
    calls: list[str] = []

    def run(item, progress):
        progress(1, 1)

    item = TransferItem("download", "/remote/b", "b")
    passthrough = TransferSessionController(
        [item], run, verify=lambda it: calls.append(it.src)
    )
    passthrough.set_checksum_enabled(True)
    passthrough.engine.start()
    assert passthrough.engine.wait(2)
    assert passthrough.engine.completed == [item]
    assert calls == ["/remote/b"]

    skipped_calls: list[str] = []

    def strict_verify(item):
        skipped_calls.append(item.src)
        raise AssertionError("must not run while disabled")

    skipped = TransferSessionController([item], run, verify=strict_verify)
    skipped.engine.start()
    assert skipped.engine.wait(2)
    assert skipped.engine.completed == [item]
    assert skipped_calls == []


@pytest.mark.unit
def test_cancel_transfer_sessions_cancels_and_tolerates_junk() -> None:
    from hpc_gui.wx_shell import _cancel_transfer_sessions

    cancelled: list[str] = []

    class _Session:
        def cancel(self):
            cancelled.append("session")

    class _EngineOnly:
        def __init__(self):
            from hpc_gui.services.transfer_controller import TransferController

            self.engine = TransferController([], lambda item, progress: None)

    engine_only = _EngineOnly()
    state = {"transfer_sessions": {_Session(), engine_only, object(), None}}
    assert _cancel_transfer_sessions(state) == 2
    assert cancelled == ["session"]
    assert _cancel_transfer_sessions({}) == 0
    assert _cancel_transfer_sessions(None) == 0


@pytest.mark.unit
def test_verify_transfer_item_off_unsupported_verified_failed(tmp_path, monkeypatch) -> None:
    import hpc_gui.config.storage as storage
    from hpc_gui.services.transfer_integrity import VerificationState
    from hpc_gui.wx_shell import _verify_transfer_item

    local = tmp_path / "payload.bin"
    local.write_bytes(b"w25-integrity-payload")

    class _NoHash:
        pass

    monkeypatch.setattr(storage, "get_transfer_checksum_verification_enabled", lambda *a, **k: False)
    assert _verify_transfer_item(_NoHash(), TransferItem("upload", str(local), "/remote/p.bin")) is VerificationState.OFF

    monkeypatch.setattr(storage, "get_transfer_checksum_verification_enabled", lambda *a, **k: True)
    assert _verify_transfer_item(_NoHash(), TransferItem("upload", str(local), "/remote/p.bin")) is VerificationState.UNSUPPORTED

    import hashlib

    # Backend whose probe itself fails -> honest UNSUPPORTED passthrough.
    class _ExplodingHash:
        def sha256(self, path):
            raise OSError("sha256sum missing")

    assert _verify_transfer_item(_ExplodingHash(), TransferItem("download", "/remote/p.bin", str(local))) is VerificationState.UNSUPPORTED

    digest = hashlib.sha256(local.read_bytes()).hexdigest()

    class _MatchingHash:
        def sha256(self, path):
            assert path == "/remote/p.bin"
            return digest

    assert _verify_transfer_item(_MatchingHash(), TransferItem("upload", str(local), "/remote/p.bin")) is VerificationState.VERIFIED

    class _MismatchHash:
        def sha256(self, path):
            return "0" * 64

    with pytest.raises(RuntimeError, match="SHA-256 verification failed"):
        _verify_transfer_item(_MismatchHash(), TransferItem("upload", str(local), "/remote/p.bin"))


@pytest.mark.unit
def test_wx_settings_checksum_checkbox_persists_to_stored_setting(tmp_path, monkeypatch) -> None:
    import hpc_gui.config.storage as storage
    from hpc_gui.wx_settings import WxSettingsModel, persist_transfer_checksum_to_storage

    monkeypatch.setattr(storage, "_config_path", lambda: tmp_path / "config.json")
    assert storage.get_transfer_checksum_verification_enabled() is False
    assert persist_transfer_checksum_to_storage(WxSettingsModel({"transfer_checksum": True})) is True
    assert storage.get_transfer_checksum_verification_enabled() is True
    assert persist_transfer_checksum_to_storage(WxSettingsModel({})) is False
    assert storage.get_transfer_checksum_verification_enabled() is False


wx = pytest.importorskip("wx")


def _pump(app, predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def wx_app():
    from hpc_gui.core.i18n import load_language

    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def _click(control):
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId()))


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_embedded_panel_retry_clears_failed_rows(wx_app) -> None:
    from hpc_gui.wx_transfer_workspace import build_transfers_panel

    parent = wx.Frame(None)
    panel = build_transfers_panel(parent)
    controls = panel._wx_transfer_controls
    attempts = 0

    def run(item, progress):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary")
        progress(1, 1)

    item = TransferItem("upload", "a.txt", "/remote/a.txt")
    controller = TransferSessionController(
        [item],
        run,
        on_queue=panel._wx_transfer_queue,
        on_progress=panel._wx_transfer_progress,
    )
    panel._wx_transfer_set_controller(controller)
    controller.engine.start()
    assert controller.engine.wait(3)
    _pump(wx_app, lambda: controls["failed"].GetItemCount() == 1)
    assert controls["queue"].GetItemCount() == 0

    assert controller.engine.retry_failed() == 1
    _pump(
        wx_app,
        lambda: controls["failed"].GetItemCount() == 0 and controls["queue"].GetItemCount() == 1,
    )
    controller.engine.start()
    assert controller.engine.wait(3)
    _pump(
        wx_app,
        lambda: controls["queue"].GetItemCount() == 0 and controls["completed"].GetItemCount() == 1,
    )
    assert controls["failed"].GetItemCount() == 0
    parent.Destroy()
    wx_app.ProcessPendingEvents()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_embedded_panel_tracks_concurrent_transfers_in_isolated_rows(wx_app) -> None:
    from hpc_gui.wx_transfer_workspace import build_transfers_panel

    parent = wx.Frame(None)
    panel = build_transfers_panel(parent)
    controls = panel._wx_transfer_controls
    import threading

    started = {name: threading.Event() for name in ("first", "second")}
    release = {name: threading.Event() for name in ("first", "second")}

    def run(item, progress):
        progress(0, 2)
        started[item.src].set()
        assert release[item.src].wait(5)
        progress(2, 2)

    items = [TransferItem("upload", "first", "/remote/first"), TransferItem("upload", "second", "/remote/second")]
    controller = TransferSessionController(
        items,
        run,
        parallel_limit=2,
        on_queue=panel._wx_transfer_queue,
        on_progress=panel._wx_transfer_progress,
    )
    panel._wx_transfer_set_controller(controller)
    controller.engine.start()
    assert started["first"].wait(5) and started["second"].wait(5)
    _pump(wx_app, lambda: controls["queue"].GetItemCount() == 2)
    # Complete the first transfer while the second is still running: the
    # finished row must leave the queue without disturbing the other row.
    release["first"].set()
    _pump(
        wx_app,
        lambda: controls["queue"].GetItemCount() == 1 and controls["completed"].GetItemCount() == 1,
    )
    release["second"].set()
    assert controller.engine.wait(5)
    _pump(
        wx_app,
        lambda: controls["queue"].GetItemCount() == 0 and controls["completed"].GetItemCount() == 2,
    )
    assert {controller.engine.completed[0].src, controller.engine.completed[1].src} == {"first", "second"}
    parent.Destroy()
    wx_app.ProcessPendingEvents()


def _open_editor(path, content, **callbacks):
    from hpc_gui.wx_editor_view import show_editor

    show_editor(path=path, content=content, **callbacks)
    title = path.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if path else "untitled.sh"
    return [window for window in wx.GetTopLevelWindows() if window.GetTitle() == title][-1]


def _settle_done(frame, app):
    _pump(app, lambda: not frame._wx_editor_state["in_flight"])


def _close_clean(frame, app):
    from hpc_gui.wx_editor import WxEditorModel  # noqa: F401  (keeps editor import surface stable)

    model = frame._wx_editor_model
    active = model.controller.active
    if active is not None and active.dirty:
        frame._wx_editor_controls["editor"].SetValue(active.saved_content)
    frame.Close()
    app.ProcessPendingEvents()
    wx.Yield()


@pytest.mark.gui
@pytest.mark.wx
def test_editor_normal_save_needs_no_prompt(wx_app, tmp_path, monkeypatch) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("orig", encoding="utf-8")
    frame = _open_editor(str(doc), "orig", is_local=True)
    controls = frame._wx_editor_controls

    def _boom(*args, **kwargs):
        raise AssertionError("no prompt expected for an unchanged-target save")

    monkeypatch.setattr(wx, "MessageBox", _boom)
    controls["editor"].SetValue("edited")
    _click(controls["save"])
    _settle_done(frame, wx_app)
    assert doc.read_text(encoding="utf-8") == "edited"
    assert not frame._wx_editor_model.controller.active.dirty
    assert controls["status"].GetLabel() == ""
    _close_clean(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_editor_save_as_cancel_is_side_effect_free(wx_app, tmp_path, monkeypatch) -> None:
    from hpc_gui.core.i18n import t

    doc = tmp_path / "doc.txt"
    target = tmp_path / "target.txt"
    doc.write_text("orig", encoding="utf-8")
    target.write_text("target-orig", encoding="utf-8")
    frame = _open_editor(str(doc), "orig", is_local=True)
    controls = frame._wx_editor_controls
    header = frame._wx_editor_header["path"]
    header.SetValue(str(target))
    controls["editor"].SetValue("edited")
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.ID_NO)
    _click(controls["save"])
    app = wx_app
    app.ProcessPendingEvents()
    assert not frame._wx_editor_state["in_flight"]
    assert target.read_text(encoding="utf-8") == "target-orig"
    assert doc.read_text(encoding="utf-8") == "orig"
    active = frame._wx_editor_model.controller.active
    assert active.dirty and active.path == str(doc)
    assert controls["status"].GetLabel() == t("editor.save_as_cancelled")
    _close_clean(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_editor_save_as_overwrite_writes_and_adopts_path(wx_app, tmp_path, monkeypatch) -> None:
    doc = tmp_path / "doc.txt"
    target = tmp_path / "target.txt"
    doc.write_text("orig", encoding="utf-8")
    target.write_text("target-orig", encoding="utf-8")
    frame = _open_editor(str(doc), "orig", is_local=True)
    controls = frame._wx_editor_controls
    header = frame._wx_editor_header["path"]
    header.SetValue(str(target))
    controls["editor"].SetValue("edited")
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.ID_YES)
    _click(controls["save"])
    _settle_done(frame, wx_app)
    assert target.read_text(encoding="utf-8") == "edited"
    assert doc.read_text(encoding="utf-8") == "orig"
    active = frame._wx_editor_model.controller.active
    assert active.path == str(target) and not active.dirty
    assert header.GetValue() == str(target)
    _close_clean(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_editor_external_change_cancel_preserves_disk_and_edits(wx_app, tmp_path, monkeypatch) -> None:
    from hpc_gui.core.i18n import t

    doc = tmp_path / "doc.txt"
    doc.write_text("orig", encoding="utf-8")
    frame = _open_editor(str(doc), "orig", is_local=True)
    controls = frame._wx_editor_controls
    doc.write_text("EXTERNAL", encoding="utf-8")
    controls["editor"].SetValue("edited")
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.ID_NO)
    _click(controls["save"])
    wx_app.ProcessPendingEvents()
    assert not frame._wx_editor_state["in_flight"]
    assert doc.read_text(encoding="utf-8") == "EXTERNAL"
    assert frame._wx_editor_model.controller.active.dirty
    assert controls["status"].GetLabel() == t("editor.external_change_cancelled")
    _close_clean(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_editor_external_change_overwrite_writes(wx_app, tmp_path, monkeypatch) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("orig", encoding="utf-8")
    frame = _open_editor(str(doc), "orig", is_local=True)
    controls = frame._wx_editor_controls
    doc.write_text("EXTERNAL", encoding="utf-8")
    controls["editor"].SetValue("edited")
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.ID_YES)
    _click(controls["save"])
    _settle_done(frame, wx_app)
    assert doc.read_text(encoding="utf-8") == "edited"
    assert not frame._wx_editor_model.controller.active.dirty
    _close_clean(frame, wx_app)


@pytest.mark.gui
@pytest.mark.wx
def test_editor_remote_save_as_prompts_and_redirects(wx_app, monkeypatch) -> None:
    writes: list[tuple[str, str]] = []
    prompts: list[str] = []

    def fake_save(path, content):
        writes.append((path, content))

    def fake_exists(path):
        return path == "/remote/new.txt"

    def factory(document):
        return {"save_remote": fake_save, "target_exists": fake_exists, "on_submit": None, "on_run": None}

    def fake_box(*args, **kwargs):
        prompts.append(args[0] if args else "")
        return wx.ID_YES

    monkeypatch.setattr(wx, "MessageBox", fake_box)
    frame = _open_editor("/remote/doc.txt", "hello", is_local=False, action_factory=factory)
    controls = frame._wx_editor_controls
    frame._wx_editor_header["path"].SetValue("/remote/new.txt")
    controls["editor"].SetValue("new content")
    _click(controls["save"])
    _settle_done(frame, wx_app)
    assert prompts and "/remote/new.txt" in prompts[0]
    assert writes == [("/remote/new.txt", "new content")]
    active = frame._wx_editor_model.controller.active
    assert active.path == "/remote/new.txt" and not active.dirty
    _close_clean(frame, wx_app)
