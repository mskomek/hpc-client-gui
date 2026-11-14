"""Strict vs display SFTP decoding and file-handle cleanup contracts."""

from __future__ import annotations

import codecs

import pytest

from hpc_gui.services.files_ssh_text import SSHTextMixin
from hpc_gui.services.files_ssh import SSHFilesBackend


pytestmark = pytest.mark.unit


class _RemoteFile:
    def __init__(self, storage, path, mode):
        self.storage = storage
        self.path = path
        self.mode = mode

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.storage[self.path]

    def write(self, data):
        assert "w" in self.mode and isinstance(data, bytes)
        self.storage[self.path] = data
        return len(data)


class _SFTP:
    def __init__(self, storage):
        self.storage = storage
        self.closed = False

    def open(self, path, mode):
        if "r" in mode and path not in self.storage:
            raise FileNotFoundError(2, "missing", path)
        return _RemoteFile(self.storage, path, mode)

    def close(self):
        self.closed = True


class _SSH:
    def __init__(self, storage):
        self.storage = storage
        self.sftp = _SFTP(storage)
        self.transfers = []

    def open_transfer_sftp(self):
        result = _SFTP(self.storage)
        self.transfers.append(result)
        return result


def _backend(storage):
    # Bypass connection capability probing: exercise just the inherited
    # text methods with a fake self.ssh.
    backend = object.__new__(SSHFilesBackend)
    backend.ssh = _SSH(storage)
    return backend


def test_text_methods_remain_inherited_from_exact_extracted_mixin():
    for method in (
        "read_text", "read_text_for_edit", "_read_text",
        "read_text_document", "write_text", "write_text_document",
    ):
        assert getattr(SSHFilesBackend, method) is getattr(SSHTextMixin, method)


def test_display_replaces_invalid_utf8_but_edit_rejects_it():
    backend = _backend({"/scratch/log": b"abc\xffdef"})
    assert backend.read_text("/scratch/log") == "abc\ufffddef"
    with pytest.raises(UnicodeDecodeError):
        backend.read_text_for_edit("/scratch/log")
    assert len(backend.ssh.transfers) == 2
    assert all(sftp.closed for sftp in backend.ssh.transfers)


def test_read_document_detects_utf8_bom_and_closes_sftp():
    backend = _backend({"/scratch/script": codecs.BOM_UTF8 + b"Hello"})
    assert backend.read_text_document("/scratch/script") == ("Hello", "utf-8-sig")
    assert backend.ssh.transfers[-1].closed


def test_read_failure_still_closes_transfer_channel_and_reports_path():
    backend = _backend({})
    with pytest.raises(FileNotFoundError) as exc:
        backend.read_text_for_edit("/scratch/missing")
    assert exc.value.filename == "/scratch/missing"
    assert backend.ssh.transfers[-1].closed


def test_legacy_write_contracts_keep_utf8_and_explicit_encoding():
    storage = {}
    backend = _backend(storage)
    backend.write_text("/scratch/tr", "Çağrı")
    assert storage["/scratch/tr"] == "Çağrı".encode("utf-8")
    backend.write_text_document("/scratch/latin", "café", "cp1252")
    assert storage["/scratch/latin"] == "café".encode("cp1252")
