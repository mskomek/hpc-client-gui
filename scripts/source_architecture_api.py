"""Read and validate project facade export contracts."""

from __future__ import annotations

import ast
from typing import Any


def _declared_exports(tree: ast.Module) -> set[str] | None:
    for item in tree.body:
        if isinstance(item, ast.Assign):
            targets, value = item.targets, item.value
        elif isinstance(item, ast.AnnAssign):
            targets, value = [item.target], item.value
        else:
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            continue
        if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return None
        if not all(isinstance(entry, ast.Constant) and isinstance(entry.value, str) for entry in value.elts):
            return None
        return {entry.value for entry in value.elts}
    return None


def public_symbols(tree: ast.Module) -> set[str]:
    """Use explicit ``__all__`` when a facade declares one."""
    declared = _declared_exports(tree)
    if declared is not None:
        return declared
    names: set[str] = set()
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not item.name.startswith("_"):
            names.add(item.name)
        elif isinstance(item, (ast.Assign, ast.AnnAssign)):
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name) and not target.id.startswith("_"))
        elif isinstance(item, (ast.Import, ast.ImportFrom)):
            names.update(
                alias.asname or alias.name.split(".")[0]
                for alias in item.names
                if alias.name != "*" and not (alias.asname or alias.name.split(".")[0]).startswith("_")
            )
    return names


def api_errors(scan: dict[str, Any], baseline: dict[str, Any] | None) -> list[str]:
    errors = []
    for facade, expected in (baseline or {}).get("public_api", {}).items():
        tree = scan["trees"].get(facade)
        actual = public_symbols(tree) if tree else set()
        missing = sorted(set(expected) - actual)
        if missing:
            errors.append(f"{facade}: missing public facade symbols: {', '.join(missing)}")
    return errors
