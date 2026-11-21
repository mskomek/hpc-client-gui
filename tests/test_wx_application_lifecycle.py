"""wx app event-loop policy for the production shell."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

from hpc_gui import wx_application


pytestmark = pytest.mark.unit


def test_production_app_exits_after_main_frame_deletion(monkeypatch):
    policies = []
    top_windows = []
    app = SimpleNamespace(
        SetExitOnFrameDelete=policies.append,
        SetAppName=lambda _name: None,
        SetTopWindow=top_windows.append,
        MainLoop=lambda: None,
    )
    frame = SimpleNamespace(Show=lambda: None, Raise=lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "wx",
        SimpleNamespace(App=lambda _redirect: app, version=lambda: "test-wx"),
    )
    monkeypatch.setattr(
        wx_application,
        "environment_without_qt_graphics",
        lambda: dict(os.environ),
    )
    monkeypatch.setattr(wx_application, "load_saved_language", lambda _lang: None)
    monkeypatch.setattr(wx_application, "system_default_language", lambda: "en")
    monkeypatch.setattr(wx_application, "record_terminal_event", lambda *_a, **_kw: None)
    monkeypatch.delenv("HPC_GUI_PACKAGED_SMOKE_OUTPUT", raising=False)
    monkeypatch.setattr("hpc_gui.config.storage.load_profiles", lambda: [])
    monkeypatch.setattr(
        "hpc_gui.wx_splash.create_startup_splash",
        lambda *_a, **_kw: SimpleNamespace(Show=lambda: None, Destroy=lambda: None),
    )
    monkeypatch.setattr(
        "hpc_gui.wx_startup_flow.start_startup_flow",
        lambda _app, _splash, on_complete: on_complete(),
    )

    assert wx_application.run_wx_application(
        lambda *_a, **_kw: (frame, object(), {}), None
    ) == 0
    assert policies == [True]
    assert top_windows[-1] is frame
    assert frame._wx_shell_exit_main_loop_on_close is True
