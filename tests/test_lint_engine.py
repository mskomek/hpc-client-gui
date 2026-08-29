"""Wave 08 tests: generic declarative lint engine and editor integration."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hpc_gui.lint.engine import (
    DEFAULT_MAX_DIAGNOSTICS_PER_RULE,
    MAX_LINT_TEXT_BYTES,
    LintError,
    lint_text,
)
from hpc_gui.lint.models import LintContext, RulePack, Severity
from hpc_gui.lint.rulepack import RulePackError, load_lint_packs, parse_rule


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_rule(rule_id="R001", kind="not_contains", value="bad()", severity="warning", **extra):
    rule = {
        "id": rule_id,
        "severity": severity,
        "message": f"message for {rule_id}",
        "match": {"kind": kind, "value": value},
    }
    rule.update(extra)
    return rule


def make_pack(rules, file_patterns=("*.jou",), linter_id="fluent-journal", name="Fluent"):
    return RulePack(
        linter_id=linter_id,
        name=name,
        plugin_id="org.hpcclient.fluent",
        plugin_version="0.1.0",
        file_patterns=tuple(file_patterns),
        rules=tuple(rules),
    )


def compiled(kind="contains", value="x", **kwargs):
    from hpc_gui.lint.models import CompiledRule

    defaults = dict(
        id=kwargs.pop("id", "R"),
        severity=Severity(kwargs.pop("severity", "warning")),
        kind=kind,
        message=kwargs.pop("message", "msg"),
        values=(value,),
    )
    defaults.update(kwargs)
    return CompiledRule(**defaults)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def test_contains_and_not_contains():
    pack = make_pack(
        [
            compiled("contains", "/file/set-tui-version", id="TUI-REQUIRED"),
            compiled("not_contains", "/gui/mesh", id="FORBIDDEN-GUI"),
        ]
    )
    # Missing required declaration fires; forbidden command absent stays quiet.
    diags = lint_text("/display set\n", file_name="a.jou", rule_pack=pack)
    assert [d.rule_id for d in diags] == ["TUI-REQUIRED"]

    clean = lint_text(
        "/file/set-tui-version 25.2\n", file_name="a.jou", rule_pack=pack
    )
    assert [d.rule_id for d in clean] == []

    forbidden_present = lint_text(
        "/gui/mesh\n/file/set-tui-version 25.2\n", file_name="a.jou", rule_pack=pack
    )
    assert [d.rule_id for d in forbidden_present] == ["FORBIDDEN-GUI"]


def test_regex_positions_are_line_and_column_aware():
    pack = make_pack([compiled("regex", r"solve/set\s+(\w+)", id="RX1")])
    text = "line1\n  solve/set pressure\n"
    diags = lint_text(text, file_name="a.jou", rule_pack=pack)
    assert len(diags) == 1
    assert diags[0].line == 2
    assert diags[0].column == 3


def test_line_regex_only_matches_within_lines():
    pack = make_pack([compiled("line_regex", r"^#SBATCH --time=\d+", id="SRUN")])
    text = "#SBATCH --time=01:00:00\nx #SBATCH --time=99\n"
    diags = lint_text(text, file_name="job.slurm", rule_pack=pack)
    assert [d.line for d in diags] == [1]


def test_ordered_patterns_reports_when_out_of_order():
    rules = [
        {
            "id": "ORD1",
            "severity": "error",
            "message": "init before solve",
            "match": {"kind": "ordered_patterns", "patterns": ["/file/read", "/solve/init"]},
        }
    ]
    parsed = parse_rule(rules[0], "test")
    pack = make_pack([parsed])

    good = lint_text("/file/read case.cas\n/solve/init\n", file_name="a.jou", rule_pack=pack)
    assert good == []
    bad = lint_text("/solve/init\n/file/read case.cas\n", file_name="a.jou", rule_pack=pack)
    assert len(bad) == 1
    assert bad[0].rule_id == "ORD1"


def test_count_primitive():
    raw = {
        "id": "CNT1",
        "severity": "info",
        "message": "too many saves",
        "match": {"kind": "count", "value": "/file/save", "max": 2},
    }
    pack = make_pack([parse_rule(raw, "test")])
    assert lint_text("/file/save\n/file/save\n", file_name="a.jou", rule_pack=pack) == []
    assert len(lint_text("/file/save\n" * 3, file_name="a.jou", rule_pack=pack)) == 1


def test_registry_vocabulary_aliases_accepted():
    raw = {
        "id": "TUI1",
        "severity": "error",
        "message": "TUI command in batch journal.",
        "match": {"kind": "forbidden-keyword", "value": "/gui/mesh"},
    }
    parsed = parse_rule(raw, "test")
    assert parsed.kind == "not_contains"


def test_when_target_version_gating():
    # Required keyword missing -> error only when the target version matches.
    rule = make_rule(
        "V252", kind="contains", value="/file/set-tui-version", when={"target_version": "25.2"}
    )
    parsed = parse_rule(rule, "test")
    pack = make_pack([parsed])

    matching = LintContext(application_version="25.2")
    other = LintContext(application_version="24.1")

    assert len(lint_text("/display set\n", file_name="a.jou", rule_pack=pack, context=matching)) == 1
    assert lint_text("/display set\n", file_name="a.jou", rule_pack=pack, context=other) == []
    # Missing context must skip silently (no false errors).
    assert lint_text("/display set\n", file_name="a.jou", rule_pack=pack, context=None) == []


def test_diagnostics_sorted_stably():
    rules = [
        compiled("not_contains", "b", id="B-rule", message="b"),
        compiled("not_contains", "a", id="A-rule", message="a"),
    ]
    pack = make_pack(rules)
    diags = lint_text("a then b", file_name="a.jou", rule_pack=pack)
    assert [(d.rule_id, d.column) for d in diags] == [("A-rule", 1), ("B-rule", 8)]


def test_max_diagnostics_caps():
    rule = compiled("regex", "o", id="MANY")
    pack = make_pack([rule])
    diags = lint_text("o" * 1000, file_name="a.jou", rule_pack=pack, max_diagnostics_total=7)
    assert len(diags) == 7
    _ = DEFAULT_MAX_DIAGNOSTICS_PER_RULE


def test_oversized_text_rejected():
    pack = make_pack([])
    with pytest.raises(LintError):
        lint_text("x" * (MAX_LINT_TEXT_BYTES + 1), file_name="a.jou", rule_pack=pack)


# ---------------------------------------------------------------------------
# Malformed rules / packs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        {"id": "X", "severity": "fatal", "message": "m", "match": {"kind": "contains", "value": "x"}},
        {"id": "", "severity": "info", "message": "m", "match": {"kind": "contains", "value": "x"}},
        {"id": "X", "severity": "info", "message": "", "match": {"kind": "contains", "value": "x"}},
        {"id": "X", "severity": "info", "message": "m", "match": {"kind": "eval", "value": "x"}},
        {"id": "X", "severity": "info", "message": "m", "match": {"kind": "regex", "value": "("}},
        {"id": "X", "severity": "info", "message": "m", "match": {"kind": "contains"}},
        {"id": "X", "severity": "info", "message": "m", "match": {"kind": "contains", "value": "x"}, "when": {"hostname": "h"}},
        {"id": "X", "severity": "info", "message": "m", "match": {"kind": "ordered_patterns", "patterns": []}},
    ],
)
def test_malformed_rules_rejected(raw):
    with pytest.raises(RulePackError):
        parse_rule(raw, "test")


def test_parse_rule_never_executes_values(monkeypatch):
    """A value that looks like code must be treated as plain text."""
    monkeypatch.setattr("builtins.eval", lambda *a, **k: (_ for _ in ()).throw(AssertionError("eval called")))
    rule = make_rule(value="__import__('os').system('true')")
    parsed = parse_rule(rule, "test")
    pack = make_pack([parsed])
    lint_text("nothing here", file_name="a.jou", rule_pack=pack)


def test_engine_module_has_no_execution_primitives():
    import hpc_gui.lint.engine as engine_module

    source = inspect.getsource(engine_module)
    for forbidden in ("importlib", "__import__", "exec(", "eval(", "subprocess", "os.system"):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# Plugin integration
# ---------------------------------------------------------------------------


def build_lint_plugin(root: Path, *, version="0.1.0", broken=False):
    pkg = root / "packages" / "org.hpcclient.fluent" / version
    pkg.mkdir(parents=True, exist_ok=True)

    rule_file = {
        "schema_version": 1,
        "tool": "fluent-journal",
        "rules": [
            {
                "id": "FLUENT001",
                "severity": "warning",
                "category": "compatibility",
                "message": "Journal does not declare a TUI version.",
                "suggested_fix": "Add /file/set-tui-version <version>",
                "match": {"kind": "forbidden-keyword", "value": "missing-tui-marker"},
            },
            {
                "id": "FLUENT002",
                "severity": "error",
                "category": "correctness",
                "message": "GUI-only command used.",
                "match": {"kind": "forbidden-keyword", "value": "/gui/mesh"},
            },
        ],
    }
    payload = json.dumps(rule_file).encode()
    (pkg / "rules.json").write_bytes(payload)
    if broken:
        (pkg / "lint-index.json").write_text("{broken", encoding="utf-8")
    else:
        index = {
            "schema_version": 1,
            "tool": "fluent-journal",
            "name": "ANSYS Fluent Journal",
            "file_patterns": ["*.jou"],
            "rules": [],
            "rule_files": [{"path": "rules.json", "sha256": sha256_bytes(payload)}],
        }
        (pkg / "lint-index.json").write_text(json.dumps(index), encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": "org.hpcclient.fluent",
        "name": "Fluent Journal Lint",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "Fluent journal lint rules.",
        "requires_app": ">=1.3.0",
        "capabilities": ["lint-rules"],
        "entrypoints": {"lint_index": "lint-index.json"},
        "files": [
            {
                "path": "rules.json",
                "sha256": sha256_bytes(payload),
                "size": len(payload),
                "role": "lint-rules",
            },
            {
                "path": "lint-index.json",
                "sha256": sha256_bytes((pkg / "lint-index.json").read_bytes()),
                "size": (pkg / "lint-index.json").stat().st_size,
                "role": "lint-index",
            },
        ],
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    from hpc_gui.plugins.storage import write_active_versions

    write_active_versions({"org.hpcclient.fluent": version}, root=root)


def test_installed_lint_plugin_contributes_rules(tmp_path: Path):
    build_lint_plugin(tmp_path)
    packs = load_lint_packs(root=tmp_path, app_version="1.4.0")
    assert len(packs) == 1
    pack = packs[0]
    assert pack.linter_id == "fluent-journal"
    assert pack.matches("case.jou")
    assert not pack.matches("job.slurm")

    diags = lint_text(
        "/gui/mesh\nmissing-tui-marker here too\n", file_name="run.jou", rule_pack=pack
    )
    assert [d.rule_id for d in diags] == ["FLUENT002", "FLUENT001"]


def test_broken_lint_plugin_is_skipped_silently(tmp_path: Path):
    build_lint_plugin(tmp_path, broken=True)
    packs = load_lint_packs(root=tmp_path, app_version="1.4.0")
    assert packs == []


def test_disabled_lint_plugin_contributes_nothing(tmp_path: Path):
    build_lint_plugin(tmp_path)
    from hpc_gui.plugins.state import set_plugin_disabled

    set_plugin_disabled("org.hpcclient.fluent", True, root=tmp_path)
    assert load_lint_packs(root=tmp_path, app_version="1.4.0") == []


def test_incompatible_lint_plugin_not_loaded(tmp_path: Path):
    build_lint_plugin(tmp_path)
    assert load_lint_packs(root=tmp_path, app_version="0.9.0") == []


# ---------------------------------------------------------------------------
# Editor integration
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from hpc_gui.core.i18n import load_language

    load_language("en")
    yield app


def _make_dialog_with_box_capture():
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    widget = EditorWidget()
    shown = []

    class FakeBox:
        Information = 1

        @staticmethod
        def information(*args, **kwargs):
            shown.append(("information", args))

        @staticmethod
        def warning(*args, **kwargs):
            shown.append(("warning", args))

    return widget, FakeBox, shown


def test_editor_without_linter_shows_no_linter_hint(qapp, monkeypatch):
    from hpc_gui.core.i18n import t

    monkeypatch.setattr("hpc_gui.lint.rulepack.load_lint_packs", lambda: [])
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.tools_supporting_suffix", lambda _suffix: []
    )
    widget, FakeBox, shown = _make_dialog_with_box_capture()
    widget.path_in.setText("case.jou")
    widget.text.setPlainText("/display set\n")
    monkeypatch.setattr("hpc_gui.ui.widgets.editor_widget.QMessageBox", FakeBox)
    widget.run_lint()
    assert any(t("editor.lint_ok") in str(args) for _, args in shown)


def test_editor_runs_installed_linter_for_jou_files(qapp, tmp_path, monkeypatch):
    build_lint_plugin(tmp_path)
    widget, FakeBox, shown = _make_dialog_with_box_capture()

    executed = []

    def fake_lint_text(text, *, file_name, rule_pack, **kwargs):
        executed.append((file_name, rule_pack.linter_id))
        from hpc_gui.lint.models import Diagnostic

        return [
            Diagnostic(
                rule_id="FLUENT002",
                severity=Severity.ERROR,
                message="GUI-only command used.",
                line=1,
                column=1,
                plugin_id=rule_pack.plugin_id,
            )
        ]

    monkeypatch.setattr("hpc_gui.lint.engine.lint_text", fake_lint_text)
    test_pack = make_pack(
        [compiled("forbidden-keyword", "/gui/mesh", id="FLUENT002")],
        file_patterns=("*.jou",),
    )
    monkeypatch.setattr(
        "hpc_gui.lint.rulepack.load_lint_packs", lambda *a, **k: [test_pack]
    )
    monkeypatch.setattr(
        widget,
        "_show_lint_results",
        lambda path, issues, diagnostics: shown.append((path, issues, diagnostics)),
    )
    monkeypatch.setattr("hpc_gui.ui.widgets.editor_widget.QMessageBox", FakeBox)

    widget.path_in.setText("case.jou")
    widget.text.setPlainText("/gui/mesh\n")
    widget.run_lint()

    assert executed and executed[0] == ("case.jou", "fluent-journal")
    path, issues, diagnostics = shown[0]
    assert diagnostics and diagnostics[0].rule_id == "FLUENT002"
    _ = path, issues


def test_lint_result_entries_are_line_aware(qapp):
    from hpc_gui.lint.models import Diagnostic
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    diagnostics = [
        Diagnostic(rule_id="B2", severity=Severity.INFO, message="b", line=3, column=2),
        Diagnostic(rule_id="A1", severity=Severity.ERROR, message="a", line=1, column=5),
    ]
    labels, positions = EditorWidget._lint_result_entries(["builtin issue"], diagnostics)
    assert labels[0] == "- builtin issue"
    assert positions[0] == -1
    # Sorted by line.
    assert "A1" in labels[1] and "B2" in labels[2]
    assert positions[1:] == [0, 2]


def test_editor_lint_does_not_mutate_file(qapp, tmp_path, monkeypatch):
    target = tmp_path / "case.jou"
    target.write_text("/display set\n", encoding="utf-8")
    widget, FakeBox, _ = _make_dialog_with_box_capture()
    monkeypatch.setattr("hpc_gui.ui.widgets.editor_widget.QMessageBox", FakeBox)
    monkeypatch.setattr(
        widget,
        "_show_lint_results",
        lambda *args: None,
    )
    widget.path_in.setText(str(target))
    original = target.read_bytes()
    widget.run_lint()
    assert target.read_bytes() == original
