from __future__ import annotations

import re
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import release_linux as rl

real_read_text = rl.Path.read_text


class ResolveVersionTest(unittest.TestCase):
    def test_sources_agree(self) -> None:
        version = rl.resolve_version()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_mismatch_raises(self) -> None:
        # Force the three version sources to disagree and assert a clear error.
        real_read_text = rl.Path.read_text
        pyproject = rl.REPO_ROOT / "pyproject.toml"
        init = rl.SRC_DIR / "hpc_gui" / "__init__.py"
        cli = rl.SRC_DIR / "hpc_gui" / "cli" / "main.py"

        def _fake_read(self, *args, **kwargs):
            if self == pyproject:
                return 'version = "9.9.9"\n'
            if self == init:
                return "__version__ = '1.0.0'\n"
            if self == cli:
                return 'CLI_VERSION = "1.0.0"\n'
            return real_read_text(self, *args, **kwargs)

        with mock.patch.object(rl.Path, "read_text", _fake_read):
            with self.assertRaises(rl.PackagingError):
                rl.resolve_version()

    def test_artifact_name(self) -> None:
        self.assertEqual(
            rl.appimage_artifact_name("1.2.4"),
            "hpc-client-gui-1.2.4-x86_64.AppImage",
        )


class RequiredFilesTest(unittest.TestCase):
    def test_help_files_inventory(self) -> None:
        files = rl.required_release_files()
        names = {p.name for p in files if p.is_file()}
        self.assertIn("HELP_tr.md", names)
        self.assertIn("HELP_en.md", names)
        self.assertIn("CLI_GUIDE_tr.md", names)
        self.assertIn("CLI_GUIDE_en.md", names)

    def test_validate_required_files_passes(self) -> None:
        rl.validate_required_files()

    def test_missing_file_raises(self) -> None:
        with mock.patch.object(
            rl, "required_release_files", return_value=[Path("does/not/exist.md")]
        ):
            with self.assertRaises(rl.PackagingError):
                rl.validate_required_files()


class AppImageDefinitionTest(unittest.TestCase):
    def test_desktop_entry_valid(self) -> None:
        rl.validate_desktop_entry()
        text = (rl.APPIMAGE_DEF_DIR / rl.DESKTOP_ENTRY_NAME).read_text(encoding="utf-8")
        self.assertIn("[Desktop Entry]", text)
        self.assertIn("Type=Application", text)
        self.assertRegex(text, r"(?m)^Exec=\S+$")
        self.assertRegex(text, r"(?m)^Name=")

    def test_desktop_entry_has_exec_line(self) -> None:
        text = (rl.APPIMAGE_DEF_DIR / rl.DESKTOP_ENTRY_NAME).read_text(encoding="utf-8")
        match = re.search(r"(?m)^Exec=\S+$", text)
        self.assertIsNotNone(match)

    def test_apprun_has_shebang(self) -> None:
        rl.validate_apprun()
        text = (rl.APPIMAGE_DEF_DIR / rl.APPRUN_NAME).read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!"))


class PlanTest(unittest.TestCase):
    def test_plan_dry_run(self) -> None:
        plan = rl.build_linux_plan("1.2.4")
        self.assertEqual(plan.version, "1.2.4")
        names = [stage["name"] for stage in plan.stages]
        self.assertIn("validate-version", names)
        self.assertIn("assemble-appimage", names)
        self.assertIn("build-deb", names)
        self.assertIn("build-flatpak", names)
        self.assertIn("checksum", names)

    def test_plan_rejects_bad_version(self) -> None:
        with self.assertRaises(rl.PackagingError):
            rl.build_linux_plan("not-a-version")

    def test_plan_to_dict_has_artifacts(self) -> None:
        data = rl.plan_to_dict(rl.build_linux_plan("1.2.4"))
        self.assertIn("hpc-client-gui-1.2.4-x86_64.AppImage", data["artifacts"])
        self.assertIn("hpc-client-gui_1.2.4_amd64.deb", data["artifacts"])
        self.assertIn("hpc-client-gui-1.2.4.flatpak", data["artifacts"])

    def test_main_plan_exit_zero(self) -> None:
        self.assertEqual(rl.main(["--version", "1.2.4", "--json"]), 0)

    def test_pip_install_command(self) -> None:
        self.assertEqual(rl.pip_install_command(), ["python", "-m", "pip", "install", "-e", ".[test]"])

    def test_validate_pip_metadata_passes(self) -> None:
        rl.validate_pip_metadata()

    def test_release_dir_contents(self) -> None:
        contents = rl.release_dir_contents("1.2.4")
        self.assertIn("hpc-client-gui-1.2.4-x86_64.AppImage.sha256", contents)
        self.assertIn("hpc-client-gui_1.2.4_amd64.deb.sha256", contents)
        self.assertIn("hpc-client-gui-1.2.4.flatpak.sha256", contents)

    def test_plan_has_release_layout_stage(self) -> None:
        plan = rl.build_linux_plan("1.2.4")
        names = [stage["name"] for stage in plan.stages]
        self.assertIn("validate-pip-source", names)
        self.assertIn("release-layout", names)

    def test_sha256(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(b"abc")
            tmp = Path(f.name)
        try:
            self.assertEqual(rl.sha256_hex(tmp), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        finally:
            tmp.unlink(missing_ok=True)


class DebFlatpakTest(unittest.TestCase):
    def test_deb_artifact_name(self) -> None:
        self.assertEqual(rl.deb_artifact_name("1.2.4"), "hpc-client-gui_1.2.4_amd64.deb")

    def test_flatpak_artifact_name(self) -> None:
        self.assertEqual(rl.flatpak_artifact_name("1.2.4"), "hpc-client-gui-1.2.4.flatpak")

    def test_validate_deb_control_passes(self) -> None:
        rl.validate_deb_control()

    def test_validate_flatpak_manifest_passes(self) -> None:
        rl.validate_flatpak_manifest()

    def test_flatpak_manifest_ids(self) -> None:
        data = json.loads((rl.FLATPAK_DEF_DIR / f"{rl.FLATPAK_ID}.json").read_text(encoding="utf-8"))
        self.assertEqual(data["app-id"], "io.github.mskomek.HpcClientGui")
        self.assertIn("command", data)

    def test_deb_control_missing_version_placeholder_raises(self) -> None:
        real = rl.DEB_DEF_DIR / "DEBIAN" / "control"

        def _fake_read(self, *args, **kwargs):
            if self == real:
                return "Package: hpc-client-gui\nVersion: 1.2.4\nArchitecture: amd64\nDescription: x\n"
            return real_read_text(self, *args, **kwargs)

        with mock.patch.object(rl.Path, "read_text", _fake_read):
            with self.assertRaises(rl.PackagingError):
                rl.validate_deb_control()


if __name__ == "__main__":
    unittest.main()
