import pytest

from hpc_gui.wx_directories import WxDirectoriesWorkspace


@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
def test_dynamic_storage_and_directory_workflows():
    opened, submitted, shell = [], [], []
    workspace = WxDirectoriesWorkspace(
        ({"id": "fast", "label": "Fast", "path": "/scratch/user"}, {"id": "archive", "path": "/archive/user"}),
        open_editor=opened.append,
        submit=lambda path, job_id: submitted.append((path, job_id)),
        run_shell=shell.append,
    )
    assert [pane.id for pane in workspace.storages] == ["fast", "archive"]
    assert workspace.storage("fast").path == "/scratch/user"
    assert workspace.double_click("/scratch/user/job.slurm") == "view_edit"
    workspace.submit_item("/scratch/user/job.slurm", "123")
    workspace.run_shell("/scratch/user/run.sh")
    assert opened == ["/scratch/user/job.slurm"] and submitted == [("/scratch/user/job.slurm", "123")] and shell
    assert workspace.double_click("/scratch/user", is_dir=True) == "navigate"


@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
def test_batch_submit_is_deterministic_and_model_has_no_qt():
    workspace = WxDirectoriesWorkspace(({"id": "x", "path": "/x"},))
    assert workspace.batch_submit(("/x/b.slurm", "/x/a.slurm"))[1].index == 2
    source = open("src/hpc_gui/wx_directories.py", encoding="utf-8").read()
    assert "PySide6" not in source and "wx" in source


@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
def test_w24_new_slurm_target_resolves_from_current_session_at_click_time():
    """REQ HPC-W06-TODO-DIR-SESSION-002 / DIR-004: click-time scratch resolve."""
    from hpc_gui.wx_directories_view import _resolve_new_slurm_target

    def _session(scratch):
        return {
            "session": {
                "profile": {"username": "hpctest"},
                "cfg": {
                    "username": "hpctest",
                    "system_settings": {"scratch_dir": scratch, "home_dir": "/home/hpctest"},
                },
            }
        }

    first = _resolve_new_slurm_target(_session("/scratch/aaa"), "new_job.slurm")
    second = _resolve_new_slurm_target(_session("/scratch/bbb"), "new_job.slurm")
    assert first == "/scratch/aaa/new_job.slurm"
    assert second == "/scratch/bbb/new_job.slurm"
    # Negative: stale build-time capture must not leak into the second resolve.
    assert second != first


@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
def test_w24_directories_backend_rebind_prefers_live_session_files():
    """REQ HPC-W06-DIR-008 / SESSION-REBIND-002: live backend wins over snapshot."""
    from hpc_gui.wx_directories_view import _resolve_live_files

    old_backend, new_backend = object(), object()
    session_state = {"session": {"files": old_backend}}
    assert _resolve_live_files(session_state, old_backend) is old_backend
    # Profile/provider switch replaces the live backend object.
    session_state["session"]["files"] = new_backend
    assert _resolve_live_files(session_state, old_backend) is new_backend
    # Negative: disconnect (live backend gone) falls back to snapshot/None safely.
    session_state["session"]["files"] = None
    assert _resolve_live_files(session_state, old_backend) is old_backend
    assert _resolve_live_files({"session": {}}, None) is None


@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
def test_w24_double_click_targets_selected_storage_area():
    """REQ HPC-W06-DIR-005: directory navigation targets the selected pane."""
    workspace = WxDirectoriesWorkspace(
        ({"id": "scratch", "path": "/scratch/u"}, {"id": "home", "path": "/home/u"}),
    )
    assert workspace.double_click("/home/u/sub", is_dir=True, storage_id="home") == "navigate"
    assert workspace.remote["home"].current_path == "/home/u/sub"
    # The unselected pane must not move.
    assert workspace.remote["scratch"].current_path == "/scratch/u"
    # Negative: compat path without storage_id keeps first-pane behavior.
    assert workspace.double_click("/scratch/u/other", is_dir=True) == "navigate"
    assert workspace.remote["scratch"].current_path == "/scratch/u/other"


@pytest.mark.unit
@pytest.mark.wx
@pytest.mark.semantic
def test_w24_directories_rebind_and_disconnect_helpers():
    """REQ DIR-SESSION-001 / SESSION-DISCONNECT-001 / DIR-009 / TODO-020."""
    from hpc_gui.wx_directories_view import (
        mark_directories_disconnected,
        rebind_directories_storage,
    )

    class _Label:
        def __init__(self, text=""):
            self.text = text

        def SetLabel(self, value):
            self.text = value

    class _Model:
        def __init__(self, path):
            self.current_path = path
            self.invalidated = 0
            self.history = ["/old/provider-a-path"]

        def invalidate(self):
            self.invalidated += 1

        def navigate(self, path):
            self.current_path = path

    class _Host:
        pass

    host = _Host()
    host._wx_dirs_models = {"scratch": _Model("/old/scratch"), "home": _Model("/old/home")}
    host._wx_dirs_controls = {"scratch_label": _Label(), "home_label": _Label()}
    session_state = {
        "session": {
            "profile": {"username": "hpctest"},
            "cfg": {
                "username": "hpctest",
                "system_settings": {"scratch_dir": "/scratch/new", "home_dir": "/home/new"},
            },
        }
    }
    resolved = rebind_directories_storage(host, session_state)
    assert resolved == {"scratch": "/scratch/new", "home": "/home/new"}
    assert host._wx_dirs_models["scratch"].current_path == "/scratch/new"
    assert host._wx_dirs_models["home"].current_path == "/home/new"
    assert host._wx_dirs_controls["scratch_label"].text == "Scratch — /scratch/new"
    assert host._wx_dirs_controls["home_label"].text == "Home — /home/new"
    # Stale provider-A history must not survive the rebind.
    assert host._wx_dirs_models["scratch"].history == []
    # Negative: disconnect must not keep stale paths as valid.
    mark_directories_disconnected(host)
    assert host._wx_dirs_controls["scratch_label"].text == "Scratch — disconnected"
    assert host._wx_dirs_controls["home_label"].text == "Home — disconnected"
