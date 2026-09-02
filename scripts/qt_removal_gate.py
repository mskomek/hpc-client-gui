"""Evidence-backed Qt removal readiness gate."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

REQUIRED_WX_EVIDENCE_PLATFORMS = ("windows", "linux", "macos")
PACKAGED_CHECKS = ("process_started", "wx_runtime_started", "main_frame_created", "clean_shutdown")
MANUAL_CHECKS = ("launch", "connection", "terminal", "files", "jobs", "plugins", "shutdown")
QT_IMPORT_PREFIXES = ("PySide6", "shiboken6")
QT_PACKAGING_NAMES = ("pyside6", "shiboken6", "qtcore", "qtgui", "qtwidgets", "qtsvg", "qtwebchannel", "qtwebengine")


def _full_sha(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{40}", value))


def current_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and _full_sha(value) else None


def normalize_distribution(name: str) -> str:
    """PEP 503 normalization plus compatibility for PySide-6 spellings."""
    return re.sub(r"[-_.]+", "", name).lower()


def _dependency_name(line: str) -> str | None:
    match = re.search(r"(?i)(?:^|[\"'])(pyside(?:[-_.]?6)|shiboken(?:[-_.]?6))(?:\s*[<>=!~]|[\"']|$)", line.strip())
    return match.group(1) if match else None


def dependency_records(root: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    candidates = [root / "pyproject.toml", root / "requirements.txt"]
    candidates += [p for p in root.glob("*.txt") if "constraint" in p.name.lower() or "lock" in p.name.lower()]
    candidates += [p for p in root.glob("*.lock")]
    for path in dict.fromkeys(candidates):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = _dependency_name(line)
            if raw and normalize_distribution(raw) in {"pyside6", "shiboken6"}:
                records.append({"source": path.relative_to(root).as_posix(), "dependency": raw})
    return records


def _qt_name(value: str) -> bool:
    low = value.lower().replace("-", "_")
    return low.startswith(("pyside6", "shiboken6", "qtcore", "qtgui", "qtwidgets", "qtsvg", "qtweb"))


def production_qt_imports(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    source_root = root / "src"
    for path in source_root.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name == "PySide6" or name.startswith("PySide6.") or name == "shiboken6" or name.startswith("shiboken6."):
                    category = "framework-neutralize" if "/core/" in rel or "/services/" in rel else "wx-replacement"
                    records.append({
                        "path": rel,
                        "line": node.lineno,
                        "import": name,
                        "category": category,
                        "reason": "production Qt import",
                        "migration_target": "framework-neutral service or wx adapter",
                        "parity_ids": [],
                    })
    return records


def packaging_blockers(root: Path) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for path in (root / "build").rglob("*.spec"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"hiddenimports", "binaries"} for t in node.targets):
                for item in ast.walk(node.value):
                    if isinstance(item, ast.Constant) and isinstance(item.value, str) and _qt_name(item.value):
                        blockers.append({"path": path.relative_to(root).as_posix(), "line": item.lineno, "reference": item.value})
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "collect_dynamic_libs":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and normalize_distribution(arg.value) in {"shiboken6", "pyside6"}:
                        blockers.append({"path": path.relative_to(root).as_posix(), "line": node.lineno, "reference": arg.value})
    return blockers


def default_gui_runtime(root: Path) -> str | None:
    path = root / "src" / "hpc_gui" / "runtime.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEFAULT_GUI_RUNTIME" for t in node.targets):
            return node.value.value if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) else None
    return None


def _read_evidence(path: Path, platform: str, schema: str, checks: tuple[str, ...], commit: str | None) -> tuple[str, str | None]:
    if not path.is_file():
        return "MISSING", f"{platform}: file missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "INVALID", f"{platform}: invalid JSON"
    if not isinstance(data, dict) or data.get("schema") != schema:
        return "INVALID", f"{platform}: unsupported or missing schema"
    if not _full_sha(data.get("commit")) or data.get("commit") != commit:
        return "STALE", f"{platform}: evidence commit does not match current HEAD"
    if data.get("platform") != platform or data.get("result") != "PASS":
        return "FAIL", f"{platform}: result/platform is not PASS"
    if not isinstance(data.get("artifact"), str) or not data["artifact"]:
        return "INVALID", f"{platform}: artifact missing"
    if not isinstance(data.get("artifact_sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", data["artifact_sha256"]):
        return "INVALID", f"{platform}: artifact digest missing or invalid"
    values = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    missing = [name for name in checks if values.get(name) != "PASS"]
    if missing:
        return "INVALID", f"{platform}: mandatory checks not PASS: {', '.join(missing)}"
    return "PASS", None


def evidence_status(root: Path, directory: Path, filename: str, schema: str, checks: tuple[str, ...], commit: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for platform in REQUIRED_WX_EVIDENCE_PLATFORMS:
        status, _ = _read_evidence(directory / filename.format(platform=platform), platform, schema, checks, commit)
        result[platform] = status
    return result


def _p0_statuses(baseline: Path, status: Path) -> dict[str, str]:
    p0: dict[str, str] = {}
    for line in baseline.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].startswith("GUI-") and any("P0" == c for c in cells):
            p0[cells[0]] = "UNVERIFIED"
    for line in status.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 1 and cells[0] in p0:
            p0[cells[0]] = cells[1].upper()
    return p0


def evaluate_gate(*, p0: dict[str, str], qt_imports: list[dict[str, object]], qt_dependencies: list[dict[str, str]], qt_packaging: list[dict[str, object]], default_runtime: str | None, packaged: dict[str, str], manual: dict[str, str], commit: str | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not commit:
        reasons.append("current repository commit could not be determined")
    reasons += [f"P0 parity not covered: {key}" for key, value in p0.items() if value != "COVERED"]
    reasons += [f"Qt production import: {item['path']}:{item['line']} {item['import']}" for item in qt_imports]
    reasons += [f"Qt production dependency remains: {item['source']} -> {item['dependency']}" for item in qt_dependencies]
    reasons += [f"Qt packaging blocker: {item['path']}:{item['line']} {item['reference']}" for item in qt_packaging]
    if default_runtime != "wx":
        reasons.append(f"default GUI runtime remains: {default_runtime or 'unknown'}")
    reasons += [f"packaged wx evidence {value.lower()}: {platform}" for platform, value in packaged.items() if value != "PASS"]
    reasons += [f"manual wx evidence {value.lower()}: {platform}" for platform, value in manual.items() if value != "PASS"]
    return ("GO" if not reasons else "NO-GO"), reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    commit = current_commit(root)
    imports = production_qt_imports(root)
    dependencies = dependency_records(root)
    packaging = packaging_blockers(root)
    runtime = default_gui_runtime(root)
    packaged = evidence_status(root, root / "build" / "audit", "wx-packaged-smoke-{platform}.json", "wx-packaged-smoke/1", PACKAGED_CHECKS, commit)
    manual = evidence_status(root, root / "docs" / "v2" / "manual-results", "{platform}.json", "wx-manual-parity/1", MANUAL_CHECKS, commit)
    p0 = _p0_statuses(root / "docs/v2/GUI_FEATURE_PARITY_BASELINE.md", root / "docs/v2/V2_PARITY_STATUS.md")
    decision, reasons = evaluate_gate(p0=p0, qt_imports=imports, qt_dependencies=dependencies, qt_packaging=packaging, default_runtime=runtime, packaged=packaged, manual=manual, commit=commit)
    report = {
        "schema": "qt-removal-gate/3", "commit": commit, "decision": decision, "reasons": reasons,
        "p0": p0, "qt_imports": imports, "qt_files": sorted({item["path"] for item in imports}),
        "qt_dependencies": dependencies, "qt_packaging": packaging, "default_gui_runtime": runtime,
        "packaged_evidence": packaged, "manual_evidence": manual,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Qt Removal Readiness: {decision}")
    for reason in reasons:
        print(reason)
    print(f"Qt import points: {len(imports)}")
    print(f"Qt production files: {len(report['qt_files'])}")
    print(f"Qt dependencies: {len(dependencies)}")
    print(f"Qt packaging blockers: {len(packaging)}")
    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
