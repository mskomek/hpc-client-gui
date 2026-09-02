from pathlib import Path

from hpc_gui.wx_logs import WxLogsModel


def test_large_log_tail_copy_and_redaction(tmp_path: Path):
    path = tmp_path / "app.log"
    path.write_text("\n".join(f"line {i} password=secret" for i in range(5100)), encoding="utf-8")
    exported = []
    model = WxLogsModel(path, bundle=lambda destination: exported.append(destination) or Path(destination) / "bundle.zip")
    text = model.refresh()
    assert "line 0" not in text and "line 5099" in text and "secret" not in text
    assert model.copy_all() == text and model.copy_selection(0, 4) == text[:4]
    assert model.export_bundle(str(tmp_path)) == tmp_path / "bundle.zip" and exported


def test_missing_log_is_empty_and_model_has_no_qt():
    model = WxLogsModel("missing.log")
    assert model.refresh() == "" and model.copy_all() == ""
    source = open("src/hpc_gui/wx_logs.py", encoding="utf-8").read()
    assert "PySide6" not in source and "import wx" not in source
