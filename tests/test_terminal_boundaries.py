import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TerminalBoundaryTests(unittest.TestCase):
    def test_terminal_bridge_does_not_depend_on_login_widget(self):
        names = imports(ROOT / "src/hpc_gui/services/terminal_bridge.py")
        self.assertFalse(any("login_widget" in name for name in names))

    def test_terminal_header_does_not_own_ssh_or_profile_logic(self):
        names = imports(ROOT / "src/hpc_gui/ui/widgets/terminal_header.py")
        self.assertFalse(any(name.startswith("hpc_gui.ssh") for name in names))
        self.assertFalse(any("config.storage" in name for name in names))


if __name__ == "__main__":
    unittest.main()
