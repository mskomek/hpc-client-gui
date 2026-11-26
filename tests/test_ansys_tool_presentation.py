from types import SimpleNamespace

import pytest

from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation, approved_tool_manifest
from hpc_gui.plugins.linter_tools import LinterTool


@pytest.mark.integration
def test_headless_tool_model_and_failure_isolation(monkeypatch):
    module_name = "_fake_ansys_tool"
    fake = SimpleNamespace(lint_text=lambda text, file_name="": [{"line": 1, "message": "warning"}])
    monkeypatch.setitem(__import__("sys").modules, module_name, fake)
    tool = LinterTool("org.hpcclient.ansyslint", "0.1.0", "ANSYS", "Journal lint", lambda **kwargs: None, module_name)
    presentation = AnsysToolPresentation(tool)
    assert presentation.view.suffixes == frozenset()
    assert presentation.run("text", "a.wbjn").status == "completed"
    broken = LinterTool("x", "1", "broken", "", lambda **kwargs: None, "_missing_tool")
    assert AnsysToolPresentation(broken).run("text").status == "failed"


@pytest.mark.contract
def test_trusted_tool_allowlist_remains_fail_closed():
    assert approved_tool_manifest({"id": "org.example.bad"}) is False



def test_real_file_result_shape_and_approved_wx_host(monkeypatch):
    import sys
    from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost

    finding = SimpleNamespace(code="RULE", message="finding")
    module_name = "_fake_ansys_file_result"
    monkeypatch.setitem(sys.modules, module_name, SimpleNamespace(
        SUPPORTED_SUFFIXES={".jou"}, lint_text=lambda text, file_name="": SimpleNamespace(diagnostics=[finding])))
    def forbidden_page(**kwargs):
        pytest.fail("Qt page factory must not be called")
    tool = LinterTool("org.hpcclient.ansyslint", "1", "ANSYS", "", forbidden_page, module_name)
    assert AnsysToolPresentation(tool).run("text", "job.jou").diagnostics == (finding,)

    approved = SimpleNamespace(manifest=SimpleNamespace(
        id=tool.plugin_id, publisher="HPC Client GUI", plugin_api=2,
        capabilities=["linter-tool"], entrypoints={"linter_engine":"engine/ansys_lint/__init__.py"}))
    blocked = SimpleNamespace(manifest=SimpleNamespace(
        id="unapproved", publisher="HPC Client GUI", plugin_api=2,
        capabilities=["linter-tool"], entrypoints={"linter_engine":"engine/ansys_lint/__init__.py"}))
    opened = []
    monkeypatch.setattr("hpc_gui.plugins.linter_tools.load_tool_for_plugin", lambda plugin: tool)
    monkeypatch.setattr("hpc_gui.wx_ansys_view.show_ansys_lint",
                        lambda parent, presentation, lifecycle=None: opened.append((parent, presentation.tool, lifecycle)))
    host = WxPluginMenuHost(parent="owner")
    assert not host.open_trusted_tool(blocked) and not opened
    assert host.open_trusted_tool(approved)
    assert opened == [("owner", tool, None)]
