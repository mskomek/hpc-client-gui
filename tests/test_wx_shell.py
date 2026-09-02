from pathlib import Path


def test_wx_shell_is_optional_and_has_migration_entrypoint():
    source = Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert "import wx" in source and "from PySide6" not in source
    assert "--wx" in Path("src/hpc_gui/__main__.py").read_text(encoding="utf-8")


def test_wx_shell_uses_shared_commands_and_responsive_start_size():
    source = Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert "COMMAND_REGISTRY" in source and "size=(960, 640)" in source
