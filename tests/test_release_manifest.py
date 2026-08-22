from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_release_manifest as gen  # noqa: E402


class ReleaseManifestTests(unittest.TestCase):
    def test_manifest_inventories_artifacts_with_hashes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            (release_dir / "hpc-client-gui_windows_onedir.zip").write_bytes(b"win")
            (release_dir / "hpc-client-gui_windows_onedir.zip.sha256").write_text("x  y\n")
            (release_dir / "hpc-client-gui-1.0.0-x86_64.AppImage").write_bytes(b"app")
            (release_dir / "CHANGELOG.md").write_text("# notes\n")

            manifest = gen.build_manifest(release_dir, "v1.0.0")

        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["release"], "v1.0.0")
        self.assertIsNone(manifest["sbom"])
        names = {entry["file"] for entry in manifest["artifacts"]}
        self.assertEqual(
            names,
            {
                "CHANGELOG.md",
                "hpc-client-gui-1.0.0-x86_64.AppImage",
                "hpc-client-gui_windows_onedir.zip",
                "hpc-client-gui_windows_onedir.zip.sha256",
            },
        )
        by_name = {entry["file"]: entry for entry in manifest["artifacts"]}
        self.assertEqual(by_name["hpc-client-gui_windows_onedir.zip"]["platform"], "windows")
        self.assertEqual(by_name["hpc-client-gui_windows_onedir.zip"]["format"], "zip")
        self.assertEqual(by_name["hpc-client-gui-1.0.0-x86_64.AppImage"]["platform"], "linux")
        self.assertEqual(by_name["hpc-client-gui-1.0.0-x86_64.AppImage"]["format"], "appimage")
        self.assertEqual(by_name["hpc-client-gui_windows_onedir.zip.sha256"]["format"], "checksum")

    def test_sha256_matches_hashlib_for_known_content(self) -> None:
        import hashlib
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blob.bin"
            path.write_bytes(b"deterministic-bytes")
            self.assertEqual(gen.sha256_file(path), hashlib.sha256(b"deterministic-bytes").hexdigest())

    def test_json_output_is_stable_and_secret_free(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            release_dir = Path(tmp)
            (release_dir / "tool.deb").write_bytes(b"deb")
            manifest = gen.build_manifest(release_dir, "v2.0.0")

        encoded = json.dumps(manifest, indent=2)
        self.assertNotIn(str(Path(tempfile.gettempdir())), encoded)


if __name__ == "__main__":
    unittest.main()
