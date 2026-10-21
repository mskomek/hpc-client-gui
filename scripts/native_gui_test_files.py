"""Discover test modules that need isolated native GUI processes."""

from __future__ import annotations

import ast
from pathlib import Path

_NATIVE_GUI_MARKERS = frozenset({"gui", "wx", "qt"})
_NATIVE_GUI_MODULES = frozenset({"wx", "PySide6", "PyQt5", "PyQt6"})


class _NativeGuiMarkerVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.pytest_aliases = {"pytest"}
        self.mark_aliases = {"mark"}
        self.found = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pytest":
                self.pytest_aliases.add(alias.asname or "pytest")
            if alias.name.split(".", 1)[0] in _NATIVE_GUI_MODULES:
                self.found = True

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if (node.module or "").split(".", 1)[0] in _NATIVE_GUI_MODULES:
            self.found = True
        if any(alias.name == "wx" for alias in node.names):
            self.found = True
        if node.module == "pytest":
            self.mark_aliases.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "mark"
            )

    def visit_Call(self, node: ast.Call) -> None:
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and function.attr == "importorskip"
            and isinstance(function.value, ast.Name)
            and function.value.id in self.pytest_aliases
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.split(".", 1)[0] in _NATIVE_GUI_MODULES
        ):
            self.found = True
        self.generic_visit(node)

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


def _has_pytest_test_declaration(tree: ast.Module) -> bool:
    """Exclude manual ``test_*.py`` verification scripts with no test nodes."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            if any(
                isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                and member.name.startswith("test_")
                for member in node.body
            ):
                return True
    return False


def discover_native_gui_test_files(test_root: Path) -> tuple[str, ...]:
    """Return collected test modules marked for GUI isolation or native toolkit use."""
    paths: list[str] = []
    for path in sorted(test_root.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not _has_pytest_test_declaration(tree):
            continue
        visitor = _NativeGuiMarkerVisitor()
        visitor.visit(tree)
        if visitor.found:
            paths.append(path.relative_to(test_root.parent).as_posix())
    return tuple(paths)
