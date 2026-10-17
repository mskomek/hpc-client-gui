
pytest_plugins = ('support.test_wx_connection_71_2_shared',)
"""Wave 71.2 — wx Connection final closure tests.

Covers: blank-name Save & Connect, real WxConnectionDialog button event,
master-password wx event chain (success/cancel/wrong), Test Cluster
master-password chain, typed password precedence.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_2_shared import (
    _isolated_storage,
    _seed_master_dpapi_cache,
    load_profiles,
    mock,
    pytest,
    storage,
    wx,
)


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
