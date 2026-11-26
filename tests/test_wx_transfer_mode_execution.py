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


@pytest.mark.parametrize("mode", ["binary", "ascii"])
@pytest.mark.parametrize("outcome", ["success", "verify_failure", "cancel", "unsupported"])
def test_ssh_overwrite_stages_before_atomic_publish(tmp_path, monkeypatch, mode, outcome):
    from hpc_gui.services.transfer_controller import TransferCancelled
    from hpc_gui.services.transfer_mode_execution import execute_with_mode
    from test_transfer_resume_semantics import ssh_backend

    source = tmp_path / "source.txt"
    source.write_bytes(b"a\r\nb\r\n")
    destination = "/remote/existing.txt"
    files, sftp = ssh_backend({destination: b"original", destination + ".part": b"unrelated"})
    events = []
    expected = b"a\nb\n" if mode == "ascii" else source.read_bytes()

    def remove(path):
        events.append(("remove", path))
        del sftp.store[path]

    def publish(path, target):
        assert target == destination
        assert bytes(sftp.store[target]) == b"original"
        assert bytes(sftp.store[path]) == expected
        events.append(("publish", path))
        if outcome == "unsupported":
            raise OSError("POSIX rename unsupported")
        sftp.store[target] = sftp.store.pop(path)

    monkeypatch.setattr(sftp, "remove", remove, raising=False)
    monkeypatch.setattr(sftp, "posix_rename", publish, raising=False)

    def verify(local, remote):
        assert remote != destination
        assert bytes(sftp.store[destination]) == b"original"
        assert Path(local).read_bytes() == bytes(sftp.store[remote]) == expected
        events.append(("verify", remote))
        if outcome == "verify_failure":
            raise RuntimeError("checksum mismatch")

    def progress(done, total):
        assert bytes(sftp.store[destination]) == b"original"
        if outcome == "cancel":
            raise TransferCancelled()

    def execute():
        return execute_with_mode(
            files, TransferItem("upload", str(source), destination), progress,
            mode, "overwrite", lambda *a, **k: pytest.fail("raw overwrite invoked"),
            verify_bytes=verify,
        )

    if outcome == "success":
        assert execute() == mode
        assert bytes(sftp.store[destination]) == expected
        assert [event for event, _ in events] == ["verify", "publish"]
    else:
        error = {"verify_failure": RuntimeError, "cancel": TransferCancelled, "unsupported": OSError}[outcome]
        with pytest.raises(error):
            execute()
        assert bytes(sftp.store[destination]) == b"original"
        assert events[-1][0] == "remove"
    assert bytes(sftp.store[destination + ".part"]) == b"unrelated"
    assert set(sftp.store) == {destination, destination + ".part"}
    assert sftp.modes(destination) == []
    opens = [(path, flags) for kind, path, flags in sftp.events if kind == "open"]
    assert len(opens) == 1 and opens[0][0].startswith("/remote/.hpc-upload-")
    assert opens[0][1] == "wx"


@pytest.mark.parametrize("mode", ["binary", "ascii"])
def test_renamed_download_never_overwrites_file_created_during_transfer(tmp_path, mode):
    from hpc_gui.services.transfer_mode_execution import execute_with_mode

    target = tmp_path / "new.txt"
    remote = "/remote/source.txt"

    class RacingFiles(MockFilesBackend):
        def download(self, src, dst, progress_cb=None):
            super().download(src, dst, progress_cb=progress_cb)
            target.write_bytes(b"new owner")

    files = RacingFiles()
    files._files[remote] = b"a\r\nb\r\n"
    item = TransferItem("download", remote, str(target))
    with pytest.raises(FileExistsError):
        execute_with_mode(files, item, lambda *_: None, mode, "rename", None)
    assert target.read_bytes() == b"new owner"
    assert Path(str(target) + ".part").read_bytes() == b"a\r\nb\r\n"


@pytest.mark.parametrize("direction", ["upload", "download"])
@pytest.mark.parametrize("partial", [False, True])
def test_rename_rechecks_existing_target_and_partial(tmp_path, direction, partial):
    from hpc_gui.services.transfer_mode_execution import execute_with_mode

    files = MockFilesBackend()
    local = tmp_path / "source.bin"
    remote = "/remote/source.bin"
    destination = (str(tmp_path / "new.bin") if direction == "download" else "/remote/new.bin")
    occupied = destination + (".part" if partial else "")
    if direction == "download":
        files._files[remote] = b"payload"
        Path(occupied).write_bytes(b"original")
        item = TransferItem(direction, remote, destination)
    else:
        local.write_bytes(b"payload")
        files._files[occupied] = b"original"
        item = TransferItem(direction, str(local), destination)
    with pytest.raises(FileExistsError):
        execute_with_mode(files, item, lambda *_: None, "binary", "rename", None)
    assert (Path(occupied).read_bytes() if direction == "download" else files._files[occupied]) == b"original"
