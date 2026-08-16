import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_wiki  # noqa: E402

WIKI_ROOT = REPO_ROOT / "docs" / "wiki"


def _write(root: Path, name: str, text: str) -> None:
    (root / f"{name}.md").write_text(text, encoding="utf-8")


def _minimal_wiki(root: Path) -> None:
    _write(root, "Home", "# Home\n\n[[Page|Topic]]\n")
    _write(root, "Home-TR", "# Ana Sayfa\n\n[[Sayfa|Topic-TR]]\n")
    _write(root, "Topic", "# Topic\n\nBody.\n")
    _write(root, "Topic-TR", "# Konu\n\nGövde.\n")
    _write(root, "_Sidebar", "- [[Home|Home]]\n- [[Topic|Topic]]\n- [[Ana|Home-TR]]\n- [[Konu|Topic-TR]]\n")


class WikiCheckTest(unittest.TestCase):
    @unittest.skipUnless(WIKI_ROOT.is_dir(), "docs/wiki is outside the main sync boundary")
    def test_repository_wiki_is_clean(self):
        self.assertEqual(check_wiki.check_wiki(WIKI_ROOT), [])

    def test_minimal_wiki_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_wiki(root)
            self.assertEqual(check_wiki.check_wiki(root), [])

    def test_violations_are_reported(self):
        cases = {
            "missing Turkish counterpart": lambda r: (r / "Topic-TR.md").unlink(),
            "unresolved wiki link": lambda r: _write(r, "Topic", "# Topic\n\n[[Gone|Nowhere]]\n"),
            "unresolved asset reference": lambda r: _write(r, "Topic", "# Topic\n\n![x](assets/missing.png)\n"),
            "unresolved asset reference assets/gone.png": lambda r: _write(
                r,
                "Topic",
                f"# Topic\n\n![x]({check_wiki.WIKI_RAW_PREFIX}assets/gone.png)\n",
            ),
            "heading count differs": lambda r: _write(r, "Topic", "# Topic\n\n## Extra\n"),
            "forbidden term": lambda r: _write(r, "Topic", "# Topic\n\nSee waves/ for details.\n"),
            "not listed in _Sidebar.md": lambda r: _write(r, "_Sidebar", "- [[Home|Home]]\n- [[Ana|Home-TR]]\n- [[Konu|Topic-TR]]\n"),
            "orphan page": lambda r: _write(r, "Home", "# Home\n\nNo links.\n"),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    _minimal_wiki(root)
                    mutate(root)
                    problems = check_wiki.check_wiki(root)
                self.assertTrue(
                    any(expected in p for p in problems),
                    f"expected {expected!r} in {problems}",
                )


if __name__ == "__main__":
    unittest.main()
