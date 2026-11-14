"""Wave 71.2.6 - Test Cluster master-password chain.

Split out of test_wx_connection_71_2.py to keep both modules under the
500-line source limit; fixtures are repeated so each module stands alone.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import current_language, set_language


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
@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_cluster_self_test_master_password_chain(monkeypatch):
    """Test Cluster: saved master-encrypted profile -> edit dialog -> Test Cluster -> real resolver -> decrypt.

    Does NOT mock resolve_password_for_connect or decrypt_with_master.
    Pre-seeds DPAPI cache so _make_master_ask returns master without wx dialog.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "cluster-secret")
        storage.upsert_profile({
            "name": "m-cluster",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        _seed_master_dpapi_cache(monkeypatch, "master123")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cluster")
        before = [dict(p) for p in load_profiles()]

        dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
        dlg.host_ctrl.SetValue("h.example")
        dlg.username_ctrl.SetValue("user")
        dlg.password_ctrl.SetValue("")

        captured = {}
        def fake_self_test(info, provider=None, project="", account=""):
            captured["pwd"] = info.password
            class R:
                status = "PASS"
                sections = []
            return R()

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
             mock.patch("wx.MessageBox"):
            with mock.patch.object(dlg.btn_test_cluster, "Enable"), mock.patch.object(dlg.btn_test_cluster, "SetLabel"):
                dlg._test_cluster()
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if captured.get("pwd"):
                        break
                assert captured.get("pwd") == "cluster-secret"
        after = [dict(p) for p in load_profiles()]
        assert before == after, "Test Cluster must not mutate storage"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
