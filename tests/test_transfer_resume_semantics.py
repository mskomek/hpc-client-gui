"""Byte/protocol level proof that Overwrite and Resume differ.

The GUI conflict dialog routes ``overwrite`` to ``upload``/``download`` and
``resume`` to ``resume_upload``/``resume_download``.  These tests assert the
observable protocol behaviour of both FTP and SFTP backends rather than the
method names, so an accidental return to implicit auto-resume fails here.
"""

from __future__ import annotations

import os

import pytest

from hpc_gui.services.files_base import RESUME_DEST_LARGER
from hpc_gui.services.files_ftp import FTPFilesBackend
from hpc_gui.services.files_ssh import SSHFilesBackend

REMOTE_DIR = "/remote"
REMOTE_FILE = "/remote/dst.bin"
SOURCE = b"ABCDEF"
PARTIAL = b"XYZ"


class FakeFTP:
    """Minimal ftplib.FTP stand-in that records transfer verbs and offsets."""

    def __init__(self, files=None):
        self.files = dict(files or {})
        self.dirs = {"/", REMOTE_DIR}
        self.transfer_commands = []
        self.rest_offsets = []
        self._cwd = "/"

    def voidcmd(self, command):
        return "200 ok"

    def pwd(self):
        return self._cwd

    def cwd(self, path):
        if path not in self.dirs:
            raise OSError(f"550 {path}: not a directory")
        self._cwd = path

    def size(self, path):
        if path not in self.files:
            raise OSError(f"550 {path}: no such file")
        return len(self.files[path])

    def sendcmd(self, command):
        raise OSError(f"500 unsupported: {command}")

    def retrbinary(self, command, callback, blocksize=8192, rest=None):
        verb, path = command.split(" ", 1)
        self.transfer_commands.append(verb)
        self.rest_offsets.append(rest)
        data = self.files[path][(rest or 0):]
        for start in range(0, len(data), 2):
            callback(data[start:start + 2])

    def storbinary(self, command, handle, blocksize=8192, callback=None):
        verb, path = command.split(" ", 1)
        self.transfer_commands.append(verb)
        payload = handle.read()
        if verb == "APPE":
            self.files[path] = self.files.get(path, b"") + payload
        else:
            self.files[path] = payload
        if callback is not None:
            callback(payload)


class FakeSFTPFile:
    def __init__(self, store, path, mode, events):
        self._store = store
        self._path = path
        self._mode = mode
        self._events = events
        if "w" in mode:
            store[path] = bytearray()
            self._pos = 0
        elif "a" in mode:
            self._pos = len(store.setdefault(path, bytearray()))
        else:
            self._pos = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def seek(self, offset, whence=0):
        assert whence == 0
        self._events.append(("seek", self._path, offset))
        self._pos = offset

    def read(self, size=-1):
        data = bytes(self._store.get(self._path, b""))
        chunk = data[self._pos:] if size is None or size < 0 else data[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk

    def write(self, chunk):
        buffer = self._store.setdefault(self._path, bytearray())
        if "a" in self._mode:
            buffer.extend(chunk)
            self._pos = len(buffer)
            return
        if len(buffer) < self._pos:
            buffer.extend(b"\0" * (self._pos - len(buffer)))
        buffer[self._pos:self._pos + len(chunk)] = chunk
        self._pos += len(chunk)

    def close(self):
        return None


class FakeSFTP:
    def __init__(self, files=None):
        self.store = {path: bytearray(data) for path, data in (files or {}).items()}
        self.events = []

    def stat(self, path):
        if path not in self.store:
            raise FileNotFoundError(path)
        return type("Attr", (), {"st_size": len(self.store[path])})()

    def open(self, path, mode):
        self.events.append(("open", path, mode))
        return FakeSFTPFile(self.store, path, mode, self.events)

    def close(self):
        return None

    def seeks(self, path):
        return [offset for kind, target, offset in self.events if kind == "seek" and target == path]

    def modes(self, path):
        return [mode for kind, target, mode in self.events if kind == "open" and target == path]


def ftp_backend(files=None):
    backend = FTPFilesBackend.__new__(FTPFilesBackend)
    backend.ftp = FakeFTP(files)
    return backend


def ssh_backend(files=None):
    backend = SSHFilesBackend.__new__(SSHFilesBackend)
    sftp = FakeSFTP(files)
    backend.ssh = type(
        "Ssh",
        (),
        {"open_transfer_sftp": staticmethod(lambda: sftp), "sftp": sftp},
    )()
    return backend, sftp


def write_local(tmp_path, data, name="src.bin"):
    target = tmp_path / name
    target.write_bytes(data)
    return str(target)


def recorder():
    seen = []
    return seen, lambda done, total: seen.append((done, total))


# --------------------------------------------------------------------------
# FTP upload
# --------------------------------------------------------------------------

def test_ftp_upload_overwrite_uses_stor_from_zero(tmp_path):
    backend = ftp_backend({REMOTE_FILE: PARTIAL})
    backend.upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert backend.ftp.transfer_commands == ["STOR"]
    assert bytes(backend.ftp.files[REMOTE_FILE]) == SOURCE


def test_ftp_upload_resume_uses_appe_from_remote_size(tmp_path):
    backend = ftp_backend({REMOTE_FILE: PARTIAL})
    backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert backend.ftp.transfer_commands == ["APPE"]
    # Only the bytes past the existing remote size were sent.
    assert bytes(backend.ftp.files[REMOTE_FILE]) == PARTIAL + SOURCE[len(PARTIAL):]


def test_ftp_upload_overwrite_replaces_equal_sized_remote(tmp_path):
    backend = ftp_backend({REMOTE_FILE: b"ZZZZZZ"})
    backend.upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert backend.ftp.transfer_commands == ["STOR"]
    assert bytes(backend.ftp.files[REMOTE_FILE]) == SOURCE


def test_ftp_upload_resume_equal_size_is_completed_noop(tmp_path):
    backend = ftp_backend({REMOTE_FILE: b"ZZZZZZ"})
    progress, callback = recorder()
    backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE, callback)
    assert backend.ftp.transfer_commands == []
    assert progress == [(len(SOURCE), len(SOURCE))]
    assert bytes(backend.ftp.files[REMOTE_FILE]) == b"ZZZZZZ"


def test_ftp_upload_resume_zero_length_remote_transfers_everything(tmp_path):
    backend = ftp_backend({REMOTE_FILE: b""})
    backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert backend.ftp.transfer_commands == ["STOR"]
    assert bytes(backend.ftp.files[REMOTE_FILE]) == SOURCE


def test_ftp_resume_upload_rejects_remote_larger_than_local(tmp_path):
    backend = ftp_backend({REMOTE_FILE: SOURCE + b"EXTRA"})
    with pytest.raises(ValueError) as excinfo:
        backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert str(excinfo.value) == RESUME_DEST_LARGER.format(path=REMOTE_FILE)
    assert backend.ftp.transfer_commands == []
    assert bytes(backend.ftp.files[REMOTE_FILE]) == SOURCE + b"EXTRA"


# --------------------------------------------------------------------------
# FTP download
# --------------------------------------------------------------------------

def test_ftp_download_overwrite_uses_retr_without_rest_and_wb(tmp_path):
    backend = ftp_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, PARTIAL, "dst.bin")
    backend.download(REMOTE_FILE, local)
    assert backend.ftp.transfer_commands == ["RETR"]
    assert backend.ftp.rest_offsets == [None]
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


def test_ftp_download_resume_uses_rest_and_append(tmp_path):
    backend = ftp_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, PARTIAL, "dst.bin")
    backend.resume_download(REMOTE_FILE, local)
    assert backend.ftp.transfer_commands == ["RETR"]
    assert backend.ftp.rest_offsets == [len(PARTIAL)]
    # Append semantics keep the existing local prefix; overwrite would not.
    with open(local, "rb") as handle:
        assert handle.read() == PARTIAL + SOURCE[len(PARTIAL):]


def test_ftp_download_overwrite_replaces_equal_sized_local(tmp_path):
    backend = ftp_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, b"ZZZZZZ", "dst.bin")
    backend.download(REMOTE_FILE, local)
    assert backend.ftp.transfer_commands == ["RETR"]
    assert backend.ftp.rest_offsets == [None]
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


def test_ftp_download_resume_equal_size_is_completed_noop(tmp_path):
    backend = ftp_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, b"ZZZZZZ", "dst.bin")
    progress, callback = recorder()
    backend.resume_download(REMOTE_FILE, local, callback)
    assert backend.ftp.transfer_commands == []
    assert progress == [(len(SOURCE), len(SOURCE))]
    with open(local, "rb") as handle:
        assert handle.read() == b"ZZZZZZ"


def test_ftp_download_resume_zero_length_local_transfers_everything(tmp_path):
    backend = ftp_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, b"", "dst.bin")
    backend.resume_download(REMOTE_FILE, local)
    assert backend.ftp.rest_offsets == [None]
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


def test_ftp_resume_download_rejects_local_larger_than_remote(tmp_path):
    backend = ftp_backend({REMOTE_FILE: PARTIAL})
    local = write_local(tmp_path, SOURCE, "dst.bin")
    with pytest.raises(ValueError) as excinfo:
        backend.resume_download(REMOTE_FILE, local)
    assert str(excinfo.value) == RESUME_DEST_LARGER.format(path=local)
    assert backend.ftp.transfer_commands == []
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


# --------------------------------------------------------------------------
# SFTP upload
# --------------------------------------------------------------------------

def test_ssh_upload_overwrite_truncates_and_writes_from_zero(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: PARTIAL})
    backend.upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert sftp.modes(REMOTE_FILE) == ["wb"]
    assert bytes(sftp.store[REMOTE_FILE]) == SOURCE


def test_ssh_upload_resume_starts_at_remote_size(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: PARTIAL})
    backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert sftp.modes(REMOTE_FILE) == ["ab"]
    assert bytes(sftp.store[REMOTE_FILE]) == PARTIAL + SOURCE[len(PARTIAL):]


def test_ssh_upload_overwrite_replaces_equal_sized_remote(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: b"ZZZZZZ"})
    backend.upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert sftp.modes(REMOTE_FILE) == ["wb"]
    assert bytes(sftp.store[REMOTE_FILE]) == SOURCE


def test_ssh_upload_resume_equal_size_is_completed_noop(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: b"ZZZZZZ"})
    progress, callback = recorder()
    backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE, callback)
    assert sftp.modes(REMOTE_FILE) == []
    assert progress == [(len(SOURCE), len(SOURCE))]
    assert bytes(sftp.store[REMOTE_FILE]) == b"ZZZZZZ"


def test_ssh_upload_resume_zero_length_remote_transfers_everything(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: b""})
    backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert sftp.modes(REMOTE_FILE) == ["wb"]
    assert bytes(sftp.store[REMOTE_FILE]) == SOURCE


def test_ssh_resume_upload_rejects_remote_larger_than_local(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: SOURCE + b"EXTRA"})
    with pytest.raises(ValueError) as excinfo:
        backend.resume_upload(write_local(tmp_path, SOURCE), REMOTE_FILE)
    assert str(excinfo.value) == RESUME_DEST_LARGER.format(path=REMOTE_FILE)
    assert sftp.modes(REMOTE_FILE) == []
    assert bytes(sftp.store[REMOTE_FILE]) == SOURCE + b"EXTRA"


# --------------------------------------------------------------------------
# SFTP download
# --------------------------------------------------------------------------

def test_ssh_download_overwrite_replaces_local_file(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, PARTIAL, "dst.bin")
    backend.download(REMOTE_FILE, local)
    assert sftp.seeks(REMOTE_FILE) == []
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


def test_ssh_download_resume_starts_at_local_size(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, PARTIAL, "dst.bin")
    backend.resume_download(REMOTE_FILE, local)
    assert sftp.seeks(REMOTE_FILE) == [len(PARTIAL)]
    with open(local, "rb") as handle:
        assert handle.read() == PARTIAL + SOURCE[len(PARTIAL):]


def test_ssh_download_overwrite_replaces_equal_sized_local(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, b"ZZZZZZ", "dst.bin")
    backend.download(REMOTE_FILE, local)
    assert sftp.seeks(REMOTE_FILE) == []
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


def test_ssh_download_resume_equal_size_is_completed_noop(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, b"ZZZZZZ", "dst.bin")
    progress, callback = recorder()
    backend.resume_download(REMOTE_FILE, local, callback)
    assert sftp.modes(REMOTE_FILE) == []
    assert progress == [(len(SOURCE), len(SOURCE))]
    with open(local, "rb") as handle:
        assert handle.read() == b"ZZZZZZ"


def test_ssh_download_resume_zero_length_local_transfers_everything(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    local = write_local(tmp_path, b"", "dst.bin")
    backend.resume_download(REMOTE_FILE, local)
    assert sftp.seeks(REMOTE_FILE) == []
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


def test_ssh_resume_download_rejects_local_larger_than_remote(tmp_path):
    backend, sftp = ssh_backend({REMOTE_FILE: PARTIAL})
    local = write_local(tmp_path, SOURCE, "dst.bin")
    with pytest.raises(ValueError) as excinfo:
        backend.resume_download(REMOTE_FILE, local)
    assert str(excinfo.value) == RESUME_DEST_LARGER.format(path=local)
    assert sftp.modes(REMOTE_FILE) == []
    with open(local, "rb") as handle:
        assert handle.read() == SOURCE


# --------------------------------------------------------------------------
# Overwrite and Resume must not be interchangeable
# --------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["ftp", "ssh"])
def test_overwrite_and_resume_upload_produce_different_bytes(tmp_path, kind):
    local = write_local(tmp_path, SOURCE)
    if kind == "ftp":
        overwrite = ftp_backend({REMOTE_FILE: PARTIAL})
        resume = ftp_backend({REMOTE_FILE: PARTIAL})
        overwrite.upload(local, REMOTE_FILE)
        resume.resume_upload(local, REMOTE_FILE)
        after_overwrite = bytes(overwrite.ftp.files[REMOTE_FILE])
        after_resume = bytes(resume.ftp.files[REMOTE_FILE])
    else:
        overwrite, overwrite_sftp = ssh_backend({REMOTE_FILE: PARTIAL})
        resume, resume_sftp = ssh_backend({REMOTE_FILE: PARTIAL})
        overwrite.upload(local, REMOTE_FILE)
        resume.resume_upload(local, REMOTE_FILE)
        after_overwrite = bytes(overwrite_sftp.store[REMOTE_FILE])
        after_resume = bytes(resume_sftp.store[REMOTE_FILE])
    assert after_overwrite == SOURCE
    assert after_resume == PARTIAL + SOURCE[len(PARTIAL):]
    assert after_overwrite != after_resume


@pytest.mark.parametrize("kind", ["ftp", "ssh"])
def test_overwrite_and_resume_download_produce_different_bytes(tmp_path, kind):
    overwrite_local = write_local(tmp_path, PARTIAL, "ow.bin")
    resume_local = write_local(tmp_path, PARTIAL, "rs.bin")
    if kind == "ftp":
        backend = ftp_backend({REMOTE_FILE: SOURCE})
    else:
        backend, _ = ssh_backend({REMOTE_FILE: SOURCE})
    backend.download(REMOTE_FILE, overwrite_local)
    backend.resume_download(REMOTE_FILE, resume_local)
    with open(overwrite_local, "rb") as handle:
        overwritten = handle.read()
    with open(resume_local, "rb") as handle:
        resumed = handle.read()
    assert overwritten == SOURCE
    assert resumed == PARTIAL + SOURCE[len(PARTIAL):]
    assert overwritten != resumed
    assert os.path.getsize(overwrite_local) == os.path.getsize(resume_local)
