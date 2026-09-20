"""Shared profile/security service tests – regression before/while extracting."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

from hpc_gui.config import storage
from hpc_gui.services.connection_profile_service import (
    decrypt_profile_password,
    resolve_password_for_connect,
    save_profile,
)
from hpc_gui.core.secret_store import KEYCHAIN_SERVICE


class ConnectionProfileServiceTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        patch = mock.patch.object(Path, "home", return_value=Path(self._dir.name))
        patch.start()
        self.addCleanup(patch.stop)
        # Ensure clean config
        try:
            storage.save_config({"profiles": [], "settings": {}})
        except Exception:
            pass

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_save_patches_without_dropping_unknown_keys(self):
        existing = {
            "id": "stable-id",
            "name": "lab",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "system_template_source": {"kind": "plugin", "plugin_id": "org.hpcclient.truba", "profile_id": "truba"},
            "file_manager": {"local_start_dir": "/tmp/work", "future_key": 1},
            "jump_host": {"enabled": False},
            "plugin_meta": {"custom": {"nested": True}},
            "save_password": True,
            "password_enc": "token",
            "password_salt": "salt",
        }
        storage.upsert_profile(dict(existing))
        collected = {
            "name": "lab",
            "host": "edited.example.org",
            "port": 22,
            "username": "user",
            "system": {"name": "Generic Slurm"},
            "file_manager": {"local_start_dir": "/tmp/work"},
            "jump_host": {"enabled": False},
            "save_password": True,
            "password_prompt_policy": "when-needed",
        }
        # keep existing secret: no plain password, save true -> keep
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=True, prompt_policy="when-needed", ask_master=lambda confirm: None)
        self.assertEqual(saved["host"], "edited.example.org")
        self.assertEqual(saved["plugin_meta"], {"custom": {"nested": True}})
        self.assertEqual(saved["file_manager"]["future_key"], 1)
        self.assertEqual(saved["password_enc"], "token")
        self.assertEqual(saved.get("password"), "")

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_disable_save_removes_secret(self):
        existing = {"id": "stable-id", "name": "lab", "host": "h.example", "save_password": True, "password_enc": "token", "password_salt": "salt"}
        storage.upsert_profile(dict(existing))
        collected = {"name": "lab", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=False, prompt_policy="when-needed")
        self.assertNotIn("password_enc", saved)
        self.assertNotIn("password_salt", saved)
        self.assertEqual(saved.get("password"), "")

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_rename_preserves_id_and_removes_old(self):
        existing = {"id": "stable-id", "name": "lab", "host": "h.example"}
        storage.upsert_profile(dict(existing))
        collected = {"name": "lab-renamed", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=False, prompt_policy="when-needed", original_name_override="lab")
        self.assertEqual(saved["name"], "lab-renamed")
        self.assertEqual(saved["id"], "stable-id")
        self.assertIsNone(storage.load_profile_by_name("lab") if hasattr(storage, "load_profile_by_name") else next((p for p in storage.load_profiles() if p.get("name")=="lab"), None))
        self.assertIsNotNone(next((p for p in storage.load_profiles() if p.get("name")=="lab-renamed"), None))

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_only_one_secret_scheme_survives(self):
        # Simulate saving with keychain available – old dpapi should be removed
        existing = {"name": "lab", "host": "h.example", "password_dpapi": "oldtoken"}
        storage.upsert_profile(dict(existing))
        collected = {"name": "lab", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": True, "password_prompt_policy": "when-needed"}
        fake_entries = {}
        def fake_protect(plain, ref=None):
            rid = ref or "new-ref"
            fake_entries[rid] = plain
            return rid
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=True), \
             mock.patch("hpc_gui.services.connection_profile_service.protect_keychain_secret", side_effect=fake_protect), \
             mock.patch("hpc_gui.services.connection_profile_service.delete_keychain_secret"):
            saved = save_profile(collected, initial_profile=existing, plain_password="s3cret", save_password=True, prompt_policy="when-needed")
        self.assertIn("password_keychain_ref", saved)
        self.assertNotIn("password_dpapi", saved)
        self.assertNotIn("password_enc", saved)

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_plaintext_never_persisted(self):
        existing = None
        collected = {"name": "lab", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": True, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False), \
             mock.patch("hpc_gui.core.crypto_master.encrypt_with_master") as mock_enc:
            from hpc_gui.core.crypto_master import EncryptedSecret
            mock_enc.return_value = EncryptedSecret(token="tok", salt="salt")
            saved = save_profile(collected, initial_profile=existing, plain_password="mysecret", save_password=True, prompt_policy="when-needed", ask_master=lambda confirm: "master123")
        self.assertEqual(saved.get("password"), "")
        self.assertNotEqual(saved.get("password"), "mysecret")
        # token/salt should exist, not plaintext
        self.assertIn("password_enc", saved)
        self.assertNotIn("mysecret", str(saved))

    @pytest.mark.integration
    @pytest.mark.wx
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_mfa_transient_not_stored(self):
        pytest.importorskip("wx")
        from hpc_gui.services.connection_controller import KeyboardInteractiveRequest
        from hpc_gui.wx_connection import WxConnectionModel

        storage.upsert_profile({
            "name": "lab", "host": "h.example", "port": 22,
            "username": "user", "password": "",
        })
        stored_before = storage.load_profiles()
        response = "temporary-mfa-731942"
        request = KeyboardInteractiveRequest(
            "SSH authentication", "Enter the verification code",
            ("Verification code:",), (False,),
        )
        received = []

        def answer_keyboard_interactive(actual_request):
            received.append(actual_request)
            return [response]

        model = WxConnectionModel(
            profiles=stored_before,
            keyboard_interactive=answer_keyboard_interactive,
        )
        assert model.answer_keyboard_interactive(request) == [response]
        assert received == [request]
        assert model.profiles == stored_before
        assert storage.load_profiles() == stored_before
        assert response not in repr(storage.load_profiles())

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_unknown_field_preservation(self):
        existing = {"name": "lab", "host": "h.example", "unknown_future": {"nested": True}, "save_password": False}
        storage.upsert_profile(dict(existing))
        collected = {"name": "lab", "host": "newhost.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=False, prompt_policy="when-needed")
        self.assertEqual(saved["unknown_future"], {"nested": True})
        self.assertEqual(saved["host"], "newhost.example")

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_decrypt_keychain(self):
        # Simulate keychain secret
        ref = "test-ref"
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=True):
            # Mock keyring
            import sys
            import types
            entries = {(KEYCHAIN_SERVICE, ref): "secret123"}
            fake = types.SimpleNamespace(
                get_keyring=lambda: object(),
                set_password=lambda s,u,v: entries.__setitem__((s,u), v),
                get_password=lambda s,u: entries.get((s,u)),
                delete_password=lambda s,u: entries.pop((s,u), None),
            )
            with mock.patch.dict(sys.modules, {"keyring": fake}):
                with mock.patch("hpc_gui.core.secret_store.keychain_available", return_value=True):
                    # Use real protect to ensure we have entry
                    # Already entries has secret
                    profile = {"password_keychain_ref": ref}
                    result = decrypt_profile_password(profile, allow_prompt=False)
                    self.assertEqual(result, "secret123")

    @pytest.mark.unit
    @pytest.mark.regression
    def test_typed_password_precedes_saved_secret(self):
        from hpc_gui.core.crypto_master import encrypt_with_master

        enc = encrypt_with_master("master123", "old-secret")
        profile = {
            "name": "p",
            "host": "h.example",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        }
        ask_master = mock.Mock()

        result = resolve_password_for_connect(
            profile,
            typed_password="new-temporary-secret",
            ask_master=ask_master,
        )

        self.assertEqual(result, "new-temporary-secret")
        ask_master.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_rename_onto_existing_name_raises_and_preserves_both(self):
        # DEF-W17-001: renaming beta -> alpha must not create duplicate rows.
        storage.upsert_profile({"name": "alpha", "host": "h1.example", "port": 22, "username": "u1"})
        storage.upsert_profile({"name": "beta", "host": "h2.example", "port": 22, "username": "u2"})
        beta = next(p for p in storage.load_profiles() if p.get("name") == "beta")
        alpha_before = next(p for p in storage.load_profiles() if p.get("name") == "alpha")
        collected = {
            "name": "alpha",
            "host": "h2x.example",
            "port": 22,
            "username": "u2",
            "save_password": False,
            "password_prompt_policy": "when-needed",
        }
        with self.assertRaises(ValueError):
            save_profile(
                collected,
                initial_profile=beta,
                plain_password="",
                save_password=False,
                prompt_policy="when-needed",
                original_name_override="beta",
            )
        rows = storage.load_profiles()
        self.assertEqual(len([p for p in rows if p.get("name") == "alpha"]), 1)
        self.assertEqual(len([p for p in rows if p.get("name") == "beta"]), 1)
        alpha_after = next(p for p in rows if p.get("name") == "alpha")
        beta_after = next(p for p in rows if p.get("name") == "beta")
        self.assertEqual(alpha_after["host"], "h1.example")
        self.assertEqual(alpha_after["id"], alpha_before["id"])
        self.assertEqual(beta_after["host"], "h2.example")
        self.assertEqual(beta_after["id"], beta["id"])

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_add_duplicate_name_upserts_in_place_by_design(self):
        # FIND-W17-003 lock-in: Add-path upsert-by-name stays allowed and
        # converges to exactly one row with a stable id (Qt parity).
        first = save_profile(
            {"name": "alpha", "host": "h1.example", "port": 22, "username": "u1"},
            plain_password="",
            save_password=False,
        )
        second = save_profile(
            {"name": "alpha", "host": "h9.example", "port": 22, "username": "u9"},
            initial_profile=None,
            plain_password="",
            save_password=False,
        )
        rows = storage.load_profiles()
        self.assertEqual(len([p for p in rows if p.get("name") == "alpha"]), 1)
        survivor = next(p for p in rows if p.get("name") == "alpha")
        self.assertEqual(survivor["host"], "h9.example")
        self.assertEqual(survivor["id"], first["id"])
        self.assertEqual(second["id"], first["id"])

    @pytest.mark.unit
    @pytest.mark.regression
    @pytest.mark.semantic
    def test_add_returns_stored_stable_id(self):
        # DEF-W17-002: the Add path must return the same stable identity that
        # is persisted on disk (edit callers already receive it via merge).
        saved = save_profile(
            {"name": "fresh", "host": "h.example", "port": 22, "username": "user"},
            initial_profile=None,
            plain_password="",
            save_password=False,
        )
        self.assertTrue(saved.get("id"))
        stored = next(p for p in storage.load_profiles() if p.get("name") == "fresh")
        self.assertEqual(saved["id"], stored["id"])
        self.assertEqual(storage.get_last_profile_name(), "fresh")

if __name__ == "__main__":
    unittest.main()
