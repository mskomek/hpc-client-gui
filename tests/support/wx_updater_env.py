"""Tests for wx update flow per spec 37 — real wx events, fixed changelog, real progress."""


import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]

from hpc_gui.services.app_updater import UpdateRelease


def _make_release(version="1.9.0", body="- Demo update\n- New features\n- Fixes", size=184*1024*1024):
    return UpdateRelease(version=version, tag=f"v{version}", zip_name="a.zip", zip_url="https://example.com/a.zip", sha_name="a.sha", sha_url="https://example.com/a.sha", html_url="https://example.com", body=body, size=size)


class _WrapperDialog:
    class _Wx:
        ID_OK = 5100
        ID_CANCEL = 5101

    wx = _Wx()

    def __init__(self, _parent, _release):
        self.destroyed = False

    def _build_for_state(self, _state):
        pass

    def _start_download(self):
        pass

    def Destroy(self):
        self.destroyed = True
