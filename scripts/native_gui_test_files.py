"""Discover test modules that need isolated native GUI processes."""

from __future__ import annotations

import ast
from pathlib import Path

_NATIVE_GUI_MARKERS = frozenset({"gui", "wx", "qt"})


class _NativeGuiMarkerVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.pytest_aliases = {"pytest"}
        self.mark_aliases = {"mark"}
        self.found = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pytest":
                self.pytest_aliases.add(alias.asname or "pytest")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pytest":
            self.mark_aliases.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "mark"
            )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _NATIVE_GUI_MARKERS:
            value = node.value
            if (
                isinstance(value, ast.Attribute)
                and value.attr == "mark"
                and isinstance(value.value, ast.Name)
                and value.value.id in self.pytest_aliases
            ):
                self.found = True
            elif isinstance(value, ast.Name) and value.id in self.mark_aliases:
                self.found = True
        self.generic_visit(node)


def discover_native_gui_test_files(test_root: Path) -> tuple[str, ...]:
    """Return every test module declaring gui, wx, or qt pytest markers."""
    paths: list[str] = []
    for path in sorted(test_root.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _NativeGuiMarkerVisitor()
        visitor.visit(tree)
        if visitor.found:
            paths.append(path.relative_to(test_root.parent).as_posix())
    return tuple(paths)
