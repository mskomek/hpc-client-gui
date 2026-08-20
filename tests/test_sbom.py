import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_sbom import write_sbom


class SbomTests(unittest.TestCase):
    def test_generates_sorted_purls_from_pinned_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "requirements.lock"
            output = root / "SBOM.cdx.json"
            lock.write_text("zeta==2.0\nAlpha_Pkg==1.0\n", encoding="utf-8")
            write_sbom(lock, output, "1.2.7")
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([item["name"] for item in data["components"]], ["Alpha_Pkg", "zeta"])
            self.assertEqual(data["components"][0]["purl"], "pkg:pypi/alpha-pkg@1.0")


if __name__ == "__main__":
    unittest.main()
