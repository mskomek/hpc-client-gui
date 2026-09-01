import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hpc_gui.core import diagnostics
from hpc_gui.services.cluster_self_test import ClusterSelfTestResult, SelfTestSection


class DiagnosticBundleTests(unittest.TestCase):
    def test_excludes_config_json_and_redacts_included_files(self) -> None:
        with TemporaryDirectory() as home_dir, TemporaryDirectory() as out_dir:
            home = Path(home_dir)
            app_data = home / ".truba_slurm_gui"
            app_data.mkdir(parents=True, exist_ok=True)

            (app_data / "config.json").write_text(
                json.dumps({"profiles": [{"host": "arf.truba.gov.tr", "username": "mkomek",
                                           "password_enc": "super-secret-blob"}]}),
                encoding="utf-8",
            )
            (app_data / "app.log").write_text(
                r"C:\Users\mkomek\file.log connecting to arf.truba.gov.tr -pw FakeX11Password Authorization: Bearer fake.token",
                encoding="utf-8",
            )

            with patch.object(Path, "home", return_value=home), patch(
                "getpass.getuser", return_value="mkomek"
            ), patch(
                "hpc_gui.config.storage.load_profiles",
                return_value=[{"username": "mkomek", "host": "arf.truba.gov.tr"}],
            ):
                bundle_path = diagnostics.create_diagnostic_bundle(out_dir)

            self.assertTrue(bundle_path.name.startswith("hpc_diagnostics_"))
            with zipfile.ZipFile(bundle_path) as zf:
                names = zf.namelist()
                self.assertNotIn("config.json", names)
                self.assertIn("app.log", names)
                log_content = zf.read("app.log").decode("utf-8")
                self.assertNotIn("mkomek", log_content)
                self.assertNotIn("arf.truba.gov.tr", log_content)
                self.assertIn("<user>", log_content)
                self.assertIn("<host>", log_content)
                self.assertNotIn("FakeX11Password", log_content)
                self.assertNotIn("fake.token", log_content)
                manifest = json.loads(zf.read("manifest.json"))
                self.assertIn("app.log", manifest["included_files"])

    def test_v2_bundle_has_safe_structured_context_and_bounded_logs(self) -> None:
        with TemporaryDirectory() as home_dir, TemporaryDirectory() as out_dir:
            home = Path(home_dir)
            app_data = home / ".truba_slurm_gui"
            app_data.mkdir(parents=True, exist_ok=True)
            (app_data / "history.jsonl").write_text(
                "\n".join(f"line-{i}" for i in range(6000)), encoding="utf-8"
            )
            provider = {
                "name": "Example",
                "access": {"auth_methods": ["key"]},
                "secret_token": "DUMMY-TOKEN",
            }
            with patch.object(Path, "home", return_value=home), patch(
                "hpc_gui.config.storage.load_profiles", return_value=[]
            ):
                bundle_path = diagnostics.create_diagnostic_bundle(
                    out_dir,
                    provider=provider,
                    self_test=ClusterSelfTestResult("PASS", (SelfTestSection("Connection"),)),
                )
            with zipfile.ZipFile(bundle_path) as zf:
                names = set(zf.namelist())
                assert {"manifest.json", "runtime.json", "plugins.json", "provider.json", "self_test.json"} <= names
                combined = b"".join(zf.read(name) for name in names)
                self.assertNotIn(b"DUMMY-TOKEN", combined)
                manifest = json.loads(zf.read("manifest.json"))
                self.assertEqual(manifest["schema"], "hpc-diagnostics/2")
                self.assertTrue(manifest["redaction"]["secrets_excluded"])


if __name__ == "__main__":
    unittest.main()
