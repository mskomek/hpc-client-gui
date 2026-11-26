"""Exercise mode-aware native queue with real local bytes and a mock backend."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_conflict_policy import conflict_target, available_rename_destination
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


def run(files, item, mode, decision=None):
    session = {"files": files}
    state = {"session": session, "ftp_transfer_type": mode}
    controller = _start_file_transfers(state, None, [item], conflict_resolver=lambda _: decision)
    assert controller.engine.wait(5)
    assert not controller.engine.failed, controller.engine.failed
    return item


@pytest.mark.parametrize("mode,expected", [("ascii", b"a\nb\n"), ("auto", b"a\nb\n"), ("binary", b"a\r\nb\r\n")])
def test_wx_upload_mode_controls_actual_bytes(tmp_path, mode, expected):
    source = tmp_path / "test.txt"
    source.write_bytes(b"a\r\nb\r\n")
    files = MockFilesBackend()
    dst = "/arf/scratch/user/new.txt"
    item = run(files, TransferItem("upload", str(source), dst), mode)
    assert files._files[dst] == expected
    assert not files.exists(dst + ".part")
    assert item.effective_mode == ("binary" if mode == "binary" else "ascii")


def test_wx_download_partial_skip_then_overwrite(tmp_path):
    files = MockFilesBackend()
    src = "/arf/scratch/user/new.bin"
    files._files[src] = b"fresh\x00data"
    dst = tmp_path / "result.bin"
    part = Path(str(dst) + ".part")
    part.write_bytes(b"stale")
    run(files, TransferItem("download", src, str(dst)), "binary", "skip")
    assert not dst.exists() and part.read_bytes() == b"stale"
    run(files, TransferItem("download", src, str(dst)), "binary", "overwrite")
    assert dst.read_bytes() == b"fresh\x00data" and not part.exists()


def test_rename_does_not_claim_an_existing_partial(tmp_path):
    dst = tmp_path / "result.bin"
    Path(str(dst) + ".part").write_bytes(b"x")
    (tmp_path / "result (1).bin.part").write_bytes(b"x")
    assert conflict_target(None, "download", str(dst), include_partial=True) == str(dst) + ".part"
    assert available_rename_destination(None, "download", str(dst), include_partial=True) == str(tmp_path / "result (2).bin")


def test_transfer_backend_value_error_is_not_replayed(tmp_path):
    from hpc_gui.services.transfer_mode import upload_with_mode

    source = tmp_path / "file.bin"
    source.write_bytes(b"x")
    calls = []
    def upload(src, dst, progress_cb=None):
        calls.append(dst)
        raise ValueError("backend error after write")
    files = SimpleNamespace(upload=upload)
    with pytest.raises(ValueError, match="after write"):
        upload_with_mode(files, str(source), "/target", "binary")
    assert calls == ["/target"]
