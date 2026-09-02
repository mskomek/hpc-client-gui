"""Reproducible, evidence-backed Qt removal readiness gate."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

REQUIRED_WX_EVIDENCE_PLATFORMS = ("windows", "linux", "macos")
PRODUCTION_DEPENDENCY_FILES = ("pyproject.toml", "requirements.txt", "requirements-release.lock")
PACKAGED_CHECKS = ("process_started", "wx_runtime_started", "main_frame_created", "clean_shutdown")
MANUAL_CHECKS = ("launch", "connection", "terminal", "files", "jobs", "plugins", "shutdown")
QT_PACKAGING_PREFIXES = ("pyside6", "shiboken6", "qtcore", "qtgui", "qtwidgets", "qtsvg", "qtweb")


class GitScanError(RuntimeError):
    """The gate cannot establish a trustworthy tracked-file scan."""


def _full_sha(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{40}", value))


def current_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and _full_sha(value) else None


def git_tracked_files(root: Path, patterns: tuple[str, ...] | None = None) -> list[Path]:
    """Return deterministic paths from Git's index, never from directory traversal."""
    args = ["git", "ls-files", "-z"]
    if patterns:
        args += ["--", *patterns]
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitScanError(f"git tracked-file enumeration failed: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        raise GitScanError(f"git tracked-file enumeration failed{': ' + detail if detail else ''}")
    paths: list[Path] = []
    root_resolved = root.resolve()
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8", errors="strict").replace("\\", "/")
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise GitScanError(f"tracked path escapes repository: {name}")
        path = (root / Path(*relative.parts)).resolve()
        if root_resolved not in path.parents and path != root_resolved:
            raise GitScanError(f"tracked path escapes repository: {name}")
        paths.append(path)
    return sorted(set(paths), key=lambda path: path.relative_to(root_resolved).as_posix())


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _relevant_dirty_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(["git", "diff", "--name-only", "HEAD", "--"], cwd=root, capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitScanError(f"git dirty-tree check failed: {exc}") from exc
    if result.returncode != 0:
        raise GitScanError("git dirty-tree check failed")
    names = [line.replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    relevant = []
    for name in names:
        is_relevant = name.startswith(("src/", "build/", "docs/v2/")) or name in PRODUCTION_DEPENDENCY_FILES
        if is_relevant and (name.startswith("src/") or name.startswith("docs/v2/") or name in PRODUCTION_DEPENDENCY_FILES or fnmatch(name, "build/**/*.spec")):
            relevant.append(name)
    return sorted(set(relevant))


def normalize_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _dependency_names(line: str) -> list[str]:
    pattern = r"(?i)(?<![A-Za-z0-9])((?:pyside[-_.]?6(?:[-_.](?:addons|essentials))?)|shiboken[-_.]?6)(?=$|[\s<>=!~;,\"'])"
    return [match.group(1) for match in re.finditer(pattern, line)]


def dependency_records(root: Path, *, return_scanned: bool = False):
    tracked = {_relative(root, path): path for path in git_tracked_files(root)}
    records: list[dict[str, str]] = []
    scanned: list[str] = []
    for name in PRODUCTION_DEPENDENCY_FILES:
        path = tracked.get(name)
        if path is None:
            continue
        scanned.append(name)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            for raw in _dependency_names(line):
                normalized = normalize_distribution(raw)
                if normalized in {"pyside6", "pyside6-addons", "pyside6-essentials", "shiboken6"}:
                    records.append({"source": name, "dependency": raw, "normalized": normalized})
    return (records, scanned) if return_scanned else records


def production_qt_imports(root: Path, *, return_scanned: bool = False):
    records: list[dict[str, object]] = []
    files = [path for path in git_tracked_files(root) if _relative(root, path).startswith("src/") and path.suffix == ".py"]
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        rel = _relative(root, path)
        for node in ast.walk(tree):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            for name in names:
                if name == "PySide6" or name.startswith("PySide6.") or name == "shiboken6" or name.startswith("shiboken6."):
                    records.append({"path": rel, "line": node.lineno, "import": name, "category": "framework-neutralize" if "/core/" in rel or "/services/" in rel else "wx-replacement", "reason": "production Qt import", "migration_target": "framework-neutral service or wx adapter", "parity_ids": []})
    return (records, [_relative(root, path) for path in files]) if return_scanned else records


def _string_constants(node: ast.AST):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "collect_dynamic_libs":
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _string_constants(child)


def _packaging_record(path: Path, root: Path, node: ast.AST, value: str) -> dict[str, object]:
    return {"path": _relative(root, path), "line": getattr(node, "lineno", 1), "reference": value}


def packaging_blockers(root: Path, *, return_scanned: bool = False):
    blockers: list[dict[str, object]] = []
    specs = [path for path in git_tracked_files(root) if _relative(root, path).startswith("build/") and path.suffix == ".spec"]
    for path in specs:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            values: list[ast.AST] = []
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {"hiddenimports", "binaries"} for target in node.targets):
                values = list(_string_constants(node.value))
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "collect_dynamic_libs":
                    values = [node.args[0]] if node.args and isinstance(node.args[0], ast.Constant) else []
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in {"hiddenimports", "binaries"} and node.func.attr in {"append", "extend"}:
                    values = list(_string_constants(node.args[0])) if node.args else []
                elif isinstance(node.func, ast.Name) and node.func.id == "Analysis":
                    for keyword in node.keywords:
                        if keyword.arg in {"hiddenimports", "binaries"}:
                            values += list(_string_constants(keyword.value))
            for value_node in values:
                value = value_node.value
                low = value.lower().replace("-", "_")
                if low.startswith(QT_PACKAGING_PREFIXES):
                    blockers.append(_packaging_record(path, root, value_node, value))
    return (blockers, [_relative(root, path) for path in specs]) if return_scanned else blockers


def default_gui_runtime(root: Path) -> str | None:
    path = root / "src" / "hpc_gui" / "runtime.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "DEFAULT_GUI_RUNTIME" for target in node.targets):
            return node.value.value if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) else None
    return None


def _common_evidence(data: object, path: Path, platform: str, schema: str, checks: tuple[str, ...], commit: str | None) -> tuple[str, str | None]:
    if not path.is_file():
        return "MISSING", "file missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "INVALID", "invalid JSON"
    if not isinstance(data, dict) or data.get("schema") != schema:
        return "INVALID", "unsupported or missing schema"
    if not _full_sha(data.get("commit")) or data.get("commit") != commit:
        return "STALE", "evidence commit does not match current HEAD"
    if data.get("platform") != platform:
        return "FAIL", "platform does not match evidence path"
    if data.get("result") != "PASS":
        return "FAIL", f"result is {data.get('result', 'missing')}"
    if not isinstance(data.get("artifact"), str) or not data["artifact"].strip():
        return "INVALID", "artifact missing or empty"
    if not isinstance(data.get("artifact_sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", data["artifact_sha256"]):
        return "INVALID", "artifact SHA-256 missing or invalid"
    values = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    missing = [name for name in checks if values.get(name) != "PASS"]
    if missing:
        return "INVALID", f"mandatory checks not PASS: {', '.join(missing)}"
    return "PASS", None


def read_packaged_evidence(path: Path, platform: str, commit: str | None) -> tuple[str, str | None]:
    return _common_evidence(None, path, platform, "wx-packaged-smoke/1", PACKAGED_CHECKS, commit)


def read_manual_evidence(path: Path, platform: str, commit: str | None) -> tuple[str, str | None]:
    status, reason = _common_evidence(None, path, platform, "wx-manual-parity/1", MANUAL_CHECKS, commit)
    if status != "PASS":
        return status, reason
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "INVALID", "invalid JSON"
    if not isinstance(data.get("tester"), str) or not data["tester"].strip():
        return "INVALID", "tester missing or empty"
    if not isinstance(data.get("tested_at"), str) or not data["tested_at"].strip():
        return "INVALID", "tested_at missing or empty"
    try:
        timestamp = data["tested_at"].replace("Z", "+00:00")
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return "INVALID", "tested_at is not ISO-8601"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return "INVALID", "tested_at must include a timezone"
    return "PASS", None


def _evidence_map(root: Path, commit: str | None, manual: bool) -> tuple[dict[str, str], dict[str, str]]:
    statuses: dict[str, str] = {}
    details: dict[str, str] = {}
    directory = root / "docs" / "v2" / "manual-results" if manual else root / "build" / "audit"
    for platform in REQUIRED_WX_EVIDENCE_PLATFORMS:
        path = directory / (f"{platform}.json" if manual else f"wx-packaged-smoke-{platform}.json")
        validator = read_manual_evidence if manual else read_packaged_evidence
        status, reason = validator(path, platform, commit)
        statuses[platform] = status
        if reason:
            details[platform] = reason
    return statuses, details


def _p0_statuses(root: Path) -> dict[str, str]:
    baseline = (root / "docs/v2/GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8").splitlines()
    status = (root / "docs/v2/V2_PARITY_STATUS.md").read_text(encoding="utf-8").splitlines()
    result: dict[str, str] = {}
    for line in baseline:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0].startswith("GUI-") and "P0" in cells:
            result[cells[0]] = "UNVERIFIED"
    for line in status:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) > 1 and cells[0] in result:
            result[cells[0]] = cells[1].upper()
    return result


def evaluate_gate(*, p0: dict[str, str], qt_imports: list[dict[str, object]], qt_dependencies: list[dict[str, str]], qt_packaging: list[dict[str, object]], default_runtime: str | None, packaged: dict[str, str], manual: dict[str, str], commit: str | None, dirty_relevant: list[str] | None = None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not commit:
        reasons.append("current repository commit could not be determined")
    if dirty_relevant:
        reasons.append("gate-relevant tracked working tree changes exist: " + ", ".join(dirty_relevant))
    reasons += [f"P0 parity not covered: {key}" for key, value in sorted(p0.items()) if value != "COVERED"]
    reasons += [f"Qt production import: {item['path']}:{item['line']} {item['import']}" for item in qt_imports]
    reasons += [f"Qt production dependency remains: {item['source']} -> {item['dependency']}" for item in qt_dependencies]
    reasons += [f"Qt packaging blocker: {item['path']}:{item['line']} {item['reference']}" for item in qt_packaging]
    if default_runtime != "wx":
        reasons.append(f"default GUI runtime remains: {default_runtime or 'unknown'}")
    reasons += [f"packaged wx evidence {status.lower()}: {platform}" for platform, status in packaged.items() if status != "PASS"]
    reasons += [f"manual wx evidence {status.lower()}: {platform}" for platform, status in manual.items() if status != "PASS"]
    return ("GO" if not reasons else "NO-GO"), reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    commit = current_commit(root)
    report: dict[str, object] = {"schema": "qt-removal-gate/3", "commit": commit, "scan_basis": "git-tracked-files", "working_tree_gate_relevant_clean": False}
    try:
        dirty = _relevant_dirty_files(root)
        imports, source_files = production_qt_imports(root, return_scanned=True)
        dependencies, dependency_files = dependency_records(root, return_scanned=True)
        packaging, spec_files = packaging_blockers(root, return_scanned=True)
        packaged, packaged_details = _evidence_map(root, commit, False)
        manual, manual_details = _evidence_map(root, commit, True)
        runtime = default_gui_runtime(root)
        p0 = _p0_statuses(root)
        decision, reasons = evaluate_gate(p0=p0, qt_imports=imports, qt_dependencies=dependencies, qt_packaging=packaging, default_runtime=runtime, packaged=packaged, manual=manual, commit=commit, dirty_relevant=dirty)
        report.update({"decision": decision, "reasons": reasons, "p0": p0, "qt_imports": imports, "qt_files": sorted({item["path"] for item in imports}), "qt_dependencies": dependencies, "qt_packaging": packaging, "qt_packaging_files": sorted({item["path"] for item in packaging}), "default_gui_runtime": runtime, "packaged_evidence": packaged, "packaged_evidence_details": packaged_details, "manual_evidence": manual, "manual_evidence_details": manual_details, "scanned_dependency_files": dependency_files, "scanned_spec_files": spec_files, "scanned_source_file_count": len(source_files), "working_tree_gate_relevant_clean": not dirty})
    except (GitScanError, OSError, UnicodeError) as exc:
        report.update({"decision": "NO-GO", "reasons": [str(exc)], "p0": {}, "qt_imports": [], "qt_files": [], "qt_dependencies": [], "qt_packaging": [], "qt_packaging_files": [], "default_gui_runtime": None, "packaged_evidence": {}, "manual_evidence": {}, "scanned_dependency_files": [], "scanned_spec_files": [], "scanned_source_file_count": 0})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Qt Removal Readiness: {report['decision']}")
    for reason in report["reasons"]:
        print(reason)
    print(f"P0 blockers: {sum(value != 'COVERED' for value in report['p0'].values())}")
    print(f"Qt import points: {len(report['qt_imports'])}")
    print(f"Qt production files: {len(report['qt_files'])}")
    print(f"Qt dependency records: {len(report['qt_dependencies'])}")
    print(f"Qt dependency unique packages: {len({item['normalized'] for item in report['qt_dependencies']})}")
    print(f"Qt packaging blocker references: {len(report['qt_packaging'])}")
    print(f"Qt packaging blocker files: {len(report['qt_packaging_files'])}")
    return 0 if report["decision"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
