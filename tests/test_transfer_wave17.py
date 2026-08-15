"""Wave 17 focused regression tests for transfer integrity and streaming.

Covers the bounded-read streaming conversions (no whole-file read), CRLF/LF
normalization, invalid UTF-8 rejection, ``.dat`` Auto semantics, the
``<destination>.part`` download swap, and the rename-capable upload path with
its direct fallback.
"""

from __future__ import annotations

import builtins
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hpc_gui.services.transfer_mode import (
    ASCII,
    AUTO,
    BINARY,
    CHUNK_SIZE,
    download_with_mode,
    resolve_transfer_mode,
    upload_with_mode,
)


class _MemFiles:
    """Tiny in-memory backend that can optionally expose a rename operation."""

    def __init__(self, rename_capable: bool = True) -> None:
        self.remote: dict[str, bytes] = {}
        self.rename_capable = rename_capable
        self.upload_calls: list[tuple[str, str]] = []
        self.download_calls: list[tuple[str, str]] = []
        if not rename_capable:
            # Shadow the class-level rename so the backend genuinely lacks a
            # callable rename operation, exactly like real backends that do not
            # support server-side renaming.
            self.rename = None

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        self.upload_calls.append((local_path, remote_path))
        self.remote[remote_path] = Path(local_path).read_bytes()

    def download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        self.download_calls.append((remote_path, local_path))
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        Path(local_path).write_bytes(self.remote[remote_path])

    def rename(self, old_path: str, new_path: str) -> None:
        self.remote[new_path] = self.remote.pop(old_path)


class _ReadSpy:
    """Records every ``read`` request size for a set of watched paths."""

    def __init__(self) -> None:
        self.reads: list[int] = []
        self._watched: set[str] = set()

    def patch(self, *paths: str):
        self._watched = {os.fspath(path) for path in paths}
        real_open = builtins.open

        def spy(path, *args, **kwargs):
            handle = real_open(path, *args, **kwargs)
            try:
                key = os.fspath(path)
            except TypeError:
                key = None
            if key in self._watched:
                read = handle.read

                def recorded(size: int = -1) -> bytes:
                    self.reads.append(size)
                    return read(size)

                handle.read = recorded
            return handle

        return patch("builtins.open", side_effect=spy)


class DatSemanticsTests(unittest.TestCase):
    def test_dat_is_binary_in_auto_mode(self) -> None:
        self.assertEqual(resolve_transfer_mode("input.dat", AUTO), BINARY)
        self.assertEqual(resolve_transfer_mode("input.dat", ASCII), ASCII)
        self.assertEqual(resolve_transfer_mode("input.dat", BINARY), BINARY)
        self.assertEqual(resolve_transfer_mode("notes.txt", AUTO), ASCII)
        self.assertEqual(resolve_transfer_mode("archive", AUTO), BINARY)

    def test_auto_dat_upload_passes_through_unconverted(self) -> None:
        data = b"1 2 3\r\n4 5 6\r\n"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "input.dat")
            source.write_bytes(data)
            files = _MemFiles(rename_capable=False)
            effective = upload_with_mode(files, str(source), "/remote/input.dat", AUTO)
        self.assertEqual(effective, BINARY)
        self.assertEqual(files.remote["/remote/input.dat"], data)

    def test_explicit_ascii_rejects_binary_content(self) -> None:
        with self.assertRaises(ValueError):
            resolve_transfer_mode("file.txt", ASCII, b"ok\x00binary")
        with self.assertRaises(ValueError):
            resolve_transfer_mode("file.txt", ASCII, b"\xff\xfe")
        self.assertEqual(resolve_transfer_mode("file.bin", BINARY, b"\x00x"), BINARY)


class StreamingConversionTests(unittest.TestCase):
    def test_ascii_upload_normalizes_line_endings_to_lf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "text.txt")
            source.write_bytes(b"a\r\nb\nc\r")
            files = _MemFiles(rename_capable=False)
            effective = upload_with_mode(files, str(source), "/remote/text.txt", ASCII)
        self.assertEqual(effective, ASCII)
        self.assertEqual(files.remote["/remote/text.txt"], b"a\nb\nc\n")

    def test_ascii_download_normalizes_line_endings_to_local(self) -> None:
        files = _MemFiles(rename_capable=False)
        files.remote["/remote/text.txt"] = b"a\r\nb\nc\r"
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "text.txt")
            effective = download_with_mode(
                files, "/remote/text.txt", str(destination), ASCII
            )
            expected = "a\nb\nc\n".replace("\n", os.linesep).encode("utf-8")
            downloaded = destination.read_bytes()
            part_remains = Path(str(destination) + ".part").exists()
            tmp_remains = Path(str(destination) + ".tmp").exists()
        self.assertEqual(effective, ASCII)
        self.assertEqual(downloaded, expected)
        self.assertFalse(part_remains)
        self.assertFalse(tmp_remains)

    def test_crlf_split_across_chunk_boundary_stays_one_newline(self) -> None:
        content = "x" * (CHUNK_SIZE - 1) + "\r\ny"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "edge.txt")
            source.write_bytes(content.encode("utf-8"))
            files = _MemFiles(rename_capable=False)
            upload_with_mode(files, str(source), "/remote/edge.txt", ASCII)
        self.assertEqual(
            files.remote["/remote/edge.txt"],
            ("x" * (CHUNK_SIZE - 1) + "\ny").encode("utf-8"),
        )

    def test_multibyte_utf8_across_chunk_boundary_is_preserved(self) -> None:
        # The three-byte euro sign straddles the boundary between the second
        # and third read chunks, while the first (classification) sample stays
        # entirely ASCII so the file is still classified as text.
        content = "y" * (CHUNK_SIZE * 2 - 1) + "€z"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "utf8.txt")
            source.write_bytes(content.encode("utf-8"))
            files = _MemFiles(rename_capable=False)
            upload_with_mode(files, str(source), "/remote/utf8.txt", ASCII)
        self.assertEqual(files.remote["/remote/utf8.txt"], content.encode("utf-8"))

    def test_ascii_upload_rejects_late_invalid_utf8(self) -> None:
        data = b"a" * CHUNK_SIZE + b"\xff\xfe bad\n"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "bad.txt")
            source.write_bytes(data)
            files = _MemFiles(rename_capable=False)
            with self.assertRaises(ValueError):
                upload_with_mode(files, str(source), "/remote/bad.txt", ASCII)
        self.assertNotIn("/remote/bad.txt", files.remote)

    def test_ascii_upload_rejects_truncated_utf8_at_eof(self) -> None:
        data = b"a" * CHUNK_SIZE + b"\xc3"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "bad.txt")
            source.write_bytes(data)
            files = _MemFiles(rename_capable=False)
            with self.assertRaises(ValueError):
                upload_with_mode(files, str(source), "/remote/bad.txt", ASCII)
        self.assertNotIn("/remote/bad.txt", files.remote)

    def test_ascii_download_rejects_invalid_utf8_and_keeps_final(self) -> None:
        files = _MemFiles(rename_capable=False)
        files.remote["/remote/bad.txt"] = b"a" * CHUNK_SIZE + b"\xff"
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "bad.txt")
            destination.write_bytes(b"KEEP")
            with self.assertRaises(ValueError):
                download_with_mode(files, "/remote/bad.txt", str(destination), ASCII)
            kept = destination.read_bytes()
        self.assertEqual(kept, b"KEEP")


class DroppedConnectionTests(unittest.TestCase):
    def test_mid_download_drop_preserves_final_and_partial(self) -> None:
        class Dropped(_MemFiles):
            def download(self, _remote_path, local_path, progress_cb=None):
                Path(local_path).write_bytes(b"partial")
                raise OSError("connection dropped")

        files = Dropped(rename_capable=False)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "data.bin")
            destination.write_bytes(b"ORIGINAL")
            with self.assertRaises(OSError):
                download_with_mode(files, "/remote/data.bin", str(destination), BINARY)
            self.assertEqual(destination.read_bytes(), b"ORIGINAL")
            self.assertEqual(Path(str(destination) + ".part").read_bytes(), b"partial")

    def test_mid_upload_drop_preserves_final_and_partial(self) -> None:
        class Dropped(_MemFiles):
            def upload(self, local_path, remote_path, progress_cb=None):
                self.remote[remote_path] = Path(local_path).read_bytes()[:7]
                raise OSError("connection dropped")

        files = Dropped(rename_capable=True)
        files.remote["/remote/data.bin"] = b"ORIGINAL"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "data.bin")
            source.write_bytes(b"NEW CONTENT")
            with self.assertRaises(OSError):
                upload_with_mode(files, str(source), "/remote/data.bin", BINARY)
        self.assertEqual(files.remote["/remote/data.bin"], b"ORIGINAL")
        self.assertEqual(files.remote["/remote/data.bin.part"], b"NEW CON")

class BoundedReadTests(unittest.TestCase):
    def test_ascii_upload_reads_source_in_bounded_chunks(self) -> None:
        data = b"line\r\n" * 3000
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "big.txt")
            source.write_bytes(data)
            files = _MemFiles(rename_capable=False)
            spy = _ReadSpy()
            with spy.patch(str(source)):
                effective = upload_with_mode(
                    files, str(source), "/remote/big.txt", ASCII
                )
        self.assertEqual(effective, ASCII)
        self.assertTrue(spy.reads)
        self.assertEqual(max(spy.reads), CHUNK_SIZE)
        self.assertNotIn(len(data), spy.reads)
        self.assertEqual(
            files.remote["/remote/big.txt"],
            data.replace(b"\r\n", b"\n"),
        )

    def test_ascii_download_converts_part_in_bounded_chunks(self) -> None:
        data = b"line\n" * 3000
        files = _MemFiles(rename_capable=False)
        files.remote["/remote/big.txt"] = data
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "big.txt")
            spy = _ReadSpy()
            with spy.patch(str(destination) + ".part"):
                effective = download_with_mode(
                    files, "/remote/big.txt", str(destination), ASCII
                )
            expected = data.decode("utf-8").replace("\n", os.linesep).encode("utf-8")
            downloaded = destination.read_bytes()
        self.assertEqual(effective, ASCII)
        self.assertTrue(spy.reads)
        self.assertLess(max(spy.reads), len(data))
        self.assertNotIn(len(data), spy.reads)
        self.assertEqual(downloaded, expected)


class DownloadIntegrityTests(unittest.TestCase):
    def test_failed_download_leaves_final_untouched(self) -> None:
        class _FailingDownload(_MemFiles):
            def download(self, remote_path, local_path, progress_cb=None):
                raise OSError("simulated network failure")

        files = _FailingDownload()
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "keep.bin")
            destination.write_bytes(b"ORIGINAL")
            with self.assertRaises(OSError):
                download_with_mode(
                    files, "/remote/x.bin", str(destination), BINARY
                )
            self.assertEqual(destination.read_bytes(), b"ORIGINAL")

    def test_download_replaces_final_only_after_success(self) -> None:
        data = b"complete payload"
        files = _MemFiles(rename_capable=False)
        files.remote["/remote/data.bin"] = data
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "data.bin")
            destination.write_bytes(b"OLD")
            effective = download_with_mode(
                files, "/remote/data.bin", str(destination), BINARY
            )
            self.assertEqual(effective, BINARY)
            self.assertEqual(destination.read_bytes(), data)
            self.assertFalse(Path(str(destination) + ".part").exists())

    def test_download_resumes_from_existing_part(self) -> None:
        data = b"complete payload"
        files = _MemFiles(rename_capable=False)
        files.remote["/remote/data.bin"] = data

        def resuming_download(remote_path, local_path, progress_cb=None):
            existing = Path(local_path).read_bytes() if Path(local_path).exists() else b""
            Path(local_path).write_bytes(existing + data[len(existing):])

        files.download = resuming_download
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp, "data.bin")
            destination.write_bytes(b"OLD")
            part = Path(str(destination) + ".part")
            part.write_bytes(data[:5])
            effective = download_with_mode(
                files, "/remote/data.bin", str(destination), BINARY
            )
            self.assertEqual(effective, BINARY)
            self.assertEqual(destination.read_bytes(), data)
            self.assertFalse(part.exists())


class UploadIntegrityTests(unittest.TestCase):
    def test_upload_with_rename_uses_temp_name_then_renames(self) -> None:
        data = b"\x00\x01payload"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "data.bin")
            source.write_bytes(data)
            files = _MemFiles(rename_capable=True)
            effective = upload_with_mode(
                files, str(source), "/remote/data.bin", BINARY
            )
        self.assertEqual(effective, BINARY)
        self.assertEqual(files.upload_calls, [(str(source), "/remote/data.bin.part")])
        self.assertNotIn("/remote/data.bin.part", files.remote)
        self.assertEqual(files.remote.get("/remote/data.bin"), data)

    def test_upload_without_rename_uploads_directly(self) -> None:
        data = b"\x00\x01payload"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "data.bin")
            source.write_bytes(data)
            files = _MemFiles(rename_capable=False)
            effective = upload_with_mode(
                files, str(source), "/remote/data.bin", BINARY
            )
        self.assertEqual(effective, BINARY)
        self.assertEqual(files.upload_calls, [(str(source), "/remote/data.bin")])
        self.assertEqual(files.remote.get("/remote/data.bin"), data)

    def test_ascii_upload_with_rename_uploads_converted_temp_then_renames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "text.txt")
            source.write_bytes(b"a\r\nb\r\n")
            files = _MemFiles(rename_capable=True)
            effective = upload_with_mode(files, str(source), "/remote/text.txt", ASCII)
        self.assertEqual(effective, ASCII)
        self.assertEqual(len(files.upload_calls), 1)
        uploaded_local, uploaded_remote = files.upload_calls[0]
        self.assertEqual(uploaded_remote, "/remote/text.txt.part")
        self.assertNotEqual(uploaded_local, str(source))
        self.assertEqual(files.remote.get("/remote/text.txt"), b"a\nb\n")
        self.assertNotIn("/remote/text.txt.part", files.remote)


if __name__ == "__main__":
    unittest.main()
