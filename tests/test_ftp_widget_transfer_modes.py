"""Focused FTP widget tests for transfer modes behavior."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
from pathlib import Path
import pytest
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.services.transfer_mode import (
    ASCII,
    AUTO,
    BINARY,
    _ascii_bytes_for_local,
    _ascii_bytes_for_remote,
    download_with_mode,
    resolve_transfer_mode,
    upload_with_mode,
)
from ftp_widget_test_support import FtpWidgetTestCase, _ProgressUploadFiles, _ResumableFiles


class FtpWidgetTransferModesTests(FtpWidgetTestCase):
    @pytest.mark.unit
    @pytest.mark.semantic
    def test_transfer_mode_policy_and_conversion(self) -> None:
        self.assertEqual(resolve_transfer_mode("notes.txt", AUTO), ASCII)
        self.assertEqual(resolve_transfer_mode("archive", AUTO), BINARY)
        self.assertEqual(resolve_transfer_mode("image.bin", AUTO, b"\x00x"), BINARY)
        with self.assertRaises(ValueError):
            resolve_transfer_mode("image.bin", ASCII, b"\x00x")

        self.assertEqual(_ascii_bytes_for_remote(b"a\r\nb\r\n"), b"a\nb\n")
        self.assertEqual(
            _ascii_bytes_for_local(b"x\ny\n").decode("utf-8").splitlines(),
            ["x", "y"],
        )

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.resource
    def test_download_with_mode_resumes_from_part_and_replaces_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "large.bin")
            part = Path(str(destination) + ".part")
            part.write_bytes(b"partial-")
            files = _ResumableFiles(b"partial-complete")

            effective = download_with_mode(
                files,
                "/remote/large.bin",
                str(destination),
                BINARY,
            )

            self.assertEqual(effective, BINARY)
            self.assertEqual(files.calls, [str(part)])
            self.assertEqual(destination.read_bytes(), b"partial-complete")
            self.assertFalse(part.exists())

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.resource
    @pytest.mark.regression
    def test_resume_rejects_stale_download_part_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "large.bin")
            part = Path(str(destination) + ".part")
            part.write_bytes(b"stale")
            Path(str(part) + ".meta").write_text("{}", encoding="utf-8")
            files = MockFilesBackend()
            files.write_text("/remote/large.bin", "fresh-content")

            download_with_mode(files, "/remote/large.bin", str(destination), BINARY)

            self.assertEqual(destination.read_bytes(), b"fresh-content")
            self.assertFalse(Path(str(part) + ".meta").exists())

    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.resource
    @pytest.mark.regression
    def test_resume_rejects_stale_upload_part_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "payload.bin")
            source.write_bytes(b"fresh-content")
            files = MockFilesBackend()
            stale = Path(tmp, "stale.bin")
            stale.write_bytes(b"stale")
            files.upload(str(stale), "/remote/payload.bin.part")
            files.write_text("/remote/payload.bin.part.meta", "{}")

            upload_with_mode(files, str(source), "/remote/payload.bin", BINARY)

            self.assertEqual(files.read_text("/remote/payload.bin"), "fresh-content")
            self.assertFalse(files.exists("/remote/payload.bin.part.meta"))

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_upload_with_mode_forwards_progress_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "payload.bin")
            source.write_bytes(b"\x00" + b"x" * 4096)
            files = _ProgressUploadFiles()
            progress = []

            effective = upload_with_mode(
                files,
                str(source),
                "/remote/payload.bin",
                BINARY,
                progress_cb=lambda done, total: progress.append((done, total)),
            )

            self.assertEqual(effective, BINARY)
            self.assertEqual(files.calls, [(str(source), "/remote/payload.bin")])
            self.assertEqual(progress[-1], (source.stat().st_size, source.stat().st_size))
