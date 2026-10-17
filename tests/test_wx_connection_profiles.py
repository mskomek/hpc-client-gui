"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""
from support.test_wx_connection_profiles_shared import (
    WxConnectionModel,
    _isolated_storage,
    duplicate_profile,
    load_profiles,
    mock,
    normalize_file_manager_settings,
    normalize_jump_host_settings,
    normalize_system_settings,
    pytest,
    storage,
    validate_storage_area,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
def test_wx_add_button_enabled_in_normal_startup(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel

        frame = wx.Frame(None)
        panel_host = build_connection_panel(frame, profiles=[], connect=lambda p: {"connected": True})
        # The host panel is a wx.Panel with exposed controls
        assert hasattr(panel_host, "_wx_connection_add_button")
        add_btn = panel_host._wx_connection_add_button
        assert add_btn.IsEnabled(), "Add Connection must be enabled in normal startup without external callback"
        # Also click should not raise
        # Simulate via model directly: Add is owned, not dependent on callback
        source = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
        assert "if not add_connection:" not in source or "add_button.Enable(False)" not in source or "not add_connection" not in source.split("add_button.Enable")[0][-200:]  # ensure not disabling
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
def test_wx_add_opens_dialog(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel
        from unittest.mock import patch as mock_patch

        frame = wx.Frame(None)
        called = {"ctor": 0, "show": 0, "destroy": 0}

        class FakeDialog:
            def __init__(self, *a, **kw):
                called["ctor"] += 1
                called["opened"] = True
            def ShowModal(self):
                called["show"] += 1
                return wx.ID_CANCEL
            def Destroy(self):
                called["destroy"] += 1

        with mock_patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            host = build_connection_panel(frame, profiles=[])
            add_btn = host._wx_connection_add_button
            assert add_btn.IsEnabled(), "Add must be enabled in normal startup"
            # Dispatch real wx button event -> production Add handler -> dialog
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
            add_btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(5):
                wx.Yield()
            assert called.get("opened") is True
            assert called["ctor"] == 1, "dialog constructor called exactly once"
            assert called["show"] == 1, "ShowModal called exactly once"
            assert called["destroy"] == 1, "Destroy called exactly once"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.integration
def test_add_and_save_persists_and_refreshes(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.services.connection_profile_service import save_profile

        collected = {
            "name": "test-profile",
            "host": "h.example",
            "port": 22,
            "username": "alice",
            "project": "",
            "account": "",
            "password": "",
            "key_path": "",
            "host_key_policy": "accept-new",
            "x11_forwarding": False,
            "cli_allowed": False,
            "keepalive_interval_seconds": 30,
            "transfer_parallelism": 1,
            "ssh_timeout": None,
            "save_password": False,
            "password_prompt_policy": "when-needed",
            "system": normalize_system_settings(None),
            "file_manager": normalize_file_manager_settings(None),
            "jump_host": normalize_jump_host_settings(None),
        }
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=None, plain_password="", save_password=False, prompt_policy="when-needed")
        assert saved["name"] == "test-profile"
        assert load_profiles()[0]["name"] == "test-profile"
        # List refresh would select new profile – check storage
        assert len(load_profiles()) == 1
    finally:
        tmp.cleanup()

@pytest.mark.unit
def test_save_and_connect_invokes_connect_once(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.services.connection_profile_service import save_profile

        collected = {
            "name": "conn-profile",
            "host": "h.example",
            "port": 22,
            "username": "bob",
            "system": normalize_system_settings(None),
            "file_manager": normalize_file_manager_settings(None),
            "jump_host": normalize_jump_host_settings(None),
            "save_password": False,
            "password_prompt_policy": "when-needed",
        }
        calls = []
        def fake_connect(profile):
            calls.append(profile["name"])
            return {"connected": True, "profile_name": profile["name"]}

        model = WxConnectionModel([{"name": "conn-profile", "host": "h.example"}], connect=fake_connect)
        model.select("conn-profile")
        # Simulate save then connect
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            save_profile(collected, initial_profile=None, plain_password="", save_password=False, prompt_policy="when-needed")
        # Now connect via model
        assert model.connect_selected() is True
        assert len(calls) == 1
        assert calls[0] == "conn-profile"
        # Failure to save should prevent connect – simulate validation failure
        bad_collected = {"name": "", "host": "", "port": 22, "username": "", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        try:
            with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
                 mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
                save_profile(bad_collected, initial_profile=None, plain_password="", save_password=False, prompt_policy="when-needed")
            saved_ok = True
        except Exception:
            saved_ok = False
        assert not saved_ok
        # Connect not called again
        assert len(calls) == 1
    finally:
        tmp.cleanup()

@pytest.mark.integration
@pytest.mark.regression
def test_edit_preserves_unknown_and_provenance(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.services.connection_profile_service import save_profile

        existing = {
            "id": "stable-id",
            "name": "lab",
            "host": "h.example",
            "system_template_source": {"kind": "plugin", "plugin_id": "org.example.test", "profile_id": "test"},
            "provider_template": {"name": "Test", "requirements": {"project": {"required": True}}},
            "file_manager": {"local_start_dir": "/tmp/work", "future_key": 42},
            "jump_host": {"enabled": False},
            "plugin_meta": {"custom": {"nested": True}},
            "save_password": False,
        }
        storage.upsert_profile(dict(existing))
        # Simulate edit: change host only, keep rest via save_profile patch
        collected = {
            "name": "lab",
            "host": "new.example.org",
            "port": 22,
            "username": "user",
            "system": normalize_system_settings({"name": "Generic Slurm"}),
            "file_manager": {"local_start_dir": "/tmp/work"},
            "jump_host": {"enabled": False},
            "save_password": False,
            "password_prompt_policy": "when-needed",
        }
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=False, prompt_policy="when-needed")
        assert saved["id"] == "stable-id"
        # unknown survives via merge? plugin_meta was not in collected, but merge should keep
        assert saved["plugin_meta"] == {"custom": {"nested": True}}
        # system_template_source survives? It was not in collected but merge keeps
        assert saved["system_template_source"]["kind"] == "plugin"
        # file_manager future_key survives via helper
        assert saved["file_manager"]["future_key"] == 42
    finally:
        tmp.cleanup()

@pytest.mark.integration
@pytest.mark.regression
def test_rename_removes_old_only_after_success(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.services.connection_profile_service import save_profile

        existing = {"id": "stable-id", "name": "lab", "host": "h.example"}
        storage.upsert_profile(dict(existing))
        collected = {"name": "lab-renamed", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=False, prompt_policy="when-needed", original_name_override="lab")
        assert saved["name"] == "lab-renamed"
        assert len([p for p in load_profiles() if p.get("name") == "lab"]) == 0
        assert len([p for p in load_profiles() if p.get("name") == "lab-renamed"]) == 1
    finally:
        tmp.cleanup()

@pytest.mark.unit
def test_duplicate_uses_naming_and_independent_identity(monkeypatch):
    existing = {"id": "one", "name": "Cluster", "host": "h.example", "username": "alice"}
    profiles = [existing]
    duplicate = duplicate_profile(existing, [p["name"] for p in profiles])
    assert duplicate["name"] == "Cluster (copy)"
    assert duplicate["id"] != existing["id"]
    assert duplicate["host"] == "h.example"
    # Modifying duplicate doesn't affect original
    duplicate["host"] = "other.example"
    assert existing["host"] == "h.example"
    # Second duplicate should increment
    duplicate2 = duplicate_profile(existing, ["Cluster", "Cluster (copy)"])
    assert duplicate2["name"] == "Cluster (copy) 2"

@pytest.mark.gui
@pytest.mark.wx
def test_delete_requires_confirmation_and_cleans(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel

        # Seed storage with profile
        storage.upsert_profile({"name": "to-delete", "host": "h.example", "port": 22, "username": "user"})
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        choices = host._wx_connection_controls["choices"]
        assert choices.FindString("to-delete") != wx.NOT_FOUND
        choices.SetStringSelection("to-delete")
        # Simulate cancel – we mock MessageDialog to return NO, then trigger delete button
        with mock.patch.object(wx, "MessageDialog") as MockDlg:
            inst = MockDlg.return_value
            inst.ShowModal.return_value = wx.ID_NO
            inst.Destroy = mock.Mock()
            delete_btn = host._wx_connection_controls["delete"]
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, delete_btn.GetId())
            delete_btn.GetEventHandler().ProcessEvent(evt)
            wx.Yield()
            # Profile should still exist after cancel
            assert len([p for p in load_profiles() if p.get("name") == "to-delete"]) == 1
        # Confirm removes – mock YES
        with mock.patch.object(wx, "MessageDialog") as MockDlg2:
            inst2 = MockDlg2.return_value
            inst2.ShowModal.return_value = wx.ID_YES
            inst2.Destroy = mock.Mock()
            delete_btn = host._wx_connection_controls["delete"]
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, delete_btn.GetId())
            delete_btn.GetEventHandler().ProcessEvent(evt2)
            wx.Yield()
            assert len([p for p in load_profiles() if p.get("name") == "to-delete"]) == 0
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_saved_password_not_autopopulated(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        # Ensure wx dialog does not populate password field from encrypted storage
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog

        profile = {"name": "sec", "host": "h.example", "username": "user", "save_password": True, "password_enc": "tok", "password_salt": "salt"}
        # Need a parent frame
        frame = wx.Frame(None)
        dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
        # Password ctrl should be empty, not containing decrypted value
        assert dlg.password_ctrl.GetValue() == ""
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.unit
@pytest.mark.wx
def test_storage_add_edit_remove_and_validation(monkeypatch):
    # Validate storage area
    area = {"id": "home", "label": "Home", "kind": "home", "enabled": True, "path_template": "/home/{user}", "access_context": "login-node"}
    assert validate_storage_area(area) is None
    # Invalid path
    bad = dict(area, path_template="bad; rm -rf /")
    assert validate_storage_area(bad) is not None
    # Test wx dialog storage helpers – use dialog's storage_rows via WxConnectionDialog
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        frame = wx.Frame(None)
        dlg = WxConnectionDialog(frame, initial_profile={"name": "lab", "host": "h.example"}, mode="add", on_save=lambda p: True)
        # Simulate add
        dlg._provider_template = {"storage": []}
        dlg.storage_rows = []
        # Mock _show_storage_area_dialog to return a valid area without UI
        with mock.patch("hpc_gui.wx_connection_dialog._show_storage_area_dialog", return_value={"id": "proj", "label": "Proj", "kind": "project", "enabled": True, "path_template": "/proj/{project}", "access_context": "shared", "policy": {}}):
            dlg._add_storage_area()
            assert len(dlg.storage_rows) == 1
            assert dlg.storage_rows[0]["id"] == "proj"
        # Edit
        with mock.patch("hpc_gui.wx_connection_dialog._show_storage_area_dialog", return_value={"id": "proj", "label": "ProjEdited", "kind": "project", "enabled": True, "path_template": "/proj/{project}", "access_context": "shared", "policy": {}}):
            dlg.storage_list.SetSelection(0)
            dlg._edit_storage_area()
            assert dlg.storage_rows[0]["label"] == "ProjEdited"
        # Remove
        dlg.storage_list.SetSelection(0)
        dlg._remove_storage_area()
        assert len(dlg.storage_rows) == 0
        # Home/scratch sync
        dlg.system_name_ctrl.SetValue("Test")
        dlg.home_dir_ctrl.SetValue("/home/{user}")
        dlg.scratch_dir_ctrl.SetValue("/scratch/{user}")
        dlg._legacy_storage_snapshot = {"home_dir": "", "scratch_dir": ""}
        dlg.storage_rows = [{"id": "home", "kind": "home", "path_template": "/old/home"}]
        dlg.home_dir_ctrl.SetValue("/new/home")
        dlg._sync_legacy_storage_paths()
        assert dlg.storage_rows[0]["path_template"] == "/new/home"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.contract
def test_i18n_en_tr_labels():
    from hpc_gui.core.i18n import t, load_language
    # Ensure EN for downstream tests that expect English strings
    load_language("en")
    en_add = t("login.add_connection")
    assert en_add == "Add Connection"
    en_save = t("connection.save")
    assert en_save == "Save"
    en_delete = t("connection.delete_action")
    assert en_delete == "Delete"
    load_language("tr")
    tr_add = t("login.add_connection")
    assert tr_add == "Bağlantı Ekle"
    tr_save = t("connection.save")
    assert tr_save == "Kaydet"
    tr_delete = t("connection.delete_action")
    assert tr_delete == "Sil"
    # No missing keys for new UI
    for key in ["connection.profile_section", "connection.auth_section", "connection.cluster_settings", "connection.advanced_settings",
                "connection.delete_confirm_title", "connection.delete_confirm_message", "connection.host_key_prompt_title",
                "connection.storage_areas", "connection.quota_settings", "connection.jump_enable", "connection.host_key_verification",
                "connection.rename_name_taken"]:
        load_language("en")
        assert t(key) != f"[{key}]"
        load_language("tr")
        assert t(key) != f"[{key}]"
    load_language("en")  # leave EN for tests expecting English (e.g., macOS X11)

@pytest.mark.contract
@pytest.mark.wx
def test_dialog_preserves_unknown_nested_system_fields(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog

        frame = wx.Frame(None)
        initial = {
            "name": "p",
            "host": "h.example",
            "system": {"future_scheduler_key": {"version": 3}},
        }
        dlg = WxConnectionDialog(frame, initial_profile=initial, mode="edit")
        assert dlg._system_form_values()["future_scheduler_key"] == {"version": 3}
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
