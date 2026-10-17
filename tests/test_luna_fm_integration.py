"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations
from support.test_luna_fm_integration_shared import (
    Path,
    _base_profile,
    load_profiles,
    merge_profile_patch,
    mock,
    normalize_file_manager_settings,
    normalize_jump_host_settings,
    pytest,
    sys,
    tempfile,
    unittest,
    update_profile_file_manager_settings,
    upsert_profile,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

@pytest.mark.integration
class ProfileCompatibilityMatrixTests(unittest.TestCase):
    """Part A: fixture matrix survives edit/save round trips."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = mock.patch.object(Path, "home")
        home.start().return_value = Path(self._tmp.name)
        self.addCleanup(home.stop)

    def _round_trip(self, profile: dict, edits: dict) -> dict:
        upsert_profile(dict(profile))
        stored = next(
            p for p in load_profiles() if p.get("name") == profile["name"]
        )
        upsert_profile(merge_profile_patch(stored, edits))
        return next(p for p in load_profiles() if p.get("id") == profile["id"])

    def test_legacy_basic_profile_round_trip(self) -> None:
        saved = self._round_trip(_base_profile("legacy"), {"host": "new"})
        self.assertEqual(saved["id"], "id-legacy")
        self.assertEqual(saved["host"], "new")

    def test_encrypted_password_preserved_unless_disabled(self) -> None:
        profile = _base_profile("enc")
        profile.update({"password_enc": "tok", "password_salt": "salt"})
        saved = self._round_trip(profile, {"username": "user2"})
        self.assertEqual(saved["password_enc"], "tok")
        self.assertEqual(saved["password_salt"], "salt")
        # Disabling saved password intentionally clears the secret fields
        # (the exact keys LoginWidget.remove_keys lists).
        upsert_profile(dict(profile))
        stored = next(p for p in load_profiles() if p.get("name") == "enc")
        merged = merge_profile_patch(
            stored,
            {"save_password": False},
            remove_keys=("password_dpapi", "password_enc", "password_salt"),
        )
        upsert_profile(merged)
        saved = load_profiles()[0]
        self.assertNotIn("password_enc", saved)

    def test_plugin_provenance_survives_unrelated_edit(self) -> None:
        profile = _base_profile("plug")
        profile["system_template_source"] = {"kind": "plugin", "plugin_id": "p"}
        saved = self._round_trip(profile, {"port": 2222})
        self.assertEqual(saved["system_template_source"]["plugin_id"], "p")

    def test_unknown_top_level_and_nested_keys_survive(self) -> None:
        profile = _base_profile("future")
        profile["vendor_extension"] = {"custom": [1, 2]}
        profile["file_manager"] = {
            "local_start_dir": "/w",
            "mystery_key": {"deep": True},
        }
        profile["jump_host"] = {
            **normalize_jump_host_settings({"enabled": True, "host": "gw"}),
            "future_jump_field": 7,
        }
        saved = self._round_trip(profile, {"username": "u2"})
        self.assertEqual(saved["vendor_extension"], {"custom": [1, 2]})
        self.assertEqual(saved["file_manager"]["mystery_key"], {"deep": True})
        self.assertEqual(saved["jump_host"]["future_jump_field"], 7)
        self.assertTrue(saved["jump_host"]["enabled"])

    def test_malformed_optional_data_normalizes_without_corruption(self) -> None:
        profile = _base_profile("broken")
        profile["file_manager"] = "not-a-dict"
        profile["jump_host"] = 12345
        upsert_profile(dict(profile))
        stored = load_profiles()[0]
        fm = normalize_file_manager_settings(stored.get("file_manager"))
        jump = normalize_jump_host_settings(stored.get("jump_host"))
        self.assertFalse(fm["sync"]["enabled"])
        self.assertFalse(jump["enabled"])
        # Raw values stay untouched on disk until an intentional save.
        self.assertEqual(stored.get("file_manager"), "not-a-dict")

    def test_comparison_enabled_persists_per_profile(self) -> None:
        upsert_profile(_base_profile("cmp"))
        updated = update_profile_file_manager_settings(
            "cmp", {"comparison_enabled": True}
        )
        self.assertTrue(updated["comparison_enabled"])
        self.assertTrue(load_profiles()[0]["file_manager"]["comparison_enabled"])

    def test_renamed_profile_keeps_stable_id_and_state(self) -> None:
        profile = _base_profile("old-name")
        profile["file_manager"] = normalize_file_manager_settings(
            {"local_start_dir": "/keep"}
        )
        upsert_profile(dict(profile))
        stored = load_profiles()[0]
        merged = merge_profile_patch(stored, {"name": "new-name"})
        upsert_profile(merged)
        profiles = load_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "new-name")
        self.assertEqual(profiles[0]["id"], "id-old-name")
        self.assertEqual(profiles[0]["file_manager"]["local_start_dir"], "/keep")

    def test_merge_never_writes_plaintext_password_from_secrets(self) -> None:
        profile = _base_profile("secret")
        profile.update({"password_enc": "tok", "password_salt": "s"})
        upsert_profile(dict(profile))
        merged = merge_profile_patch(load_profiles()[0], {"username": "u3"})
        self.assertEqual(merged.get("password", ""), "")
