import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hpc_gui.services import remote_navigation_store as store_mod  # noqa: E402


class _FakeSecretStore:
    """Reversible stand-in for DPAPI so the tests run on any platform."""

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def protect_secret(plaintext: str) -> str:
        return plaintext.encode("utf-8").hex()

    @staticmethod
    def unprotect_secret(token: str) -> str:
        return bytes.fromhex(token).decode("utf-8")


class RemoteNavigationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = mock.patch.object(Path, "home")
        import tempfile

        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        home = self._tmp.start()
        home.return_value = Path(self._dir.name)
        self.addCleanup(self._tmp.stop)
        secret = mock.patch.object(store_mod, "secret_store", _FakeSecretStore)
        secret.start()
        self.addCleanup(secret.stop)
        store_mod._INSTANCES.clear()

    def _store(self, profile_id: str = "profile-a"):
        return store_mod.RemoteNavigationStore(profile_id)

    def test_favorites_survive_a_reload(self):
        store = self._store()
        store.add_favorite("/arf/scratch/mkomek/", "directory")
        store.add_favorite("/arf/scratch/mkomek/run.slurm", "file")
        reloaded = self._store()
        paths = [item["path"] for item in reloaded.favorites()]
        self.assertEqual(paths, ["/arf/scratch/mkomek", "/arf/scratch/mkomek/run.slurm"])
        self.assertEqual(reloaded.favorites()[1]["kind"], "file")

    def test_duplicate_favorite_is_ignored_and_toggle_removes(self):
        store = self._store()
        store.add_favorite("/work/project")
        store.add_favorite("/work/project/")
        self.assertEqual(len(store.favorites()), 1)
        self.assertFalse(store.toggle_favorite("/work/project"))
        self.assertEqual(store.favorites(), [])

    def test_history_dedupes_newest_first_and_caps(self):
        store = self._store()
        for index in range(store_mod.MAX_HISTORY + 5):
            store.record_visit(f"/data/dir{index}")
        store.record_visit("/data/dir10")
        history = [item["path"] for item in store.history()]
        self.assertEqual(history[0], "/data/dir10")
        self.assertEqual(len(history), store_mod.MAX_HISTORY)
        self.assertEqual(len(set(history)), len(history))

    def test_clear_history_keeps_favorites(self):
        store = self._store()
        store.add_favorite("/keep/me")
        store.record_visit("/forget/me")
        store.clear_history()
        self.assertEqual(store.history(), [])
        self.assertEqual(len(self._store().favorites()), 1)

    def test_profiles_do_not_share_state(self):
        self._store("profile-a").add_favorite("/arf/scratch/mkomek")
        self.assertEqual(self._store("profile-b").favorites(), [])

    def test_remote_paths_are_not_readable_on_disk(self):
        store = self._store()
        store.add_favorite("/arf/scratch/mkomek/secret-project")
        store.record_visit("/arf/scratch/mkomek/secret-project")
        raw = store_mod._state_path("profile-a").read_bytes()
        self.assertNotIn(b"/arf/scratch", raw)
        self.assertNotIn(b"secret-project", raw)

    def test_tampered_file_does_not_leak_or_crash(self):
        store = self._store()
        store.add_favorite("/arf/scratch/mkomek")
        path = store_mod._state_path("profile-a")
        path.write_bytes(b"HPCNAV1\nnot-really-encrypted")
        self.assertEqual(self._store().favorites(), [])

    def test_plaintext_state_is_never_accepted(self):
        path = store_mod._state_path("profile-a")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps({"favorites": [{"path": "/etc"}]}).encode("utf-8"))
        self.assertEqual(self._store().favorites(), [])

    def test_delete_removes_the_state_file(self):
        store = self._store()
        store.add_favorite("/arf/scratch/mkomek")
        store_mod.delete_profile_navigation("profile-a")
        self.assertFalse(store_mod._state_path("profile-a").exists())

    def test_shared_instance_per_profile(self):
        first = store_mod.navigation_store_for_profile("profile-a")
        second = store_mod.navigation_store_for_profile("profile-a")
        self.assertIs(first, second)

    def test_unavailable_secure_storage_disables_the_feature(self):
        with mock.patch.object(store_mod.secret_store, "is_available", return_value=False), \
             mock.patch.object(store_mod, "_fernet", return_value=None):
            self.assertFalse(store_mod.is_available())
            self.assertIsNone(store_mod.navigation_store_for_profile("profile-a"))


if __name__ == "__main__":
    unittest.main()
