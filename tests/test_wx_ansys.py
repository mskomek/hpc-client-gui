from pathlib import Path
from types import SimpleNamespace

from hpc_gui.plugins.linter_tools import LinterTool
from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation
from hpc_gui.wx_ansys import WxAnsysModel


def test_multiple_files_grouping_sources_and_folder_cap(tmp_path: Path, monkeypatch):
    module_name = "_fake_ansys_ui"
    fake = SimpleNamespace(lint_text=lambda text, file_name="": ([], {"source_url": "https://docs.example/rule"})[0])
    monkeypatch.setitem(__import__("sys").modules, module_name, fake)
    tool = LinterTool("org.hpcclient.ansyslint", "0.1.0", "ANSYS", "", lambda **kwargs: None, module_name)
    model = WxAnsysModel(AnsysToolPresentation(tool))
    assert len(model.lint_files((("a.wbjn", "x"), ("b.txt", "x")))) == 2
    for index in range(205):
        (tmp_path / f"{index}.wbjn").write_text("x", encoding="utf-8")
    assert len(model.lint_folder(tmp_path, lambda path: path.read_text(encoding="utf-8"))) == 200
    assert model.source_url_allowed("https://docs.example/rule", {"docs.example"})


def test_broken_engine_is_contained():
    tool = LinterTool("x", "1", "broken", "", lambda **kwargs: None, "_missing_ansys")
    model = WxAnsysModel(AnsysToolPresentation(tool))
    result = model.lint_files((("x.wbjn", "text"),))[0]
    assert result.state.status == "failed"
