from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_release_surface  # noqa: E402


class ReleaseSurfaceCheckTest(unittest.TestCase):
    def test_repository_surface_is_clean(self) -> None:
        self.assertEqual(check_release_surface.check_release_surface(ROOT), [])

    def test_stale_tag_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in (
                "README.md",
                "pyproject.toml",
                "scripts/release.ps1",
                "scripts/release_linux.py",
                ".github/workflows/release.yml",
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\nhttps://github.com/mskomek/hpc-client-gui/releases/tag/v1.2.6\n",
                encoding="utf-8",
            )
            problems = check_release_surface.check_release_surface(root)
        self.assertTrue(any("versioned URLs" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
