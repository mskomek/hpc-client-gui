"""The startup splash offers only a real, newer release (never a demo fake)."""
from pathlib import Path

import pytest

SHELL = Path(__file__).resolve().parents[1] / "src" / "hpc_gui" / "wx_shell.py"


def test_splash_update_check_has_no_demo_release():
    source = SHELL.read_text(encoding="utf-8")
    assert "Sahte güncelleme" not in source
    assert "example.com" not in source
    assert "release=_found" in source


def test_update_available_dialog_uses_the_given_release(monkeypatch):
    pytest.importorskip("wx")
    from hpc_gui import wx_updater_view as view
    from hpc_gui.services.app_updater import UpdateRelease

    seen = {}

    class FakeDialog:
        def __init__(self, parent, release):
            seen["release"] = release

        def _build_for_state(self, state):
            pass

        def _start_download(self, *a, **k):
            pass

        def ShowModal(self):
            pass

        def Destroy(self):
            pass

    monkeypatch.setattr(view, "WxUpdateDialog", FakeDialog)
    real = UpdateRelease(version="2.0.0", tag="v2.0.0", zip_name="z.zip", zip_url="https://github.com/x/z.zip",
                         sha_name="z.sha256", sha_url="https://github.com/x/z.sha256",
                         html_url="https://github.com/x/releases/tag/v2.0.0", body="real notes")
    assert view.show_update_available(None, "1.5.9", "2.0.0", "real notes", release=real) is False
    assert seen["release"] is real
