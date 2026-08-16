import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_branding  # noqa: E402


class BrandingCheckTest(unittest.TestCase):
    def test_clean_tree_passes(self):
        self.assertEqual(check_branding.find_corrupt_strings(REPO_ROOT), [])

    def test_seeded_corruption_is_detected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "src").mkdir()
            # Built at runtime so this file stays clean for the repo-wide scan.
            seeded = 'help="' + "L" + 'reate a profile."\n'
            (base / "src" / "seed.py").write_text(seeded, encoding="utf-8")
            findings = check_branding.find_corrupt_strings(base)
        self.assertEqual(len(findings), 1)
        self.assertIn("seed.py:1", findings[0])


if __name__ == "__main__":
    unittest.main()
