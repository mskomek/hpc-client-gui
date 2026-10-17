import tempfile
from pathlib import Path
from unittest import mock
import pytest
wx = pytest.importorskip("wx", reason="wxPython not installed")
from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import current_language, set_language
from hpc_gui.wx_connection import build_connection_panel
def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp
def _seed_master_dpapi_cache(monkeypatch, master_password):
    """Pre-seed the DPAPI master-password cache so _master_ask_factory returns
    the master without opening a wx dialog.
    """
    import hpc_gui.config.storage as cfg_storage
    fake_token = f"dpapi-{master_password}"

    def fake_load_settings():
        return {"master_password_dpapi": fake_token}

    def fake_unprotect(token):
        if token == fake_token:
            return master_password
        raise ValueError("decrypt failed")

    monkeypatch.setattr(cfg_storage, "load_settings", fake_load_settings)
    monkeypatch.setattr("hpc_gui.core.secret_store.unprotect_secret", fake_unprotect)
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.unprotect_secret", fake_unprotect)
@pytest.fixture(autouse=True)
def _clean_wx_after():
    original_language = current_language()
    set_language("en")
    yield
    try:
        set_language(original_language)
    finally:
        try:
            app = wx.GetApp()
            if app is not None:
                for win in list(wx.GetTopLevelWindows()):
                    try:
                        win.Destroy()
                    except Exception:
                        pass
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
    'current_language',
    'set_language',
    'build_connection_panel',
    '_isolated_storage',
    '_seed_master_dpapi_cache',
    '_clean_wx_after',
]
