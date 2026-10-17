import tempfile
from copy import deepcopy
from pathlib import Path
from unittest import mock
import pytest
wx = pytest.importorskip("wx", reason="wxPython not installed")
from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles, load_settings
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
    yield
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
def _make_master_encrypted_profile(monkeypatch, name="m-test", master="master123", secret="my-secret"):
    """Create a master-encrypted profile in isolated storage."""
    from hpc_gui.core.crypto_master import encrypt_with_master
    enc = encrypt_with_master(master, secret)
    storage.upsert_profile({
        "name": name,
        "host": "h.example",
        "port": 22,
        "username": "user",
        "save_password": True,
        "password_enc": enc.token,
        "password_salt": enc.salt,
    })
def _mock_master_dialog_widgets(master_password="master123", remember=False):
    """Create mock wx widgets for the master-password dialog.
    Returns (fake_dlg, fake_pwd_ctrl, fake_cb, patchers) tuple.
    """
    fake_pwd_ctrl = mock.Mock()
    fake_pwd_ctrl.GetValue.return_value = master_password
    fake_pwd_ctrl.SetFocus = mock.Mock()
    fake_confirm_ctrl = mock.Mock()
    fake_confirm_ctrl.GetValue.return_value = ""

    tc_call = [0]
    def fake_textctrl(*args, **kwargs):
        tc_call[0] += 1
        return fake_pwd_ctrl if tc_call[0] == 1 else fake_confirm_ctrl

    fake_cb = mock.Mock()
    fake_cb.GetValue.return_value = remember

    fake_dlg = mock.Mock()
    fake_dlg.ShowModal.return_value = wx.ID_OK
    fake_dlg.Destroy = mock.Mock()
    fake_sizer = mock.Mock()
    fake_static = mock.Mock()

    return fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static

__all__ = [
    'tempfile',
    'deepcopy',
    'Path',
    'mock',
    'pytest',
    'wx',
    'storage',
    'load_profiles',
    'load_settings',
    'build_connection_panel',
    '_isolated_storage',
    '_clean_wx_after',
    '_make_master_encrypted_profile',
    '_mock_master_dialog_widgets',
]
