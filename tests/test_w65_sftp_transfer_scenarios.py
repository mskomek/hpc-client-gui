"""W65 SFTP-014: shipped transfer paths over a real SFTP server."""
from __future__ import annotations

import functools
import os

import pytest

from hpc_gui.services.transfer_conflict_policy import (
    clear_session_conflict_action,
    get_session_conflict_action,
    set_session_conflict_action,
)
from hpc_gui.services.transfer_controller import TransferController, TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_shell_file_transfer import _run_file_view_item
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.ssh.client import SSHClientWrapper
from hpc_gui.ssh.contracts import SSHConnInfo
from sftp_harness_support import ROOT_ENV, remote_backend, serve


@pytest.fixture(autouse=True)
def _restore_session_conflict_policy():
    """Keep the process-wide conflict choice out of neighbouring tests."""
    saved = get_session_conflict_action("upload")
    try:
        yield
    finally:
        if saved is None:
            clear_session_conflict_action()
        else:
            set_session_conflict_action(saved)


def _payload(tmp_path, name, size):
    data = os.urandom(size)
    path = tmp_path / name
    path.write_bytes(data)
    return path, data


def _root(tmp_path, monkeypatch):
    root = tmp_path / "srv"
    root.mkdir()
    monkeypatch.setenv(ROOT_ENV, str(root))
    return root


def test_profile_connect_then_transfer(tmp_path, monkeypatch):
    """The real connect() path (host-key policy, auth) still transfers files."""
    _root(tmp_path, monkeypatch)
    local, data = _payload(tmp_path, "profile.bin", 4096)
    copy = tmp_path / "back.bin"
    known_hosts = tmp_path / "known_hosts"
    with serve() as port:
        wrapper = SSHClientWrapper()
        info = SSHConnInfo(
            host="127.0.0.1",
            port=port,
            username="user",
            password="secret",
            known_hosts_path=str(known_hosts),
            host_key_policy="accept-new",
            allow_agent=False,
            look_for_keys=False,
            timeout=20,
        )
        wrapper.connect(info)
        try:
            backend = SSHFilesBackend(wrapper)
            backend.upload(str(local), "/profile.bin")
            backend.download("/profile.bin", str(copy))
        finally:
            wrapper.close()

    assert copy.read_bytes() == data
    # accept-new pins the host key on first use instead of skipping the check.
    assert known_hosts.read_text(encoding="utf-8").strip()


def test_upload_download_roundtrip_through_shipped_backend(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    local, data = _payload(tmp_path, "payload.bin", 2048)
    copy = tmp_path / "copy.bin"
    with serve() as port, remote_backend(port) as backend:
        backend.upload(str(local), "/payload.bin")
        backend.download("/payload.bin", str(copy))

    assert copy.read_bytes() == data


def test_reupload_truncates_the_existing_remote_file(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    large, _ = _payload(tmp_path, "large.bin", 4096)
    small, small_data = _payload(tmp_path, "small.bin", 2048)
    copy = tmp_path / "copy.bin"
    with serve() as port, remote_backend(port) as backend:
        backend.upload(str(large), "/over.bin")
        backend.upload(str(small), "/over.bin")
        size = backend.stat("/over.bin")[0]
        backend.download("/over.bin", str(copy))

    # Without O_TRUNC the smaller upload would leave the 4096-byte tail behind.
    assert size == 2048
    assert copy.read_bytes() == small_data


def test_resume_upload_takes_the_partial_prefix_branch(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    full, data = _payload(tmp_path, "full.bin", 4096)
    partial = tmp_path / "partial.bin"
    partial.write_bytes(data[:1024])
    seen = []
    copy = tmp_path / "copy.bin"
    with serve() as port, remote_backend(port) as backend:
        backend.upload(str(partial), "/resume.bin")
        backend.resume_upload(str(full), "/resume.bin", progress_cb=lambda d, t: seen.append((d, t)))
        backend.download("/resume.bin", str(copy))

    # A silent full re-upload would start at (0, 4096) and still match bytes.
    assert seen[0] == (1024, 4096)
    assert seen[-1] == (4096, 4096)
    assert copy.read_bytes() == data


def test_multi_chunk_transfer_roundtrip(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    size = 9 * 1024 * 1024 + 1234
    local, data = _payload(tmp_path, "big.bin", size)
    up_seen = []
    down_seen = []
    copy = tmp_path / "copy.bin"
    with serve() as port, remote_backend(port) as backend:
        backend.upload(str(local), "/big.bin", progress_cb=lambda d, t: up_seen.append((d, t)))
        backend.download("/big.bin", str(copy), progress_cb=lambda d, t: down_seen.append((d, t)))

    # Progress is reported per MiB, so 9 MiB proves the chunk loop ran many
    # times rather than one oversized write.
    # Downloads read ahead, so they report few coarse updates; uploads report
    # per chunk. Both must stay monotonic and end on the full size.
    assert len(up_seen) >= 9 and down_seen
    assert [done for done, _total in up_seen] == sorted(done for done, _total in up_seen)
    assert [done for done, _total in down_seen] == sorted(done for done, _total in down_seen)
    assert up_seen[-1] == (size, size)
    assert down_seen[-1] == (size, size)
    assert {total for _done, total in up_seen} == {size}
    assert copy.read_bytes() == data


def test_cancel_interrupts_an_inflight_upload(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    first, data = _payload(tmp_path, "first.bin", 8 * 1024 * 1024)
    second, _ = _payload(tmp_path, "second.bin", 1024)
    item_first = TransferItem("upload", str(first), "/first.bin")
    item_second = TransferItem("upload", str(second), "/second.bin")
    fired = []

    def on_progress(_item, done, _total):
        if done >= 2 * 1024 * 1024 and not fired:
            fired.append(done)
            controller.cancel_all()

    partial = tmp_path / "partial.bin"
    with serve() as port, remote_backend(port) as backend:
        run_item = functools.partial(_run_file_view_item, backend)
        controller = TransferController([item_first, item_second], run_item, on_progress=on_progress)
        controller.start()
        assert controller.wait(120)
        assert [str(error) for _item, error in controller.failed] == ["cancelled"]
        assert [item.dst for item in controller.pending] == ["/second.bin"]
        assert backend.exists("/second.bin") is False
        backend.download("/first.bin", str(partial))

    partial_data = partial.read_bytes()
    assert 0 < len(partial_data) < len(data)
    assert data.startswith(partial_data)


def test_cancel_drains_a_parallel_batch(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    first, _ = _payload(tmp_path, "a.bin", 8 * 1024 * 1024)
    second, _ = _payload(tmp_path, "b.bin", 8 * 1024 * 1024)
    items = [
        TransferItem("upload", str(first), "/a.bin"),
        TransferItem("upload", str(second), "/b.bin"),
    ]
    fired = []

    def on_progress(_item, done, _total):
        if done >= 1024 * 1024 and not fired:
            fired.append(done)
            controller.cancel_all()

    with serve() as port, remote_backend(port) as backend:
        run_item = functools.partial(_run_file_view_item, backend)
        controller = TransferController(items, run_item, parallel_limit=2, on_progress=on_progress)
        controller.start()
        assert controller.wait(120)
        # Both in-flight items must reach a terminal state; neither may be
        # abandoned mid-batch with the row still showing as active.
        assert controller.pending == []
        assert len(controller.failed) + len(controller.completed) == 2
        assert fired
        assert backend.exists("/a.bin") or backend.exists("/b.bin")


def test_multi_file_conflicts_follow_the_session_policy(tmp_path, monkeypatch):
    root = _root(tmp_path, monkeypatch)
    (root / "a.txt").write_bytes(b"old-a")
    (root / "b.txt").write_bytes(b"old-b")
    new_a, data_a = _payload(tmp_path, "new-a.txt", 64)
    new_b, data_b = _payload(tmp_path, "new-b.txt", 96)
    items = [
        TransferItem("upload", str(new_a), "/a.txt"),
        TransferItem("upload", str(new_b), "/b.txt"),
    ]
    with serve() as port, remote_backend(port) as backend:
        run_item = functools.partial(_run_file_view_item, backend)

        set_session_conflict_action("skip")
        skipped = TransferSessionController(items, run_item, conflict_check=lambda _item: True)
        skipped.start()
        assert skipped.engine.wait(60)
        assert skipped.status().completed == 2
        assert (root / "a.txt").read_bytes() == b"old-a"
        assert (root / "b.txt").read_bytes() == b"old-b"

        set_session_conflict_action("overwrite")
        replaced = TransferSessionController(items, run_item, conflict_check=lambda _item: True)
        replaced.start()
        assert replaced.engine.wait(60)
        assert replaced.status().completed == 2
        assert (root / "a.txt").read_bytes() == data_a
        assert (root / "b.txt").read_bytes() == data_b
