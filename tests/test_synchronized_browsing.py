"""FM-02 tests: synchronized browsing mapping service and widget behavior."""

from __future__ import annotations
from support.test_synchronized_browsing_shared import (
    Path,
    SyncRoots,
    local_to_remote,
    normalize_file_manager_settings,
    normalize_local_root,
    normalize_remote_root,
    os,
    patch_file_manager_settings,
    pytest,
    remote_to_local,
    sys,
    unittest,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

class LocalMappingTests(unittest.TestCase):
    pytestmark = [pytest.mark.unit, pytest.mark.semantic]

    WINDOWS_ROOTS = SyncRoots(
        local_root=r"C:\CFD\new_dpler",
        remote_root="/arf/scratch/user/new_dpler",
    )
    POSIX_ROOTS = SyncRoots(
        local_root="/home/user/work",
        remote_root="/arf/home/user/work",
    )

    def test_local_root_maps_to_remote_root(self) -> None:
        self.assertEqual(
            local_to_remote(r"C:\CFD\new_dpler", self.WINDOWS_ROOTS),
            "/arf/scratch/user/new_dpler",
        )

    def test_one_nested_level(self) -> None:
        self.assertEqual(
            local_to_remote(r"C:\CFD\new_dpler\case1", self.WINDOWS_ROOTS),
            "/arf/scratch/user/new_dpler/case1",
        )
        self.assertEqual(
            remote_to_local(
                "/arf/scratch/user/new_dpler/case1", self.WINDOWS_ROOTS
            ),
            os.path.normpath(r"C:\CFD\new_dpler\case1"),
        )

    def test_deep_nested_both_directions(self) -> None:
        local = r"C:\CFD\new_dpler\a\b\c\d"
        remote = "/arf/scratch/user/new_dpler/a/b/c/d"
        mapped = local_to_remote(local, self.WINDOWS_ROOTS)
        self.assertEqual(mapped, remote)
        back = remote_to_local(remote, self.WINDOWS_ROOTS)
        self.assertEqual(Path(back), Path(local))

    def test_prefix_collision_is_not_contained(self) -> None:
        self.assertIsNone(local_to_remote(r"C:\CFD\new_dpler2", self.WINDOWS_ROOTS))

    def test_outside_root_returns_none(self) -> None:
        self.assertIsNone(local_to_remote(r"C:\Other\dir", self.WINDOWS_ROOTS))

    @pytest.mark.windows
    def test_windows_case_insensitive_containment_preserves_text(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows-only case rule")
        mapped = local_to_remote(r"c:\cfd\NEW_DPLER\Case", self.WINDOWS_ROOTS)
        self.assertEqual(mapped, "/arf/scratch/user/new_dpler/Case")

    @pytest.mark.windows
    def test_different_drives_return_none(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows-only drive rule")
        self.assertIsNone(local_to_remote(r"D:\CFD\new_dpler", self.WINDOWS_ROOTS))

    def test_dot_segments_are_normalized(self) -> None:
        self.assertEqual(
            local_to_remote(r"C:\CFD\.\new_dpler\sub", self.WINDOWS_ROOTS),
            "/arf/scratch/user/new_dpler/sub",
        )

    def test_dotdot_must_not_escape_root(self) -> None:
        self.assertIsNone(
            local_to_remote(r"C:\CFD\new_dpler\..\escape", self.WINDOWS_ROOTS)
        )

    def test_unicode_and_spaces_survive(self) -> None:
        roots = SyncRoots(r"C:\work\projem", "/remote/projem")
        mapped = local_to_remote(r"C:\work\projem\dosya adı - kopya", roots)
        self.assertEqual(mapped, "/remote/projem/dosya adı - kopya")

    def test_trailing_separators_do_not_mismatch(self) -> None:
        roots = SyncRoots(
            r"C:\CFD\new_dpler" + os.sep, "/arf/scratch/user/new_dpler/"
        )
        self.assertEqual(
            local_to_remote(r"C:\CFD\new_dpler\sub", roots),
            "/arf/scratch/user/new_dpler/sub",
        )

    def test_posix_local_roots_stay_case_sensitive_off_windows(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX-only exact-case rule")
        self.assertEqual(
            local_to_remote("/home/user/work/Sub", self.POSIX_ROOTS),
            "/arf/home/user/work/Sub",
        )

class RemoteMappingTests(unittest.TestCase):
    pytestmark = [pytest.mark.unit, pytest.mark.semantic]

    ROOTS = SyncRoots(
        local_root=r"C:\CFD\new_dpler",
        remote_root="/arf/scratch/user",
    )

    def test_remote_root_maps_to_local_root(self) -> None:
        self.assertEqual(
            Path(remote_to_local("/arf/scratch/user", self.ROOTS)),
            Path(r"C:\CFD\new_dpler"),
        )

    def test_nested_maps_back(self) -> None:
        self.assertEqual(
            Path(remote_to_local("/arf/scratch/user/runs/r1", self.ROOTS)),
            Path(r"C:\CFD\new_dpler\runs\r1"),
        )

    def test_remote_prefix_collision_rejected(self) -> None:
        self.assertIsNone(
            remote_to_local("/arf/scratch/user2/run", self.ROOTS)
        )

    def test_outside_remote_root_rejected(self) -> None:
        self.assertIsNone(remote_to_local("/arf/home/user", self.ROOTS))

    def test_dotdot_escape_rejected(self) -> None:
        self.assertIsNone(
            remote_to_local("/arf/scratch/user/../../etc", self.ROOTS)
        )

    def test_slash_root_pair_works(self) -> None:
        roots = SyncRoots(r"C:\mirror", "/")
        self.assertEqual(
            remote_to_local("/arf/x", roots), os.path.normpath(r"C:\mirror\arf\x")
        )
        self.assertEqual(
            local_to_remote(r"C:\mirror\arf\x", roots), "/arf/x"
        )

    def test_trailing_slashes_do_not_mismatch(self) -> None:
        self.assertEqual(
            remote_to_local("/arf/scratch/user/", self.ROOTS),
            remote_to_local("/arf/scratch/user", self.ROOTS),
        )

    def test_normalize_helpers(self) -> None:
        self.assertEqual(normalize_remote_root("/a/b/"), "/a/b")
        self.assertEqual(normalize_remote_root(""), "/")
        raw = "C:\\a\\b\\" if os.name == "nt" else "/a/b"
        expected = Path("C:\\a\\b") if os.name == "nt" else Path("/a/b")
        self.assertEqual(Path(normalize_local_root(raw)), expected)

class SyncSchemaTests(unittest.TestCase):
    pytestmark = [pytest.mark.contract, pytest.mark.semantic]

    def test_malformed_sync_gives_defaults(self) -> None:
        settings = normalize_file_manager_settings({"sync": "junk"})
        sync = settings["sync"]
        self.assertFalse(sync["enabled"])
        self.assertEqual(sync["local_root"], "")
        self.assertEqual(sync["remote_root"], "")

    def test_enabled_normalizes_to_real_bool(self) -> None:
        settings = normalize_file_manager_settings({"sync": {"enabled": 1}})
        self.assertIs(settings["sync"]["enabled"], False)
        settings = normalize_file_manager_settings({"sync": {"enabled": True}})
        self.assertIs(settings["sync"]["enabled"], True)

    def test_patch_preserves_sync_siblings_and_unknown_keys(self) -> None:
        existing = {
            "local_start_dir": "/tmp/w",
            "future_key": {"x": 1},
            "sync": {"enabled": True, "local_root": "/L", "remote_root": "/R"},
        }
        patched = patch_file_manager_settings(existing, {"sync": {"enabled": False}})
        self.assertFalse(patched["sync"]["enabled"])
        self.assertEqual(patched["sync"]["local_root"], "/L")
        self.assertEqual(patched["sync"]["remote_root"], "/R")
        self.assertEqual(patched["local_start_dir"], "/tmp/w")
        self.assertEqual(patched["future_key"], {"x": 1})
