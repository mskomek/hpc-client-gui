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
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.lint_text_with_tool_for",
        lambda tool_arg, text, file_name="", options=None: fake_run,
    )
    return tool


def _stub_v2_multi(monkeypatch, tool_diags: list[tuple]):
    """Stub multiple tools; tool_diags is list of (tool, [diags])."""
    from hpc_gui.plugins.linter_tools import LinterTool  # noqa: F401

    tools = [t for t, _ in tool_diags]
    suffix_map: dict[str, list] = {}
    for tool, diags in tool_diags:
        # Register each tool's diags by plugin_id for the for-loop stub.
        suffix_map[tool.plugin_id] = diags
    # All tools declare .py for the multi test; adjust as needed.
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.tools_supporting_suffix",
        lambda s: list(tools) if s in (".py", ".jou") else [],
    )

    def fake_for(tool_arg, text, file_name="", options=None):
        return types.SimpleNamespace(diagnostics=list(suffix_map.get(tool_arg.plugin_id, [])))

    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.lint_text_with_tool_for",
        fake_for,
    )


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
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.lint_text_with_tool_for",
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


def test_multi_tool_aggregation_and_prefix(qapp, monkeypatch):
    from hpc_gui.plugins.linter_tools import LinterTool
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    tool_a = LinterTool("org.a", "0.1.0", "A", "", lambda **k: None, "mod_a")
    tool_b = LinterTool("org.b", "0.1.0", "B", "", lambda **k: None, "mod_b")
    diag_a = _fake_engine_diag(code="CODE_A", line=2)
    diag_b = _fake_engine_diag(code="CODE_B", line=1)
    _stub_v2_multi(monkeypatch, [(tool_a, [diag_a]), (tool_b, [diag_b])])

    w = EditorWidget()
    converted = w._run_v2_tool_lint("script.py", "x")

    assert [d.rule_id for d in converted] == ["CODE_B", "CODE_A"]  # sorted by line
    assert all("[org." in d.message for d in converted)  # prefix when multiple
    assert {d.plugin_id for d in converted} == {"org.a", "org.b"}


def test_multi_tool_dedup_same_diag(qapp, monkeypatch):
    from hpc_gui.plugins.linter_tools import LinterTool
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    tool_a = LinterTool("org.a", "0.1.0", "A", "", lambda **k: None, "mod_a")
    tool_b = LinterTool("org.b", "0.1.0", "B", "", lambda **k: None, "mod_b")
    diag = _fake_engine_diag(code="SAME", line=3)
    _stub_v2_multi(monkeypatch, [(tool_a, [diag]), (tool_b, [diag])])

    w = EditorWidget()
    converted = w._run_v2_tool_lint("script.py", "x")

    assert len(converted) == 1
    assert converted[0].rule_id == "SAME"


def test_multi_tool_broken_second_is_contained(qapp, monkeypatch):
    from hpc_gui.plugins.linter_tools import LinterTool
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

    tool_ok = LinterTool("org.ok", "0.1.0", "OK", "", lambda **k: None, "mod_ok")
    tool_broken = LinterTool("org.broken2", "0.1.0", "Broken", "", lambda **k: None, "mod_broken")
    diag_ok = _fake_engine_diag(code="OK_CODE", line=1)

    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.tools_supporting_suffix",
        lambda s: [tool_ok, tool_broken] if s == ".py" else [],
    )

    def fake_for(tool_arg, text, file_name="", options=None):
        if tool_arg.plugin_id == "org.ok":
            return types.SimpleNamespace(diagnostics=[diag_ok])
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.lint_text_with_tool_for",
        fake_for,
    )

    w = EditorWidget()
    converted = w._run_v2_tool_lint("script.py", "x")

    assert len(converted) == 1
    assert converted[0].rule_id == "OK_CODE"


def test_tools_supporting_all_suffixes_intersection(monkeypatch):
    from hpc_gui.plugins.linter_tools import LinterTool, tools_supporting_all_suffixes

    def fake_suffixes(tool):
        return {".jou", ".py"} if tool.plugin_id == "org.a" else {".jou"}

    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.tool_supported_suffixes", fake_suffixes
    )
    tool_a = LinterTool("org.a", "0.1.0", "A", "", lambda **k: None, "mod_a")
    tool_b = LinterTool("org.b", "0.1.0", "B", "", lambda **k: None, "mod_b")
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.list_linter_tools",
        lambda *a, **k: [tool_a, tool_b],
    )

    assert [t.plugin_id for t in tools_supporting_all_suffixes([".jou"])] == [
        "org.a",
        "org.b",
    ]
    assert [t.plugin_id for t in tools_supporting_all_suffixes([".jou", ".py"])] == [
        "org.a"
    ]
    assert tools_supporting_all_suffixes([".jou", ".xyz"]) == []
