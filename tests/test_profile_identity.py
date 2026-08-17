import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hpc_gui.config import storage  # noqa: E402
from hpc_gui.services import remote_navigation_store as store_mod  # noqa: E402


class ProfileIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        home = mock.patch.object(Path, "home")
        home.start().return_value = Path(self._dir.name)
        self.addCleanup(home.stop)

    def _write_legacy_config(self) -> None:
        path = Path(self._dir.name) / ".truba_slurm_gui" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"profiles": [{"name": "TRUBA", "host": "levrek1"}], "last_profile": "TRUBA"}),
            encoding="utf-8",
        )

    def test_legacy_profiles_gain_a_stable_id_once(self) -> None:
        self._write_legacy_config()
        first = storage.load_profiles()[0]["id"]
        self.assertTrue(first)
        self.assertEqual(storage.load_profiles()[0]["id"], first)
        self.assertEqual(storage.load_profiles()[0]["host"], "levrek1")

    def test_rename_keeps_the_same_id(self) -> None:
        self._write_legacy_config()
        profile = dict(storage.load_profiles()[0])
        original_id = profile["id"]
        storage.upsert_profile(dict(profile, name="TRUBA Ana Hesap"))
        profiles = storage.load_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "TRUBA Ana Hesap")
        self.assertEqual(profiles[0]["id"], original_id)
        self.assertEqual(storage.get_profile_id("TRUBA Ana Hesap"), original_id)

    def test_delete_takes_the_private_state_with_it(self) -> None:
        self._write_legacy_config()
        profile_id = storage.load_profiles()[0]["id"]
        with mock.patch.object(store_mod, "secret_store", _FakeSecretStore):
            store_mod.RemoteNavigationStore(profile_id).add_favorite("/arf/scratch/mkomek")
            self.assertTrue(store_mod._state_path(profile_id).exists())
            storage.delete_profile("TRUBA")
        self.assertEqual(storage.load_profiles(), [])
        self.assertFalse(store_mod._state_path(profile_id).exists())


class _FakeSecretStore:
    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def protect_secret(plaintext: str) -> str:
        return plaintext.encode("utf-8").hex()

    @staticmethod
    def unprotect_secret(token: str) -> str:
        return bytes.fromhex(token).decode("utf-8")


if __name__ == "__main__":
    unittest.main()
