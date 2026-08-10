import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from truba_gui.core import diagnostics


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
                r"C:\Users\mkomek\file.log connecting to arf.truba.gov.tr",
                encoding="utf-8",
            )

            with patch.object(Path, "home", return_value=home), patch(
                "getpass.getuser", return_value="mkomek"
            ), patch(
                "truba_gui.config.storage.load_profiles",
                return_value=[{"username": "mkomek", "host": "arf.truba.gov.tr"}],
            ):
                bundle_path = diagnostics.create_diagnostic_bundle(out_dir)

            with zipfile.ZipFile(bundle_path) as zf:
                names = zf.namelist()
                self.assertNotIn("config.json", names)
                self.assertIn("app.log", names)
                log_content = zf.read("app.log").decode("utf-8")
                self.assertNotIn("mkomek", log_content)
                self.assertNotIn("arf.truba.gov.tr", log_content)
                self.assertIn("<user>", log_content)
                self.assertIn("<host>", log_content)


if __name__ == "__main__":
    unittest.main()
