from __future__ import annotations

import ast
import json
import re
import string
from pathlib import Path


UI_METHODS = {
    "addAction",
    "addTab",
    "setAccessibleDescription",
    "setAccessibleName",
    "setDetailedText",
    "setHeaderLabels",
    "setInformativeText",
    "setLabelText",
    "setPlaceholderText",
    "setStatusTip",
    "setText",
    "setToolTip",
    "setWhatsThis",
    "setWindowTitle",
}
UI_CONSTRUCTORS = {
    "QAction",
    "QCheckBox",
    "QGroupBox",
    "QLabel",
    "QMenu",
    "QPushButton",
    "QRadioButton",
    "QToolButton",
}
WX_CONSTRUCTORS = {
    "Button", "StaticText", "CheckBox", "RadioButton", "StaticBox", "Dialog",
    "ToggleButton", "Choice", "ListBox", "ComboBox", "MenuItem",
}
WX_CONTROL_METHODS = {"SetLabel", "SetTitle", "SetToolTip", "SetHelpText"}
MESSAGEBOX_METHODS = {"critical", "information", "question", "warning"}
FILE_DIALOG_METHODS = {"getExistingDirectory", "getOpenFileName", "getOpenFileNames", "getSaveFileName"}
I18N_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
# The only non-splash harness exclusion is the standalone mock splash entrypoint.
HARDCODED_UI_ALLOWLIST: set[str] = set()


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_messagebox_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "QMessageBox"
        and node.func.attr in MESSAGEBOX_METHODS
    )


def _literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value.strip()
        if text and any(ch.isalpha() for ch in text):
            return node.value
    return None


def _visible_literals(node: ast.AST) -> list[ast.Constant]:
    """Return user-authored literals within a UI argument, including f-strings."""
    found: list[ast.Constant] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value.strip()
        visible_text = re.sub(r"</?[A-Za-z][^>]*>", "", text).strip(" :/\t\r\n")
        if (
            _literal_text(node)
            and visible_text.strip(" →").lower() != "v"
            and any(ch.isalpha() for ch in visible_text)
        ):
            found.append(node)
    elif isinstance(node, ast.JoinedStr):
        for value in node.values:
            if isinstance(value, ast.Constant) and _visible_literals(value):
                found.append(value)
    elif isinstance(node, (ast.BinOp, ast.IfExp)):
        for child in ast.iter_child_nodes(node):
            found.extend(_visible_literals(child))
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t":
        # Translation calls are accepted; inspect conditional fallback branches separately.
        return []
    return found


def _wx_constructor_args(node: ast.Call) -> list[ast.AST]:
    if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name) or node.func.value.id != "wx":
        return []
    if node.func.attr == "MessageBox":
        return node.args[:2]
    if node.func.attr in WX_CONSTRUCTORS:
        keyword = "title" if node.func.attr == "Dialog" else "label"
        for item in node.keywords:
            if item.arg == keyword:
                return [item.value]
        if node.func.attr == "Dialog" and len(node.args) > 1:
            return [node.args[1]]
        if len(node.args) > 1:
            return [node.args[1]]
    return []


def _iter_literal_args(arg: ast.AST):
    if isinstance(arg, (ast.List, ast.Tuple)):
        yield from arg.elts
    else:
        yield arg


def find_hardcoded_ui_strings(src_root: Path) -> list[str]:
    findings: list[str] = []
    # __main2__ is a standalone mock startup/update splash harness; every
    # visible string in it belongs to the splash flow excluded by this audit.
    for path in sorted(src_root.rglob("*.py")):
        if path.name in HARDCODED_UI_ALLOWLIST or any(
            part in {"i18n", "__pycache__"} for part in path.parts
        ) or path.name in {"wx_splash.py", "splash_screen.py", "__main2__.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            args: list[ast.AST] = []
            if name in UI_METHODS:
                args = node.args[:1]
            elif name in UI_CONSTRUCTORS:
                args = node.args[:1]
            elif _is_messagebox_call(node):
                args = node.args[1:3]
            elif name in WX_CONTROL_METHODS:
                args = node.args[:1]
            elif name in FILE_DIALOG_METHODS:
                args = node.args[1:2]
            if not args:
                args.extend(_wx_constructor_args(node))
            for arg in args:
                for item in _visible_literals(arg):
                    rel = path.relative_to(src_root.parent.parent)
                    findings.append(f"{rel}:{item.lineno}: {item.value!r}")
    return findings


def find_hardcoded_html_accessibility_strings(src_root: Path) -> list[str]:
    findings: list[str] = []
    attribute = re.compile(r"\b(?:aria-label|aria-description|placeholder|alt)\s*=\s*(['\"])(.*?)\1", re.I)
    for path in sorted(src_root.rglob("*.html")):
        if any(part in {"vendor", "node_modules"} for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8")
        for match in attribute.finditer(content):
            value = match.group(2).strip()
            if value and not value.startswith("{{") and any(ch.isalpha() for ch in value):
                line = content.count("\n", 0, match.start()) + 1
                rel = path.relative_to(src_root.parent.parent)
                findings.append(f"{rel}:{line}: {value!r}")
    return findings


def _is_translation_list_name(name: str) -> bool:
    upper = name.upper()
    return upper.endswith("_KEYS") or upper.endswith("_LABELS")


def _iter_string_literals(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
    elif isinstance(node, (ast.List, ast.Tuple)):
        for item in node.elts:
            yield from _iter_string_literals(item)


def find_missing_translation_references(src_root: Path, catalog_keys: set[str]) -> list[str]:
    findings: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        if any(part in {"i18n", "__pycache__"} for part in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    key = arg.value
                    if key not in catalog_keys:
                        rel = path.relative_to(src_root.parent.parent)
                        findings.append(f"{rel}:{arg.lineno}: {key!r}")
            elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and _is_translation_list_name(target.id)
                for target in node.targets
            ):
                for item in _iter_string_literals(node.value):
                    key = item.value.strip()
                    if key == "---":
                        continue
                    if I18N_KEY_PATTERN.match(key) and key not in catalog_keys:
                        rel = path.relative_to(src_root.parent.parent)
                        findings.append(f"{rel}:{item.lineno}: {key!r}")
    return findings


def flatten_keys(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in (d or {}).items():
        if not isinstance(k, str):
            continue
        p = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out |= flatten_keys(v, p)
        else:
            out.add(p)
    return out


def flatten_values(d: dict, prefix: str = "") -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in (d or {}).items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            values.update(flatten_values(value, path))
        elif isinstance(value, str):
            values[path] = value
    return values


def validate_placeholders(tr: dict, en: dict) -> list[str]:
    issues: list[str] = []
    tr_values, en_values = flatten_values(tr), flatten_values(en)
    formatter = string.Formatter()
    for key in sorted(set(tr_values) & set(en_values)):
        parsed: dict[str, set[str]] = {}
        for language, value in (("tr", tr_values[key]), ("en", en_values[key])):
            try:
                parsed[language] = {
                    field for _, field, _, _ in formatter.parse(value) if field
                }
            except ValueError as exc:
                issues.append(f"{language}.json:{key}: invalid format string ({exc})")
        if len(parsed) == 2 and parsed["tr"] != parsed["en"]:
            issues.append(
                f"placeholder mismatch {key}: tr={sorted(parsed['tr'])}, en={sorted(parsed['en'])}"
            )
    return issues


def main() -> int:
    # Windows consoles may use legacy code pages that cannot print Turkish text.
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    base = Path(__file__).resolve().parents[1] / "src" / "hpc_gui" / "i18n"
    tr = json.loads((base / "tr.json").read_text(encoding="utf-8"))
    en = json.loads((base / "en.json").read_text(encoding="utf-8"))
    k_tr = flatten_keys(tr)
    k_en = flatten_keys(en)
    miss_en = sorted(k_tr - k_en)
    miss_tr = sorted(k_en - k_tr)
    src_root = Path(__file__).resolve().parents[1] / "src" / "hpc_gui"
    hardcoded = find_hardcoded_ui_strings(src_root)
    hardcoded.extend(find_hardcoded_html_accessibility_strings(src_root))
    missing_refs = find_missing_translation_references(src_root, k_tr & k_en)
    placeholder_issues = validate_placeholders(tr, en)
    if not miss_en and not miss_tr and not hardcoded and not missing_refs and not placeholder_issues:
        print("i18n key check: OK")
        print("i18n reference check: OK")
        print("i18n hardcoded UI text check: OK")
        return 0
    print("i18n check: FAILED")
    if miss_en:
        print(f"Missing in en.json ({len(miss_en)}):")
        for k in miss_en:
            print("  -", k)
    if miss_tr:
        print(f"Missing in tr.json ({len(miss_tr)}):")
        for k in miss_tr:
            print("  -", k)
    if hardcoded:
        print(f"Hardcoded UI strings ({len(hardcoded)}):")
        for item in hardcoded:
            print("  -", item)
    if missing_refs:
        print(f"Missing i18n references ({len(missing_refs)}):")
        for item in missing_refs:
            print("  -", item)
    if placeholder_issues:
        print(f"Translation placeholder issues ({len(placeholder_issues)}):")
        for item in placeholder_issues:
            print("  -", item)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
