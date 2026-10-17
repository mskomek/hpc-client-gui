import tempfile
from pathlib import Path
from unittest import mock
import pytest
wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")
from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import t, load_language
from hpc_gui.services.connection_profile_service import (
    resolve_password_for_connect,
)
from hpc_gui.services.connection_controller import ConnectionController
from hpc_gui.wx_connection import WxConnectionModel, build_connection_panel, ssh_info_from_profile
def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    # Patch both Path.home and the app_data_dir helpers so config and plugins
    # use the same isolated temp dir regardless of which helper a module
    # imported. Without this, conftest's tmp_path for plugins and our
    # Path.home temp would diverge and load_profiles would look in the wrong
    # place when tests are run as part of a large suite.
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Also patch the core and config helpers directly
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        # plugins uses its own helper but conftest already patches it to tmp_path;
        # we override to use the same fake_dir for consistency when tests run
        # as part of the large suite.
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp
@pytest.fixture(autouse=True)
def _clean_wx_after():
    yield
    # Ensure any wx windows left open by a failing test are destroyed so the
    # next test's wx.App.Get() does not see a polluted app with open windows
    # (which causes UnregisterClass failures and order-dependent flakes).
    try:
        app = wx.GetApp()
        if app is not None:
            for win in list(wx.GetTopLevelWindows()):
                try:
                    win.Destroy()
                except Exception:
                    pass
            # Process pending destroys
            for _ in range(5):
                try:
                    wx.Yield()
                except Exception:
                    break
    except Exception:
        pass

__all__ = [
    'tempfile',
    'Path',
    'mock',
    'pytest',
    'wx',
    'storage',
    'load_profiles',
    't',
    'load_language',
    'resolve_password_for_connect',
    'ConnectionController',
    'WxConnectionModel',
    'build_connection_panel',
    'ssh_info_from_profile',
    '_isolated_storage',
    '_clean_wx_after',
]
