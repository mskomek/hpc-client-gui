from pathlib import Path


def test_wx_shell_is_optional_and_has_migration_entrypoint():
    source = Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert "import wx" in source and "from PySide6" not in source
    assert "--wx" in Path("src/hpc_gui/__main__.py").read_text(encoding="utf-8")


def test_wx_shell_uses_shared_commands_and_responsive_start_size():
    source = Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert "COMMAND_REGISTRY" in source and "size=(960, 640)" in source
    assert "TaskBarIcon" in source and "lifecycle.shutdown" in source


def test_wx_shell_dispatches_core_views():
    source = Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert 'command_id == "NAV-FILES"' in source
    assert 'command_id == "NAV-EDITOR"' in source
    assert 'command_id == "NAV-JOBS"' in source
    assert "show_jobs(parent, lifecycle=lifecycle)" in source
    assert "show_connection(parent, load_profiles(), lifecycle=lifecycle, on_connected=connected)" in source
    assert "lifecycle.register_cleanup(ssh.close)" in source
