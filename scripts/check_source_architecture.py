"""Combine the shared Agent Core LOC gate with project dependency/API contracts."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from source_architecture_api import api_errors as _api_errors
from source_architecture_api import public_symbols as _public_symbols


LIMIT = 500
BASELINE_PATH = Path("docs/architecture/source-loc-baseline.json")
EXCLUDED_PARTS = {".git", ".tmp", ".venv", "venv", "__pycache__"}
PUBLIC_FACADES = (
    "src/hpc_gui/cli/main.py",
    "src/hpc_gui/config/storage.py",
    "src/hpc_gui/plugins/validator.py",
    "src/hpc_gui/plugins/ui_contributions.py",
    "src/hpc_gui/ui/widgets/jobs_outputs_widget.py",
    "src/hpc_gui/wx_jobs.py",
    "src/hpc_gui/ui/main_window.py",
    "src/hpc_gui/wx_connection.py",
    "src/hpc_gui/wx_editor_view.py",
    "src/hpc_gui/wx_transfer_workspace.py",
    "src/hpc_gui/wx_splash.py",
    "src/hpc_gui/wx_updater_view.py",
    "src/hpc_gui/ui/dialogs/connection_dialog.py",
    "src/hpc_gui/ui/dialogs/settings_dialog.py",
    "src/hpc_gui/ui/dialogs/transfer_dialog.py",
)


def _source_paths(root: Path) -> list[Path]:
    commands = (
        ["git", "ls-files", "-z", "--cached", "--", "*.py"],
        ["git", "ls-files", "-z", "--others", "--exclude-standard", "--", "*.py"],
    )
    paths: set[Path] = set()
    for command in commands:
        output = subprocess.run(command, cwd=root, check=True, stdout=subprocess.PIPE).stdout
        for item in output.split(b"\0"):
            if not item:
                continue
            path = Path(item.decode("utf-8"))
            if not EXCLUDED_PARTS.intersection(path.parts):
                paths.add(path)
    return sorted(paths, key=lambda path: path.as_posix())


def _module_for_path(path: Path) -> str | None:
    parts = path.as_posix().split("/")
    if len(parts) >= 3 and parts[:2] == ["src", "hpc_gui"]:
        module_parts = parts[1:]
    elif len(parts) >= 2 and parts[0] in {"tests", "scripts"}:
        module_parts = parts
    elif len(parts) == 1:
        module_parts = parts
    else:
        return None
    module_parts[-1] = Path(module_parts[-1]).stem
    if module_parts[-1] == "__init__":
        module_parts.pop()
    return ".".join(module_parts)


def _project_path(root: Path, module: str) -> Path | None:
    parts = module.split(".")
    if parts[0] == "hpc_gui":
        base = root / "src" / Path(*parts)
    elif parts[0] in {"tests", "scripts"}:
        base = root / Path(*parts)
    else:
        return None
    source, package = base.with_suffix(".py"), base / "__init__.py"
    if source.is_file():
        return source
    if package.is_file():
        return package
    return base if base.is_dir() else None


def _resolve_from_module(current: str, node: ast.ImportFrom, is_package: bool) -> str | None:
    if node.level == 0:
        return node.module
    parts = current.split(".")
    package = parts if is_package else parts[:-1]
    keep = len(package) - (node.level - 1)
    if keep < 1:
        return None
    resolved = package[:keep]
    if node.module:
        resolved.extend(node.module.split("."))
    return ".".join(resolved)


def _defined_symbols(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(item.name)
        elif isinstance(item, (ast.Assign, ast.AnnAssign)):
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
        elif isinstance(item, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split(".")[0] for alias in item.names if alias.name != "*")
    return names


def _runtime_imports(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    """Return imports that execute at runtime, excluding TYPE_CHECKING blocks."""
    imports: list[ast.Import | ast.ImportFrom] = []

    def is_type_checking(test: ast.expr) -> bool:
        return (
            isinstance(test, ast.Name) and test.id == "TYPE_CHECKING"
        ) or (
            isinstance(test, ast.Attribute)
            and test.attr == "TYPE_CHECKING"
            and isinstance(test.value, ast.Name)
            and test.value.id == "typing"
        )

    class Visitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:
            if is_type_checking(node.test):
                for item in node.orelse:
                    self.visit(item)
                return
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            imports.append(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            imports.append(node)

    Visitor().visit(tree)
    return imports


def _scan_project(root: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    trees: dict[str, ast.Module] = {}
    modules: dict[str, str] = {}
    errors: list[str] = []
    graph: dict[str, set[str]] = defaultdict(set)
    for path in _source_paths(root):
        target = root / path
        if not target.is_file():
            continue
        raw = target.read_bytes()
        relative = path.as_posix()
        text = raw.decode("utf-8", errors="replace")
        tree_module = _module_for_path(path)
        files[relative] = {"loc": len(text.splitlines()), "sha256": hashlib.sha256(raw).hexdigest()}
        if tree_module:
            modules[tree_module] = relative
        try:
            trees[relative] = ast.parse(text, filename=relative)
        except SyntaxError as exc:
            errors.append(f"{relative}:{exc.lineno}: syntax error: {exc.msg}")
    for relative, tree in trees.items():
        current = _module_for_path(Path(relative))
        for node in _runtime_imports(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in {"hpc_gui", "tests", "scripts"}:
                        destination = _project_path(root, alias.name)
                        if destination is None:
                            errors.append(f"{relative}:{node.lineno}: unresolved internal import '{alias.name}'")
                        else:
                            module = _module_for_path(destination.relative_to(root))
                            if current and module and module in modules:
                                graph[current].add(module)
                continue
            if not isinstance(node, ast.ImportFrom):
                continue
            resolved = _resolve_from_module(current, node, Path(relative).name == "__init__.py")
            if not resolved or not resolved.startswith("hpc_gui"):
                if not resolved or resolved.split(".", 1)[0] not in {"tests", "scripts"}:
                    continue
            destination = _project_path(root, resolved)
            if destination is None:
                errors.append(f"{relative}:{node.lineno}: unresolved internal import '{resolved}'")
                continue
            target_module = _module_for_path(destination.relative_to(root))
            if current and target_module and target_module in modules and target_module != current:
                graph[current].add(target_module)
            target_tree = trees.get(destination.relative_to(root).as_posix())
            defined = _defined_symbols(target_tree) if target_tree else set()
            for alias in node.names:
                if alias.name == "*":
                    continue
                child = f"{resolved}.{alias.name}"
                child_path = _project_path(root, child)
                if child_path:
                    child_module = _module_for_path(child_path.relative_to(root))
                    if current and child_module and child_module in modules and child_module != current:
                        graph[current].add(child_module)
                elif alias.name not in defined:
                    errors.append(
                        f"{relative}:{node.lineno}: unresolved internal symbol '{alias.name}' from '{resolved}'"
                    )
    return {"files": files, "trees": trees, "modules": modules, "graph": graph, "dependency_errors": sorted(set(errors))}


def _cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    index, stack = 0, []
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    active: set[str] = set()
    found: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        active.add(node)
        for target in sorted(graph.get(node, ())):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in active:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] == indices[node]:
            group = []
            while True:
                target = stack.pop()
                active.remove(target)
                group.append(target)
                if target == node:
                    break
            if len(group) > 1 or node in graph.get(node, set()):
                found.append(sorted(group))

    nodes = set(graph) | {target for edges in graph.values() for target in edges}
    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return sorted(found)


def _core_root(root: Path, explicit: Path | None) -> Path:
    candidates = [explicit] if explicit else []
    if os.environ.get("AC_CORE_ROOT"):
        candidates.append(Path(os.environ["AC_CORE_ROOT"]))
    candidates.extend(parent / ".agents-core" for parent in root.parents)
    for candidate in candidates:
        if candidate and (candidate / ".opencode/scripts/validate-source-architecture.py").is_file():
            return candidate.resolve()
    raise FileNotFoundError("shared Agent Core validator not found; set AC_CORE_ROOT to its checkout")


def _run_shared_loc(root: Path, core: Path, scope: str, base: str) -> dict[str, Any]:
    validator = core / ".opencode/scripts/validate-source-architecture.py"
    command = [sys.executable, str(validator), "--root", str(root), "--scope", scope]
    if scope == "changed":
        command.extend(["--base", base])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"shared architecture validator returned invalid JSON: {result.stderr}") from exc
    report["exit_code"] = result.returncode
    return report


def _baseline(scan: dict[str, Any], root: Path) -> dict[str, Any]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True).stdout.strip()
    return {
        "schema_version": 1,
        "limit": LIMIT,
        "source_commit": commit,
        "files": scan["files"],
        "dependency_errors": scan["dependency_errors"],
        "cycles": _cycles(scan["graph"]),
    }


def _write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = report.get("status", "FAIL")
    lines = [
        "# Source Architecture Gate", "",
        f"- Mode: `{report['mode']}`",
        f"- Source commit: `{report['source_commit']}`",
        f"- Shared LOC scope: `{report['loc_gate']['scope']}`",
        f"- Shared source count: {report['loc_gate']['source_count']}",
        f"- Files over 500 lines in current inventory: {report['over_limit_python_count']}",
        f"- Dependency errors: {len(report['dependency_errors'])}",
        f"- Current cycles: {len(report['current_cycles'])}",
        f"- Result: **{status}**", "",
    ]
    for title, values in (
        ("LOC errors", report["loc_gate"].get("errors", [])),
        ("Dependency errors", report["new_dependency_errors"]),
        ("Public API errors", report["api_errors"]),
        ("Cycle errors", report["cycle_errors"]),
    ):
        lines.extend([f"## {title}", ""])
        lines.extend([f"- {value}" for value in values] if values else ["- None"])
        lines.append("")
    lines.extend(["## Python files", "", "| File | Physical lines | SHA-256 |", "|---|---:|---|"])
    for path, data in sorted(report["files"].items()):
        lines.append(f"| `{path}` | {data['loc']} | `{data['sha256']}` |")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--core-root", type=Path)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--api-contract", type=Path, default=Path("docs/architecture/public-api-contracts.json"))
    parser.add_argument("--mode", choices=("baseline", "gate", "full"), required=True)
    parser.add_argument("--base", default="HEAD", help="Previous successful commit for changed-source LOC gate.")
    parser.add_argument("--json-report", type=Path, default=Path(".tmp/source-architecture.json"))
    parser.add_argument("--markdown-report", type=Path, default=Path(".tmp/source-architecture.md"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    core = _core_root(root, args.core_root)
    baseline_path = args.baseline if args.baseline.is_absolute() else root / args.baseline
    scan = _scan_project(root)
    scope = "project" if args.mode in {"baseline", "full"} else "changed"
    loc_gate = _run_shared_loc(root, core, scope, args.base)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.is_file() else None
    api_contract_path = args.api_contract if args.api_contract.is_absolute() else root / args.api_contract
    api_contract = None
    if api_contract_path.is_file():
        contract = json.loads(api_contract_path.read_text(encoding="utf-8"))
        api_contract = contract.get("modules", contract.get("public_api", {}))
    if api_contract is None:
        api_contract = (baseline or {}).get("public_api")
    if args.mode == "baseline":
        baseline = _baseline(scan, root)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        api_contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_modules = {
            facade: sorted(_public_symbols(scan["trees"][facade]))
            for facade in PUBLIC_FACADES
            if facade in scan["trees"]
        }
        api_contract_path.write_text(json.dumps({
            "schema_version": 1,
            "baseline_commit": baseline["source_commit"],
            "modules": contract_modules,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dependency_errors = scan["dependency_errors"]
    old_errors = set((baseline or {}).get("dependency_errors", [])) if args.mode != "baseline" else set()
    new_dependency_errors = sorted(
        set(dependency_errors) if args.mode == "full" else set(dependency_errors) - old_errors
    )
    old_cycles = {tuple(group) for group in (baseline or {}).get("cycles", [])}
    current_cycles = _cycles(scan["graph"])
    new_cycles = [group for group in current_cycles if tuple(group) not in old_cycles]
    cycle_errors = []
    if args.mode == "full":
        cycle_errors = ["cycle: " + " -> ".join(group) for group in current_cycles]
    elif args.mode == "gate":
        cycle_errors = ["new cycle: " + " -> ".join(group) for group in new_cycles]
    api_errors = [] if args.mode == "baseline" else _api_errors(scan, {"public_api": api_contract or {}})
    passed = args.mode != "baseline" and loc_gate["status"] == "PASS" and not new_dependency_errors and not api_errors and not cycle_errors
    report = {
        "schema_version": 1,
        "mode": args.mode,
        "status": "BASELINE_RECORDED" if args.mode == "baseline" else ("PASS" if passed else "FAIL"),
        "source_commit": baseline["source_commit"] if args.mode == "baseline" else subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True
        ).stdout.strip(),
        "loc_gate": loc_gate,
        "shared_loc_passed": loc_gate["status"] == "PASS",
        "file_count_python": len(scan["files"]),
        "over_limit_python_count": sum(data["loc"] > LIMIT for data in scan["files"].values()),
        "files": scan["files"],
        "dependency_errors": dependency_errors,
        "new_dependency_errors": new_dependency_errors,
        "api_errors": api_errors,
        "baseline_cycle_count": len(old_cycles),
        "current_cycles": current_cycles,
        "new_cycles": new_cycles,
        "cycle_errors": cycle_errors,
    }
    json_path = args.json_report if args.json_report.is_absolute() else root / args.json_report
    markdown_path = args.markdown_report if args.markdown_report.is_absolute() else root / args.markdown_report
    _write_reports(report, json_path, markdown_path)
    print(f"{report['status']}: {report['file_count_python']} Python files; {report['over_limit_python_count']} over 500 lines")
    print(f"JSON report: {json_path}\nMarkdown report: {markdown_path}")
    return 0 if args.mode == "baseline" or passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
