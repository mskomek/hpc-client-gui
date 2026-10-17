import time
from threading import Event
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.services.app_updater import UpdateRelease
from hpc_gui.wx_updater_view import WxUpdateDialog, _format_bytes, show_update_available
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
@pytest.fixture(autouse=True)
def _reset_update_language():
    from hpc_gui.core.i18n import current_language, load_language

    previous = current_language()
    load_language("en")
    yield
    load_language(previous if previous in {"en", "tr"} else "tr")

__all__ = [
    'time',
    'Event',
    'pytest',
    'wx',
    'UpdateRelease',
    'WxUpdateDialog',
    '_format_bytes',
    'show_update_available',
    '_make_release',
    '_WrapperDialog',
    '_reset_update_language',
]
