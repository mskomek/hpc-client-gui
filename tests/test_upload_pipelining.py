"""Pipelining expectations for every SSHFilesBackend upload mode.

The recording fake captures exactly what the backend does to the remote file
object: which mode it opened, whether it asked Paramiko for write pipelining,
how many bytes it wrote, and whether the isolated transfer channel was closed
afterwards. These tests pin the pre-existing resume/atomic behaviour and the
deliberate overwrite-pipelining decision from Wave 60.

Runs against in-memory fakes only; no socket, no cluster.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402


class _RecordingSftpFile:
    def __init__(self, recorder: "_RecordingChannel", mode: str) -> None:
        self._recorder = recorder
        self.mode = mode
        self.pipelined_calls: list[bool] = []
        self.write_calls = 0
        self.data = bytearray()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def set_pipelined(self, value: bool) -> None:
        self.pipelined_calls.append(value)

    def write(self, data: bytes) -> None:
        self.write_calls += 1
        self.data.extend(data)

    def close(self) -> None:
        self.closed = True


class _RecordingChannel:
    def __init__(self, files: dict[str, bytearray] | None = None) -> None:
        self.files = files if files is not None else {}
        self.opened_modes: list[str] = []
        self.opened_files: list[_RecordingSftpFile] = []
        self.renames: list[tuple[str, str]] = []
        self.closed = False

    def stat(self, path: str):
        data = self.files.get(path)
        return SimpleNamespace(st_size=len(data) if data is not None else 0)

    def exists(self, _path: str) -> bool:
        raise AssertionError("exists() is not part of the upload flow")

    def open(self, path: str, mode: str) -> _RecordingSftpFile:
        self.opened_modes.append(mode)
        handle = _RecordingSftpFile(self, mode)
        if mode.startswith("a"):
            handle.data.extend(self.files.get(path, b""))
        self.opened_files.append(handle)
        return handle

    def rename(self, src: str, dst: str) -> None:
        self.renames.append((src, dst))

    def close(self) -> None:
        self.closed = True


def _backend_with(channel: _RecordingChannel) -> SSHFilesBackend:
    ssh = SimpleNamespace(sftp=object(), open_transfer_sftp=lambda: channel)
    return SSHFilesBackend(ssh)


class OverwriteUploadTests(unittest.TestCase):
    def test_overwrite_upload_enables_pipelining_once(self) -> None:
        channel = _RecordingChannel(
            files={"/remote/out.bin": b"stale-data-longer-than-the-new-payload"}
        )
        backend = _backend_with(channel)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "new.bin"
            source.write_bytes(b"hello-pipelined-world")
            progress: list[tuple[int, int]] = []

            backend.upload(
                str(source),
                "/remote/out.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(channel.opened_modes, ["wb"])
        handle = channel.opened_files[0]
        self.assertEqual(handle.pipelined_calls, [True])
        self.assertEqual(bytes(handle.data), b"hello-pipelined-world")
        self.assertEqual(progress[-1], (len(b"hello-pipelined-world"), len(b"hello-pipelined-world")))
        self.assertTrue(handle.closed)
        self.assertTrue(channel.closed)


class ResumeUploadTests(unittest.TestCase):
    def test_resume_upload_keeps_pipelining_and_appends_from_remote_size(self) -> None:
        channel = _RecordingChannel(files={"/remote/resume.bin": b"abc"})
        backend = _backend_with(channel)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "resume.bin"
            source.write_bytes(b"abcdefgh")
            progress: list[tuple[int, int]] = []

            backend.resume_upload(
                str(source),
                "/remote/resume.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(channel.opened_modes, ["ab"])
        handle = channel.opened_files[0]
        self.assertEqual(handle.pipelined_calls, [True])
        self.assertEqual(bytes(handle.data), b"abcdefgh")
        self.assertEqual(progress, [(3, 8), (8, 8)])
        self.assertTrue(channel.closed)

    def test_equal_sizes_are_a_reported_no_op(self) -> None:
        channel = _RecordingChannel(files={"/remote/same.bin": b"1234"})
        backend = _backend_with(channel)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "same.bin"
            source.write_bytes(b"1234")
            progress: list[tuple[int, int]] = []

            backend.resume_upload(
                str(source),
                "/remote/same.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(channel.opened_modes, [])
        self.assertEqual(progress, [(4, 4)])
        self.assertTrue(channel.closed)

    def test_remote_larger_falls_back_to_overwrite(self) -> None:
        channel = _RecordingChannel(files={"/remote/big.bin": b"0123456789"})
        backend = _backend_with(channel)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "small.bin"
            source.write_bytes(b"xy")

            backend.upload(str(source), "/remote/big.bin")

        self.assertEqual(channel.opened_modes, ["wb"])
        self.assertEqual(bytes(channel.opened_files[0].data), b"xy")
        self.assertTrue(channel.closed)

    def test_zero_byte_file_uploads_without_writes(self) -> None:
        channel = _RecordingChannel()
        backend = _backend_with(channel)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "empty.bin"
            source.write_bytes(b"")

            backend.upload(str(source), "/remote/empty.bin")

        self.assertEqual(channel.opened_modes, ["wb"])
        handle = channel.opened_files[0]
        self.assertEqual(handle.write_calls, 0)
        self.assertEqual(handle.pipelined_calls, [True])
        self.assertTrue(channel.closed)


class AtomicUploadTests(unittest.TestCase):
    def test_upload_and_rename_pipelines_the_temporary_target(self) -> None:
        channel = _RecordingChannel()
        backend = _backend_with(channel)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "atomic.bin"
            source.write_bytes(b"atomic-bytes")
            progress: list[tuple[int, int]] = []

            backend.upload_and_rename(
                str(source),
                "/remote/.atomic.bin.part",
                "/remote/atomic.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(channel.opened_modes, ["wb"])
        handle = channel.opened_files[0]
        self.assertEqual(handle.pipelined_calls, [True])
        self.assertEqual(bytes(handle.data), b"atomic-bytes")
        self.assertEqual(channel.renames, [("/remote/.atomic.bin.part", "/remote/atomic.bin")])
        self.assertEqual(progress[-1], (12, 12))
        self.assertTrue(channel.closed)

    def test_progress_reaches_exact_total_on_atomic_path(self) -> None:
        channel = _RecordingChannel()
        backend = _backend_with(channel)
        payload = os.urandom(3 * 1024 * 1024 + 17)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "chunky.bin"
            source.write_bytes(payload)
            progress: list[tuple[int, int]] = []

            backend.upload_and_rename(
                str(source),
                "/remote/.chunky.bin.part",
                "/remote/chunky.bin",
                progress_cb=lambda done, total: progress.append((done, total)),
            )

        self.assertEqual(progress[-1], (len(payload), len(payload)))
        self.assertEqual(bytes(channel.opened_files[0].data), payload)


if __name__ == "__main__":
    unittest.main()
