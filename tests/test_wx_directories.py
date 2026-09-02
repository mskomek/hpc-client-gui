from hpc_gui.wx_directories import WxDirectoriesWorkspace


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


def test_batch_submit_is_deterministic_and_model_has_no_qt():
    workspace = WxDirectoriesWorkspace(({"id": "x", "path": "/x"},))
    assert workspace.batch_submit(("/x/b.slurm", "/x/a.slurm"))[1].index == 2
    source = open("src/hpc_gui/wx_directories.py", encoding="utf-8").read()
    assert "PySide6" not in source and "wx" in source
