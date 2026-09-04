from pathlib import Path
import threading

import pytest

wx = pytest.importorskip("wx")


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
    assert '"open_editor_new_window": lambda path: open_local(path, True)' in source
    assert "Path(path).read_text" in source and "manager.open_primary" in source
    assert '"upload": upload_local' in source and "_start_file_transfers" in source
    assert "_editor_action_factory" in source and "current.is_local" in source
    assert 'command_id == "NAV-EDITOR"' in source
    assert 'command_id == "NAV-JOBS"' in source
    assert "show_jobs(" in source and "lifecycle=lifecycle" in source and '"list_jobs": list_jobs' in source
    assert "show_connection(parent, **_conn)" in source
    assert "lifecycle.register_cleanup(ssh.close)" in source
    assert "def save_remote(path, content)" in source and "files.write_text(path, content)" in source
    assert "send_shell_text" in source
    assert "slurm.squeue" in source and "slurm.scontrol_show_job" in source
    assert "files.read_text" in source and "return slurm.scancel(job_id)" in source
    assert 'command_id == "NAV-DIRECTORIES"' in source
    assert "loader=files.iterdir_entries" in source and '"read_text": read_text' in source
    assert '"operation": remote_operation' in source and "files.remove(remote_path, recursive=True)" in source
    assert "files.rename(paths[0], destination)" in source
    assert "files.copy if action == \"copy\" else files.move" in source
    assert "TransferItem(\"download\", remote_path" in source and "_start_file_transfers" in source
    assert 'TransferItem("upload", local_path' in source and "_start_file_transfers" in source
    assert "files.mkdir(destination)" in source
    assert 'command_id == "NAV-TERMINAL"' in source and "show_terminal(parent, ssh=session.get(\"ssh\"), lifecycle=lifecycle)" in source
    assert "command_items" in source and "description_label.SetLabel" in source
    assert "lifecycle.register_cleanup(destroy_tray)" in source and "def destroy_tray" in source


def test_wx_shell_remote_operation_keeps_session_snapshot(monkeypatch):
    from hpc_gui.wx_shell import _dispatch
    import hpc_gui.wx_remote_files_view as remote_view

    class Files:
        def __init__(self, name):
            self.name = name
            self.calls = []
            self.started = threading.Event()
            self.release = threading.Event()

        def iterdir_entries(self, _path):
            return ()

        def read_text(self, _path):
            return ""

        def move(self, source, destination):
            self.calls.append((self.name, source, destination))
            self.started.set()
            self.release.wait(2)

    class Slurm:
        pass

    class Lifecycle:
        def register_cleanup(self, _callback):
            pass

    first, second = Files("A"), Files("B")
    state = {"session": {"files": first, "slurm": Slurm()}}
    captured = []
    monkeypatch.setattr(remote_view, "show_remote_files", lambda *args, **kwargs: captured.append(kwargs))
    _dispatch("NAV-DIRECTORIES", None, Lifecycle(), state)
    operation = captured[-1]["operation"]
    worker = threading.Thread(target=operation, args=("move", ("/a",), "/b"))
    worker.start()
    assert first.started.wait(2)
    state["session"] = {"files": second, "slurm": Slurm()}
    first.release.set()
    worker.join(2)
    assert first.calls == [("A", "/a", "/b/a")]
    assert second.calls == []
