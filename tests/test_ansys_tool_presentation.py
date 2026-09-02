from types import SimpleNamespace

from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation, approved_tool_manifest
from hpc_gui.plugins.linter_tools import LinterTool


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


def test_trusted_tool_allowlist_remains_fail_closed():
    assert approved_tool_manifest({"id": "org.example.bad"}) is False
