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
    assert "open_editor_new_window=lambda path: open_local(path, True)" in source
    assert "Path(path).read_text" in source and "wx.CallAfter(show_editor" in source
    assert 'command_id == "NAV-EDITOR"' in source
    assert 'command_id == "NAV-JOBS"' in source
    assert "show_jobs(parent, lifecycle=lifecycle)" in source
    assert "show_connection(parent, load_profiles(), lifecycle=lifecycle, on_connected=connected)" in source
    assert "lifecycle.register_cleanup(ssh.close)" in source
    assert "save_remote=files.write_text" in source and "slurm.sbatch" in source
    assert "send_shell_text" in source
    assert "slurm.squeue" in source and "slurm.scontrol_show_job" in source
    assert "files.read_text" in source and "cancel=slurm.scancel" in source
    assert 'command_id == "NAV-DIRECTORIES"' in source
    assert "loader=files.iterdir_entries" in source and "read_text=files.read_text" in source
    assert "operation=remote_operation" in source and "files.remove(remote_path, recursive=True)" in source
    assert "files.rename(paths[0], destination)" in source
    assert "files.copy if action == \"copy\" else files.move" in source
    assert 'command_id == "NAV-TERMINAL"' in source and "show_terminal(parent, ssh=session.get(\"ssh\"), lifecycle=lifecycle)" in source
    assert "command_items" in source and "description_label.SetLabel" in source
