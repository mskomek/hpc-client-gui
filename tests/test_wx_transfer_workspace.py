from pathlib import Path

from hpc_gui.wx_transfer_workspace import WxTransferWorkspace


def test_transfer_workspace_double_click_clipboard_dnd_and_storage(tmp_path: Path):
    workspace = WxTransferWorkspace(tmp_path)
    upload = workspace.double_click_local(tmp_path / "a.txt", "/remote")
    download = workspace.double_click_remote("/remote/b.txt", tmp_path)
    assert upload.op == "upload" and download.op == "download"
    assert workspace.cross_pane_clipboard(["/remote/b.txt"], str(tmp_path)).op == "download"
    assert workspace.drag_operation(["/remote/b.txt"], str(tmp_path), copy=True).op == "download"
    workspace.set_storage("scratch", True)
    workspace.set_conflict("resume")
    workspace.set_checksum(True)
    assert workspace.storage.available and workspace.conflict_policy == "resume"


def test_transfer_workspace_unknown_storage_is_fail_soft():
    workspace = WxTransferWorkspace(".")
    assert not workspace.storage.available and workspace.storage.name == "unknown"
