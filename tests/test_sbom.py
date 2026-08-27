import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_sbom import read_lock, write_sbom


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

    def test_selects_platform_markers_for_mac_intel_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "requirements.lock"
            lock.write_text(
                'cryptography==50.0.0; sys_platform != "darwin" or platform_machine != "x86_64"\n'
                'cryptography==48.0.1; sys_platform == "darwin" and platform_machine == "x86_64"\n',
                encoding="utf-8",
            )
            assert read_lock(lock, {"sys_platform": "darwin", "platform_machine": "x86_64"}) == [
                ("cryptography", "48.0.1")
            ]


if __name__ == "__main__":
    unittest.main()
