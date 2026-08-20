from pathlib import Path
import unittest


ASSETS = Path(__file__).parents[1] / "src" / "hpc_gui" / "assets" / "terminal"


class TerminalAssetsTests(unittest.TestCase):
    def test_terminal_is_fully_local(self):
        page = (ASSETS / "index.html").read_text(encoding="utf-8")
        bridge = (ASSETS / "bridge.js").read_text(encoding="utf-8")
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)
        self.assertIn("hpcSetFontSize", bridge)
        for name in ("xterm.js", "xterm.css", "addon-fit.js", "bridge.js"):
            self.assertTrue((ASSETS / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
