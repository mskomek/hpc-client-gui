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



@pytest.mark.parametrize("direction", ["upload", "download"])
def test_ascii_checksum_verifies_wire_bytes(tmp_path, monkeypatch, direction):
    import hashlib
    import os
    from hpc_gui.config.storage import set_transfer_checksum_verification_enabled
    from hpc_gui.services.transfer_integrity import VerificationState

    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path / "config"))
    set_transfer_checksum_verification_enabled(True)

    class HashFiles(MockFilesBackend):
        def sha256(self, path):
            return hashlib.sha256(self._files[path]).hexdigest()

    files = HashFiles()
    remote = "/arf/scratch/user/test.txt"
    local = tmp_path / "test.txt"
    if direction == "upload":
        local.write_bytes(b"a\r\nb\r\n")
        item = TransferItem("upload", str(local), remote)
    else:
        files._files[remote] = b"a\r\nb\n"
        item = TransferItem("download", remote, str(local))
    run(files, item, "ascii")
    assert item.verification_state == VerificationState.VERIFIED
    if direction == "upload":
        assert files._files[remote] == b"a\nb\n"
    else:
        assert local.read_bytes() == ("a" + os.linesep + "b" + os.linesep).encode()


def test_checksum_mismatch_does_not_publish_download(tmp_path, monkeypatch):
    from hpc_gui.config.storage import set_transfer_checksum_verification_enabled

    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path / "config"))
    set_transfer_checksum_verification_enabled(True)

    class CorruptHash(MockFilesBackend):
        def sha256(self, path):
            return "0" * 64

    files = CorruptHash()
    remote = "/arf/scratch/user/file.bin"
    files._files[remote] = b"new"
    local = tmp_path / "file.bin"
    local.write_bytes(b"old")
    controller = _start_file_transfers(
        {"session": {"files": files}, "ftp_transfer_type": "binary"},
        None, [TransferItem("download", remote, str(local))],
        conflict_resolver=lambda _: "overwrite",
    )
    assert controller.engine.wait(5)
    assert "SHA-256 verification failed" in controller.engine.failed[0][1]
    assert local.read_bytes() == b"old"
    assert Path(str(local) + ".part").read_bytes() == b"new"



class MemoryResumeStore:
    def __init__(self):
        self.records = {}

    def get(self, key):
        return self.records.get(key)

    def save(self, key, identity, partial_path, partial_bytes):
        self.records[key] = {"identity": dict(identity), "partial_path": partial_path,
                             "partial_bytes": partial_bytes}

    def remove(self, key):
        self.records.pop(key, None)


def test_matching_download_partial_resumes_and_stale_partial_stays(tmp_path, monkeypatch):
    from hpc_gui.services import transfer_mode
    from hpc_gui.services.transfer_resume_store import transfer_record_key

    store = MemoryResumeStore()
    monkeypatch.setattr(transfer_mode, "transfer_resume_store_for_backend", lambda _: store)

    class ResumingFiles(MockFilesBackend):
        def __init__(self):
            super().__init__()
            self.offsets = []

        def resume_download(self, remote, local, progress_cb=None):
            existing = Path(local).read_bytes()
            self.offsets.append(len(existing))
            Path(local).write_bytes(existing + self._files[remote][len(existing):])

    files = ResumingFiles()
    remote = "/arf/scratch/user/new.bin"
    files._files[remote] = b"abcdef"
    local = tmp_path / "result.bin"
    part = Path(str(local) + ".part")
    part.write_bytes(b"abc")
    item = TransferItem("download", remote, str(local))
    controller = _start_file_transfers(
        {"session": {"files": files}, "ftp_transfer_type": "binary"}, None, [item],
        conflict_resolver=lambda _: "resume",
    )
    assert controller.engine.wait(5)
    assert "partial identity does not match" in controller.engine.failed[0][1]
    assert part.read_bytes() == b"abc" and not local.exists() and not files.offsets
    size, mtime = files.stat(remote)
    key = transfer_record_key("download", str(local))
    store.save(key, {
        "direction": "download", "remote_path": remote,
        "local_path": str(local.resolve()), "size": size, "mtime": mtime,
        "mode": "binary",
    }, str(part.resolve()), 3)
    run(files, TransferItem("download", remote, str(local)), "binary", "resume")
    assert files.offsets == [3] and local.read_bytes() == b"abcdef"
    assert not part.exists() and not store.records


def test_legacy_sidecar_is_not_deleted_by_native_queue(tmp_path):
    files = MockFilesBackend()
    remote = "/arf/scratch/user/new.bin"
    files._files[remote] = b"payload"
    local = tmp_path / "result.bin"
    sidecar = Path(str(local) + ".part.meta")
    sidecar.write_bytes(b"unrelated")
    run(files, TransferItem("download", remote, str(local)), "binary")
    assert sidecar.read_bytes() == b"unrelated"


def test_staging_alias_is_rejected_before_any_worker(tmp_path):
    files = MockFilesBackend()
    with pytest.raises(ValueError, match="Overlapping|overlaps"):
        _start_file_transfers(
            {"session": {"files": files}, "ftp_transfer_type": "binary"}, None,
            [TransferItem("download", "/a", str(tmp_path / "a")),
             TransferItem("download", "/b", str(tmp_path / "a.part"))],
        )
    assert not list(tmp_path.iterdir())


def test_active_transfer_reservation_rejects_cross_queue_alias(tmp_path):
    from hpc_gui.services.transfer_mode_execution import reserve_transfer_paths

    owner = object()
    one = TransferItem("download", "/a", str(tmp_path / "a"))
    two = TransferItem("download", "/b", str(tmp_path / "a.part"))
    with reserve_transfer_paths(owner, one):
        with pytest.raises(RuntimeError, match="Another transfer owns"):
            with reserve_transfer_paths(object(), two):
                pytest.fail("overlapping reservation accepted")
    with reserve_transfer_paths(owner, two):
        pass
