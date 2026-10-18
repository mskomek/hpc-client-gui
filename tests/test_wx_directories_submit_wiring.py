from hpc_gui import wx_shell_files
from hpc_gui.wx_shell_events import _directories_callbacks


def test_directories_reuse_live_remote_sbatch_callback(monkeypatch):
    session_state = {"session": {"slurm": object()}}
    parent = object()
    lifecycle = object()
    def submit(path):
        return path

    def supported():
        return True
    monkeypatch.setattr(
        wx_shell_files,
        "_remote_files_callbacks",
        lambda state, owner, controller: {
            "submit_slurm": submit,
            "submit_slurm_supported": supported,
        }
        if (state, owner, controller) == (session_state, parent, lifecycle)
        else {},
    )

    callbacks = _directories_callbacks(session_state, parent, lifecycle)

    assert callbacks["session_state"] is session_state
    assert callbacks["submit"] is submit
    assert callbacks["submit_slurm"] is submit
    assert callbacks["submit_slurm_supported"] is supported
