"""Shared profile/security service tests – regression before/while extracting."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hpc_gui.config import storage
from hpc_gui.services.connection_profile_service import save_profile, decrypt_profile_password
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
             mock.patch("hpc_gui.services.connection_profile_service.delete_keychain_secret") as mock_del:
            saved = save_profile(collected, initial_profile=existing, plain_password="s3cret", save_password=True, prompt_policy="when-needed")
        self.assertIn("password_keychain_ref", saved)
        self.assertNotIn("password_dpapi", saved)
        self.assertNotIn("password_enc", saved)

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

    def test_mfa_transient_not_stored(self):
        # Ensure save doesn't store keyboard-interactive responses anywhere
        collected = {"name": "lab", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=None, plain_password="", save_password=False, prompt_policy="when-needed")
        # No field should contain MFA
        for key, val in saved.items():
            if isinstance(val, str):
                self.assertNotIn("mfa-code", val.lower())
                self.assertNotIn("otp", val.lower())

    def test_unknown_field_preservation(self):
        existing = {"name": "lab", "host": "h.example", "unknown_future": {"nested": True}, "save_password": False}
        storage.upsert_profile(dict(existing))
        collected = {"name": "lab", "host": "newhost.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved = save_profile(collected, initial_profile=existing, plain_password="", save_password=False, prompt_policy="when-needed")
        self.assertEqual(saved["unknown_future"], {"nested": True})
        self.assertEqual(saved["host"], "newhost.example")

    def test_decrypt_keychain(self):
        # Simulate keychain secret
        ref = "test-ref"
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=True):
            # Mock keyring
            import sys, types
            entries = {(KEYCHAIN_SERVICE, ref): "secret123"}
            fake = types.SimpleNamespace(
                get_keyring=lambda: object(),
                set_password=lambda s,u,v: entries.__setitem__((s,u), v),
                get_password=lambda s,u: entries.get((s,u)),
                delete_password=lambda s,u: entries.pop((s,u), None),
            )
            with mock.patch.dict(sys.modules, {"keyring": fake}):
                with mock.patch("hpc_gui.core.secret_store.keychain_available", return_value=True):
                    from hpc_gui.core.secret_store import protect_keychain_secret
                    # Use real protect to ensure we have entry
                    # Already entries has secret
                    profile = {"password_keychain_ref": ref}
                    result = decrypt_profile_password(profile, allow_prompt=False)
                    self.assertEqual(result, "secret123")

if __name__ == "__main__":
    unittest.main()
