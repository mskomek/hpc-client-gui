import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_third_party_versions as manifest


class ThirdPartyVersionsTests(unittest.TestCase):
    def test_collects_and_writes_deterministic_manifest(self):
        qtcore = types.ModuleType("PySide6.QtCore")
        qtcore.qVersion = lambda: "6.8.0"
        pyside6 = types.ModuleType("PySide6")
        pyside6.QtCore = qtcore
        versions = {distribution: "1.0.0" for _, distribution in manifest.PACKAGES}

        with patch.dict(sys.modules, {"PySide6": pyside6, "PySide6.QtCore": qtcore}), patch(
            "scripts.generate_third_party_versions.importlib.metadata.version",
            side_effect=lambda name: versions[name],
        ):
            values = manifest.collect("1.2.7")
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "THIRD_PARTY_VERSIONS.txt"
                manifest.write_manifest(output, values)
                self.assertEqual(
                    output.read_text(encoding="utf-8").splitlines()[:3],
                    ["HPC Client GUI: 1.2.7", f"Python: {sys.version.split()[0]}", "PySide6: 1.0.0"],
                )


if __name__ == "__main__":
    unittest.main()
