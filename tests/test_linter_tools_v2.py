"""Plugin API v2 linter-tool host helpers and results dialog formatting.

These tests stub the engine module instead of touching the real user
plugin installation, so they stay deterministic on every machine. The
regression root: ``SUPPORTED_SUFFIXES`` lives in the engine's ``api``
submodule, not the package ``__init__`` - without the fallback the file
panel context-menu actions could never enable.
"""

from __future__ import annotations

import sys
import types

import pytest

from hpc_gui.plugins.linter_tools import (
    LinterTool,
    ToolLoadError,
    first_linter_tool,
    lint_text_with_tool,
    supported_suffixes,
)


def _install_stub_engine(monkeypatch, *, api_suffixes=(".jou",), init_attr=None):
    """Register a fake engine package (with an ``api`` sibling) in sys.modules."""
    package = types.ModuleType("fake_lint_engine")
    if init_attr is not None:
        setattr(package, "SUPPORTED_SUFFIXES", init_attr)
    package.__path__ = []  # mark as package for importlib
    api = types.ModuleType("fake_lint_engine.api")
    api.SUPPORTED_SUFFIXES = set(api_suffixes)
    monkeypatch.setitem(sys.modules, "fake_lint_engine", package)
    monkeypatch.setitem(sys.modules, "fake_lint_engine.api", api)

    tool = LinterTool(
        plugin_id="org.hpcclient.fake",
        version="0.1.0",
        title="Fake",
        description="",
        page_factory=lambda **kwargs: None,
        module_name="fake_lint_engine",
    )
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.first_linter_tool", lambda *a, **k: tool
    )
    return tool


# ---------------------------------------------------------------------------
# supported_suffixes()
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_supported_suffixes_falls_back_to_api_submodule(monkeypatch):
    _install_stub_engine(monkeypatch)  # attribute only on the .api submodule
    assert supported_suffixes() == frozenset({".jou"})


@pytest.mark.contract
def test_supported_suffixes_prefers_package_attribute(monkeypatch):
    _install_stub_engine(
        monkeypatch, api_suffixes=(".dat",), init_attr={".wbjn", ".JOu"}
    )
    # Package-level declaration wins and entries are normalized to lowercase.
    assert supported_suffixes() == frozenset({".jou", ".wbjn"})


@pytest.mark.contract
def test_supported_suffixes_empty_when_no_tool_installed(monkeypatch):
    def raise_missing(*_args, **_kwargs):
        raise ToolLoadError("No linter tool plugin is installed.")

    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.first_linter_tool", raise_missing
    )
    assert supported_suffixes() == frozenset()


# ---------------------------------------------------------------------------
# tools_supporting_suffix() lists every supporting tool.
# ---------------------------------------------------------------------------


def _fake_tool(module_name, plugin_id):
    return LinterTool(
        plugin_id=plugin_id,
        version="0.1.0",
        title=plugin_id,
        description="",
        page_factory=lambda **kwargs: None,
        module_name=module_name,
    )


def _install_fake_module(monkeypatch, module_name, suffixes):
    package = types.ModuleType(module_name)
    package.__path__ = []
    api = types.ModuleType(f"{module_name}.api")
    api.SUPPORTED_SUFFIXES = set(suffixes)
    monkeypatch.setitem(sys.modules, module_name, package)
    monkeypatch.setitem(sys.modules, f"{module_name}.api", api)


@pytest.mark.contract
def test_tools_supporting_suffix_filters_tools(monkeypatch):
    from hpc_gui.plugins.linter_tools import tools_supporting_suffix

    _install_fake_module(monkeypatch, "engine_a", {".jou", ".wbjn"})
    _install_fake_module(monkeypatch, "engine_b", {".ccl"})
    tools = [
        _fake_tool("engine_a", "org.a"),
        _fake_tool("engine_b", "org.b"),
    ]
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.list_linter_tools", lambda *a, **k: tools
    )
    matches = tools_supporting_suffix(".jou")
    assert [tool.plugin_id for tool in matches] == ["org.a"]
    assert tools_supporting_suffix(".xyz") == []
    assert tools_supporting_suffix("") == []


@pytest.mark.contract
def test_tools_supporting_suffix_tolerates_broken_engine(monkeypatch):
    from hpc_gui.plugins.linter_tools import tools_supporting_suffix

    _install_fake_module(monkeypatch, "engine_ok", {".jou"})
    tools = [
        _fake_tool("engine_missing", "org.missing"),  # module never registered
        _fake_tool("engine_ok", "org.ok"),
    ]
    monkeypatch.setattr(
        "hpc_gui.plugins.linter_tools.list_linter_tools", lambda *a, **k: tools
    )
    assert [tool.plugin_id for tool in tools_supporting_suffix(".jou")] == ["org.ok"]


# ---------------------------------------------------------------------------
# temp_copy_for_tool() / remove_temp_copy()
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.resource
def test_temp_copy_preserves_suffix_and_content():
    from hpc_gui.plugins.linter_tools import remove_temp_copy, temp_copy_for_tool

    temp_path = temp_copy_for_tool("/file/read a.jou\n", "/truba/home/x/job.jou")
    try:
        assert temp_path.suffix == ".jou"
        assert temp_path.read_text(encoding="utf-8") == "/file/read a.jou\n"
        assert temp_path.exists()
    finally:
        remove_temp_copy(temp_path)
    assert not temp_path.exists()


@pytest.mark.unit
@pytest.mark.resource
def test_temp_copy_without_suffix_uses_txt():
    from hpc_gui.plugins.linter_tools import remove_temp_copy, temp_copy_for_tool

    temp_path = temp_copy_for_tool("data", "noextension")
    try:
        assert temp_path.suffix == ".txt"
    finally:
        remove_temp_copy(temp_path)


# ---------------------------------------------------------------------------
# first_linter_tool() against an empty (isolated) plugins root
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_first_linter_tool_raises_actionable_error_without_plugins(tmp_path):
    with pytest.raises(ToolLoadError) as excinfo:
        first_linter_tool(root=tmp_path)
    assert "Plugin Manager" in str(excinfo.value)


# ---------------------------------------------------------------------------
# lint_text_with_tool() forwards options to the engine module
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lint_text_with_tool_forwards_options(monkeypatch):
    tool = _install_stub_engine(monkeypatch)
    calls = []

    def fake_lint_text(text, *, file_name="", options=None):
        calls.append((text, file_name, options))
        return "run-result"

    sys.modules[tool.module_name].lint_text = fake_lint_text
    assert lint_text_with_tool("abc", file_name="a.jou", options=object()) == "run-result"
    assert len(calls) == 1
    assert calls[0][0:2] == ("abc", "a.jou")


# ---------------------------------------------------------------------------
# Results dialog pure formatting (no Qt widgets instantiated)
# ---------------------------------------------------------------------------


class _Severity:
    def __init__(self, value):
        self.value = value


class _Diag:
    def __init__(self, code="C1", severity="warning", line=2, column=3, fix=None, url=None):
        self.code = code
        self.severity = _Severity(severity)
        self.line = line
        self.column = column
        self.message = f"message {code}"
        self.explanation = ""
        self.suggested_fix = fix
        self.source_url = url
        self.source_title = "" if url is None else "Title"
        self.is_heuristic = False


class _Detection:
    product = "fluent"
    detected_version = "25.2"


class _FileResult:
    file_path = "job.jou"
    detection = _Detection()
    summary = {"error": 0, "warning": 1, "info": 0}

    def __init__(self, diagnostics):
        self._diags = diagnostics
        self.diagnostics = diagnostics

    def sorted_diagnostics(self):
        return self._diags


@pytest.mark.unit
def test_format_file_entries_lists_location_fix_and_source():
    from hpc_gui.services.lint_result_format import format_file_entries

    diag = _Diag(fix="/file/set-tui-version \"25.2\"", url="https://example.test/doc")
    lines = format_file_entries(_FileResult([diag]))
    assert lines[0].startswith("job.jou") and "fluent" in lines[0]
    assert any("2:3" in ln and "C1" in ln for ln in lines)
    assert any('fix:' in ln for ln in lines)
    assert any("https://example.test/doc" in ln for ln in lines)
    assert any("why flagged" in ln.lower() for ln in lines)
    assert any("confidence: structural" in ln.lower() for ln in lines)


@pytest.mark.unit
def test_format_run_entries_groups_by_file_and_reports_totals():
    from hpc_gui.services.lint_result_format import format_run_entries

    class _Run:
        files = [_FileResult([])]

    groups = format_run_entries(_Run())
    assert len(groups) == 1
    header, lines = groups[0]
    assert header == "job.jou"
    assert any("no findings" in ln for ln in lines)


@pytest.mark.unit
def test_diagnostic_explanation_omits_missing_fields():
    from hpc_gui.services.lint_result_format import format_diagnostic_explanation

    diagnostic = _Diag(fix="fix command", url="https://example.test/doc")
    diagnostic.explanation = "The journal uses a version-sensitive command."
    diagnostic.is_heuristic = True
    lines = format_diagnostic_explanation(diagnostic)
    assert any("Why flagged: The journal uses" in line for line in lines)
    assert any("Confidence: heuristic" in line for line in lines)
    assert any("Suggested action:" in line for line in lines)
    assert any("Documentation:" in line for line in lines)
    missing = format_diagnostic_explanation(_Diag(code="C2", fix=None, url=None))
    assert not any("Suggested action:" in line for line in missing)
    assert not any("Documentation:" in line for line in missing)


@pytest.mark.integration
def test_remote_folder_lint_recurses_only_supported_files(monkeypatch):
    from types import SimpleNamespace
    from hpc_gui.services.file_lint import collect_documents, lint_documents, LintCatalog
    from hpc_gui.services.files_mock import MockFilesBackend

    tool = _install_stub_engine(monkeypatch, api_suffixes=(".slurm",))
    calls = []

    def lint(text, **kwargs):
        calls.append((text, kwargs["file_name"]))
        return SimpleNamespace(diagnostics=[])

    sys.modules[tool.module_name].lint_text = lint
    backend = MockFilesBackend()
    catalog = LintCatalog((), ((tool, frozenset({".slurm"})),))
    documents = collect_documents([("/arf/scratch/user", True)], catalog, files=backend)
    result = lint_documents(documents, catalog)
    assert [d.path for d in documents] == ["/arf/scratch/user/job.slurm"]
    assert len(result.files) == 1 and result.files[0].diagnostics == ()
    assert calls == [(backend.read_text("/arf/scratch/user/job.slurm"), "/arf/scratch/user/job.slurm")]


@pytest.mark.integration
@pytest.mark.resource
def test_remote_tool_snapshot_does_not_materialize_temp_copy(monkeypatch):
    from hpc_gui.services.file_lint import collect_documents, LintCatalog
    from hpc_gui.services.files_mock import MockFilesBackend

    def forbidden(*args, **kwargs):
        pytest.fail("snapshot must not materialize a temporary file")

    monkeypatch.setattr("hpc_gui.plugins.linter_tools.temp_copy_for_tool", forbidden)
    tool = _install_stub_engine(monkeypatch, api_suffixes=(".txt",))
    backend = MockFilesBackend()
    catalog = LintCatalog((), ((tool, frozenset({".txt"})),))
    path = "/arf/scratch/user/example.txt"
    documents = collect_documents([(path, False)], catalog, files=backend, tool_only=True)
    assert len(documents) == 1
    assert documents[0].path == path
    assert documents[0].text == backend.read_text(path)
    assert catalog.common_tools(documents) == (tool,)
