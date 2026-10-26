import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import generate_third_party_versions as manifest

pytestmark = [pytest.mark.release, pytest.mark.license]


class ThirdPartyVersionsTests(unittest.TestCase):
    def test_collects_and_writes_deterministic_manifest(self):
        versions = {distribution: "1.0.0" for _, distribution in manifest.PACKAGES}

        with patch(
            "scripts.generate_third_party_versions.importlib.metadata.version",
            side_effect=lambda name: versions[name],
        ):
            values = manifest.collect("1.2.7")
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "THIRD_PARTY_VERSIONS.txt"
                manifest.write_manifest(output, values)
                self.assertEqual(
                    output.read_text(encoding="utf-8").splitlines()[:3],
                    ["HPC Client GUI: 1.2.7", f"Python: {sys.version.split()[0]}", "wxPython: 1.0.0"],
                )
                content = output.read_text(encoding="utf-8")
                self.assertIn("wxPython: 1.0.0", content)
                self.assertNotIn("PySide6", content)


if __name__ == "__main__":
    unittest.main()
