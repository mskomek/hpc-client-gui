import tempfile
from copy import deepcopy
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
def _make_profile(name="p", master=None, secret="s3cret"):
    """Create profile; if master given, encrypt with it."""
    if master:
        from hpc_gui.core.crypto_master import encrypt_with_master
        enc = encrypt_with_master(master, secret)
        storage.upsert_profile({
            "name": name, "host": "h.example", "port": 22, "username": "user",
            "save_password": True, "password_enc": enc.token, "password_salt": enc.salt,
        })
    else:
        storage.upsert_profile({
            "name": name, "host": "h.example", "port": 22, "username": "user",
        })

__all__ = [
    'tempfile',
    'deepcopy',
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
    '_clean_wx_after',
    '_make_profile',
]
