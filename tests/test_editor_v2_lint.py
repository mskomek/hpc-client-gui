"""Wave 73: EditorWidget hybrid lint (v1 packs + v2 tool)."""

from __future__ import annotations

import os
import types

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from hpc_gui.core.i18n import load_language

    load_language("en")
    yield app


def _fake_engine_diag(code="FLUENT_X", line=2):
    sev = types.SimpleNamespace(value="warning")
    return types.SimpleNamespace(
        code=code,
        severity=sev,
        message=f"engine {code}",
        line=line,
        column=1,
        endLine=None,
        endColumn=None,
        explanation="explain",
        suggestedFix="fix it",
        source_url="https://example.test/doc",
        rule_id=code,
    )


def _stub_v2(monkeypatch, diags, suffix=".jou"):
    from hpc_gui.plugins.linter_tools import LinterTool

    tool = LinterTool(
        plugin_id="org.fake",
        version="0.1.0",
        title="Fake",
        description="",
        page_factory=lambda **k: None,
        module_name="fake_engine",
    )
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.tools_supporting_suffix",
        lambda s: [tool] if s == suffix else [],
    )
    fake_run = types.SimpleNamespace(diagnostics=list(diags))
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.lint_text_with_tool",
        lambda text, file_name="", options=None: fake_run,
    )
    return tool


def test_run_v2_tool_lint_maps_engine_diag(qapp, monkeypatch):
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    diag = _fake_engine_diag(code="FLUENT_GUI_IN_HEADLESS", line=5)
    _stub_v2(monkeypatch, [diag], suffix=".jou")

    w = EditorWidget()
    converted = w._run_v2_tool_lint("job.jou", "/display/set\n")

    assert len(converted) == 1
    assert converted[0].rule_id == "FLUENT_GUI_IN_HEADLESS"
    assert converted[0].line == 5
    assert converted[0].plugin_id == "org.fake"
    assert "fix it" in converted[0].suggested_fix


def test_run_v2_tool_lint_unsupported_suffix_returns_empty(qapp, monkeypatch):
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    _stub_v2(monkeypatch, [_fake_engine_diag()], suffix=".jou")

    w = EditorWidget()
    assert w._run_v2_tool_lint("notes.xyz", "hello") == []


def test_run_v2_tool_lint_broken_engine_is_contained(qapp, monkeypatch):
    from hpc_gui.ui.widgets.editor_widget import EditorWidget
    from hpc_gui.plugins.linter_tools import LinterTool

    tool = LinterTool(
        plugin_id="org.broken",
        version="0.1.0",
        title="Broken",
        description="",
        page_factory=lambda **k: None,
        module_name="broken_engine",
    )
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.tools_supporting_suffix",
        lambda s: [tool] if s == ".jou" else [],
    )
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.lint_text_with_tool",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("engine boom")),
    )

    w = EditorWidget()
    # Must not raise; must return empty so editor still shows v1 results.
    assert w._run_v2_tool_lint("job.jou", "text") == []


def test_run_lint_merges_v2_with_v1(qapp, monkeypatch):
    from hpc_gui.lint.models import Diagnostic, Severity
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    # Stub v1 packs to return one diagnostic.
    v1_diag = Diagnostic(
        rule_id="V1_RULE", severity=Severity.WARNING, message="v1", line=1
    )
    monkeypatch.setattr(
        "hpc_gui.ui.widgets.editor_widget.EditorWidget._run_plugin_lint",
        lambda self, p, t: [v1_diag],
    )
    monkeypatch.setattr(
        "hpc_gui.ui.widgets.editor_widget.EditorWidget._run_cross_checks",
        lambda self, t: [],
    )
    diag = _fake_engine_diag(code="V2_RULE", line=2)
    _stub_v2(monkeypatch, [diag], suffix=".jou")

    shown = {}

    def fake_show(path, issues, diagnostics):
        shown["diagnostics"] = list(diagnostics)

    w = EditorWidget()
    w.path_in.setText("job.jou")
    w.text.setPlainText("/display/set\n")
    monkeypatch.setattr(w, "_show_lint_results", fake_show)
    # Avoid the QMessageBox path for lint_need_path / lint_ok
    w.run_lint()

    codes = [d.rule_id for d in shown["diagnostics"]]
    assert "V1_RULE" in codes
    assert "V2_RULE" in codes
