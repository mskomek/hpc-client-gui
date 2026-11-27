from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from mock_hpc_files import MockRemoteFilesBackend

from support.wx_remote_file_test_support import _Dialog, _browser, _pump


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_remote_chmod_accepts_four_digit_octal_mode(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    chmod_calls = []
    frame = _browser(wx_app, backend, chmod=lambda path, mode: chmod_calls.append((path, mode)))
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("1755"))

    frame._wx_remote_run_action("chmod", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])

    assert chmod_calls == [("/work/a.txt", 0o1755)]


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_remote_chmod_rejects_invalid_octal_mode(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    errors = []
    frame = _browser(
        wx_app,
        backend,
        chmod=lambda *_args: pytest.fail("invalid mode reached backend"),
    )
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("1988"))
    monkeypatch.setattr(
        wx,
        "MessageBox",
        lambda message, *_args, **_kwargs: errors.append(message) or wx.OK,
    )

    frame._wx_remote_run_action("chmod", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])

    assert errors
