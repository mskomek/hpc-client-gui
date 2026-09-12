"""Wave 3 — Remote Files, SFTP, SSH and Unicode-Safe Command Handling.

Guarantee remote filenames, directories, SSH commands, and streamed output
remain Unicode-safe and cannot silently target the wrong object.
"""

from __future__ import annotations

import io
import pathlib
import shlex
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Golden Fixtures — Unicode remote names
# ---------------------------------------------------------------------------

TURKISH_REMOTE_NAMES = [
    "Çalışmalar",
    "İşler_Çağrı_Ölçüm",
    "ısı_ölçümü.txt",
    "şğüöçıİ.dat",
]

JAPANESE_REMOTE_NAMES = [
    "日本語",
    "研究_ジョブ",
    "ジョブ結果.dat",
    "計算_結果.txt",
]

MIXED_REMOTE_NAMES = [
    "Türkçe_日本語",
    "iş_日本語_δ.txt",
]

ALL_REMOTE_NAMES = TURKISH_REMOTE_NAMES + JAPANESE_REMOTE_NAMES + MIXED_REMOTE_NAMES


# ---------------------------------------------------------------------------
# 1. SSH Command Construction Safety
# ---------------------------------------------------------------------------

class TestSSHCommandConstruction:
    """Verify SSH commands are safely constructed with proper quoting."""

    def test_shlex_quote_unicode_path(self):
        """shlex.quote should safely quote Unicode paths."""
        paths = [
            "Çalışmalar/test.txt",
            "日本語/計算結果.txt",
            "Türkçe_日本語/file.txt",
            "O'Brien.txt",
            "file with spaces.txt",
            "file$pecial.txt",
            "file(parentheses).txt",
            "file[brackets].txt",
            "file&ampersand.txt",
        ]
        for path in paths:
            quoted = shlex.quote(path)
            # Quoted path should be safe for shell
            assert quoted.startswith("'") or quoted.startswith('"') or not any(c in path for c in " $&()[]'\"")

    def test_shlex_quote_preserves_unicode(self):
        """shlex.quote should preserve Unicode characters."""
        paths = [
            "Çalışma_Sonucu.txt",
            "日本語_計算結果.txt",
            "★_Favorites.txt",
            "İşler_Çağrı.txt",
        ]
        for path in paths:
            quoted = shlex.quote(path)
            # Remove quotes and verify content preserved
            unquoted = quoted.strip("'\"")
            assert unquoted == path, f"shlex.quote corrupted path: {path} -> {quoted}"

    def test_ssh_backend_uses_shlex_quote(self):
        """A hostile Unicode path remains one shell argument for remote rm."""
        from types import SimpleNamespace

        from hpc_gui.services.files_ssh import SSHFilesBackend

        commands = []
        ssh = SimpleNamespace(
            sftp=object(),
            run=lambda command: (commands.append(command) or (0, "", "")),
        )
        backend = SSHFilesBackend(ssh)
        remote_path = "/scratch/Çalışma O'Brien/$(touch sentinel).txt"

        backend.remove(remote_path)

        assert commands == [f"rm -f {shlex.quote(remote_path)}"]
        assert shlex.split(commands[0]) == ["rm", "-f", remote_path]


# ---------------------------------------------------------------------------
# 2. SFTP Unicode Path Handling
# ---------------------------------------------------------------------------

class TestSFTPUnicodePaths:
    """Verify SFTP operations handle Unicode paths correctly."""

    def test_mock_backend_unicode_listdir(self):
        """Mock backend should list Unicode-named entries."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        # Add Unicode entries using internal API
        backend._dirs.add("/work")
        backend._dirs.add("/work/Çalışmalar")
        backend._dirs.add("/work/日本語")
        backend._files["/work/日本語/file.txt"] = b"test content"

        entries = backend.listdir("/work")
        assert "Çalışmalar" in entries
        assert "日本語" in entries

    def test_mock_backend_unicode_read_write(self):
        """Mock backend should read/write Unicode content."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        # Write Unicode content
        content = "İş tamamlandı 日本語 ✓"
        backend.write_text("/work/test.txt", content)

        # Read it back
        read_content = backend.read_text("/work/test.txt")
        assert read_content == content

    def test_ssh_backend_rejects_invalid_utf8_text(self):
        """Remote editor reads must not replace bytes before a later save."""
        from hpc_gui.services.files_ssh import SSHFilesBackend

        class SFTP:
            def open(self, _path, _mode):
                return io.BytesIO(b"valid\xff")

            def close(self):
                pass

        class SSH:
            def open_transfer_sftp(self):
                return SFTP()

        backend = SSHFilesBackend.__new__(SSHFilesBackend)
        backend.ssh = SSH()
        with pytest.raises(UnicodeDecodeError):
            backend.read_text("/work/legacy.txt")

    def test_mock_backend_unicode_rename(self):
        """Mock backend should rename to/from Unicode names."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")
        backend._files["/work/old.txt"] = b"content"

        # Rename to Unicode name
        backend.rename("/work/old.txt", "/work/yeniden_adlandır.txt")
        assert "/work/yeniden_adlandır.txt" in backend._files
        assert "/work/old.txt" not in backend._files

    def test_mock_backend_unicode_mkdir(self):
        """Mock backend should create Unicode-named directories."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        backend.mkdir("/work/日本語_ディレクトリ")
        assert backend.is_dir("/work/日本語_ディレクトリ")

    def test_mock_backend_unicode_remove(self):
        """Mock backend should remove Unicode-named files."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")
        backend._files["/work/★.txt"] = b"star content"

        backend.remove("/work/★.txt")
        assert "/work/★.txt" not in backend._files


# ---------------------------------------------------------------------------
# 3. RemoteEntry Type Safety
# ---------------------------------------------------------------------------

class TestRemoteEntryTypes:
    """Verify RemoteEntry types are consistent across layers."""

    def test_files_base_remote_entry_fields(self):
        """files_base.RemoteEntry should have 6 fields."""
        from hpc_gui.services.files_base import RemoteEntry

        entry = RemoteEntry(
            name="test.txt",
            path="/work/test.txt",
            is_dir=False,
            size=100,
            mtime=1234567890,
            mode=0o644,
        )
        assert entry.name == "test.txt"
        assert entry.path == "/work/test.txt"
        assert entry.is_dir is False
        assert entry.size == 100
        assert entry.mtime == 1234567890
        assert entry.mode == 0o644

    def test_wx_remote_files_entry_fields(self):
        """wx_remote_files.RemoteEntry should have 3 fields."""
        from hpc_gui.wx_remote_files import RemoteEntry

        entry = RemoteEntry(
            path="/work/test.txt",
            is_dir=False,
            size=100,
        )
        assert entry.path == "/work/test.txt"
        assert entry.is_dir is False
        assert entry.size == 100


# ---------------------------------------------------------------------------
# 4. Remote Directory Controller
# ---------------------------------------------------------------------------

class TestRemoteDirectoryController:
    """Verify remote directory controller navigation and generation tracking."""

    def test_navigate_increments_generation(self):
        """navigate() should increment generation counter."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        req1 = controller.navigate("/work/dir1")
        req2 = controller.navigate("/work/dir2")

        assert req2.generation > req1.generation
        assert req1.path == "/work/dir1"
        assert req2.path == "/work/dir2"

    def test_is_current_detects_stale(self):
        """is_current() should detect stale listing requests."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        req1 = controller.navigate("/work/dir1")
        req2 = controller.navigate("/work/dir2")

        # req1 is stale after navigating to dir2
        assert not controller.is_current(req1)
        # req2 is current
        assert controller.is_current(req2)

    def test_back_navigates_to_previous(self):
        """back() should navigate to previous directory."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        controller.navigate("/work/dir1")
        controller.navigate("/work/dir2")

        req = controller.back()
        assert req.path == "/work/dir1"

    def test_normalize_strips_trailing_slash(self):
        """_normalize should strip trailing slashes."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        assert controller._normalize("/work/dir/") == "/work/dir"
        assert controller._normalize("/work/dir//") == "/work/dir"
        assert controller._normalize("/") == "/"

    def test_normalize_defaults_to_root(self):
        """_normalize should default to '/' for empty/None."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        assert controller._normalize(None) == "/"
        assert controller._normalize("") == "/"


# ---------------------------------------------------------------------------
# 5. Shell Session UTF-8 Decoding
# ---------------------------------------------------------------------------

class TestShellSessionDecoding:
    """Verify shell session handles UTF-8 decoding correctly."""

    def test_incremental_decoder_unicode(self):
        """Incremental decoder should handle Unicode characters."""
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8")("replace")

        # Turkish characters
        text = "İş tamamlandı ✓"
        encoded = text.encode("utf-8")
        decoded = decoder.decode(encoded, final=True)
        assert decoded == text

    def test_incremental_decoder_split_bytes(self):
        """Incremental decoder should handle split multi-byte sequences."""
        import codecs

        # Japanese character は (U+540D) is 3 bytes in UTF-8
        text = "日本語"
        encoded = text.encode("utf-8")

        # Split at each byte boundary
        for i in range(1, len(encoded)):
            decoder2 = codecs.getincrementaldecoder("utf-8")("replace")
            part1 = decoder2.decode(encoded[:i], final=False)
            part2 = decoder2.decode(encoded[i:], final=True)
            result = part1 + part2
            assert result == text, f"Split at byte {i} failed: {result!r} != {text!r}"

    def test_incremental_decoder_emoji(self):
        """Incremental decoder should handle emoji (4-byte UTF-8)."""
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8")("replace")

        text = "🚀_job.txt"
        encoded = text.encode("utf-8")
        decoded = decoder.decode(encoded, final=True)
        assert decoded == text

    def test_incremental_decoder_turkish_dotless_i(self):
        """Incremental decoder should handle Turkish dotless i."""
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8")("replace")

        # Turkish: İ (U+0130) and ı (U+0131)
        text = "İstanbul_ırmak"
        encoded = text.encode("utf-8")
        decoded = decoder.decode(encoded, final=True)
        assert decoded == text


# ---------------------------------------------------------------------------
# 6. Unicode File Content Roundtrip
# ---------------------------------------------------------------------------

class TestUnicodeFileContentRoundtrip:
    """Verify file content survives Unicode roundtrip through backends."""

    def test_mock_backend_unicode_content_roundtrip(self):
        """Mock backend should preserve Unicode content through read/write."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        contents = [
            "İş tamamlandı 日本語 ✓",
            "Türkçe_日本語 dosya içeriği",
            "★ Favoriler listesi\nSatır 2\nSatır 3",
            "çalışma sonuçları: 42",
            "研究結果: 完了",
        ]

        for i, content in enumerate(contents):
            path = f"/work/file_{i}.txt"
            backend.write_text(path, content)
            read_content = backend.read_text(path)
            assert read_content == content, f"Roundtrip failed for: {content!r}"

    def test_unicode_paths_in_listings(self):
        """Unicode file names should appear correctly in listings."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        for name in ALL_REMOTE_NAMES:
            path = f"/work/{name}"
            if "." in name:
                backend._files[path] = f"content of {name}".encode("utf-8")
            else:
                backend._dirs.add(path)

        entries = backend.listdir("/work")

        for name in ALL_REMOTE_NAMES:
            assert name in entries, f"Unicode name {name!r} missing from listing"


# ---------------------------------------------------------------------------
# 7. SFTP Channel Manager
# ---------------------------------------------------------------------------

class TestSFTPChannelManager:
    """Verify SFTP channel manager handles Unicode paths."""

    def test_channel_manager_exists(self):
        """SFTPChannelManager should be importable."""
        from hpc_gui.ssh.sftp_channels import SFTPChannelManager
        assert SFTPChannelManager is not None

    def test_channel_manager_timeouts(self):
        """SFTPChannelManager should have defined timeouts."""

        # Check timeout constants exist
        import hpc_gui.ssh.sftp_channels as module
        assert hasattr(module, "_SFTP_TRANSFER_TIMEOUT_SECONDS")
        assert hasattr(module, "_SFTP_LISTING_TIMEOUT_SECONDS")


# ---------------------------------------------------------------------------
# 8. SSH Client Unicode Handling
# ---------------------------------------------------------------------------

class TestSSHClientUnicode:
    """Verify SSH client handles Unicode correctly."""

    def test_remote_display_decoder_is_explicit_utf8_with_safe_fallback(self):
        """SSH command/banner display output uses an explicit UTF-8 policy."""
        from hpc_gui.ssh.client import _decode_remote_text

        assert _decode_remote_text("çıktı 日本語".encode("utf-8")) == "çıktı 日本語"
        assert _decode_remote_text(b"bad\xff") == "bad\ufffd"

    def test_ssh_client_exists(self):
        """SSHClientWrapper should be importable."""
        from hpc_gui.ssh.client import SSHClientWrapper
        assert SSHClientWrapper is not None

    def test_ssh_conn_info_dataclass(self):
        """SSHConnInfo should be a proper dataclass."""
        from hpc_gui.ssh.client import SSHConnInfo

        info = SSHConnInfo(
            host="test.example.com",
            port=22,
            username="testuser",
        )
        assert info.host == "test.example.com"
        assert info.port == 22
        assert info.username == "testuser"


# ---------------------------------------------------------------------------
# 9. Remote Entry Helpers
# ---------------------------------------------------------------------------

class TestRemoteEntryHelpers:
    """Verify remote entry helper functions handle Unicode."""

    def test_file_type_directory(self):
        """file_type should detect directories correctly."""
        from hpc_gui.ui.models.remote_entry_helpers import file_type

        result = file_type("test", is_dir=True)
        # Returns i18n key for "Folder"
        assert "folder" in result.lower() or "dir" in result.lower()

    def test_file_type_file(self):
        """file_type should detect files correctly."""
        from hpc_gui.ui.models.remote_entry_helpers import file_type

        result = file_type("test.txt", is_dir=False)
        assert result != "Folder"

    def test_file_type_unicode_name(self):
        """file_type should handle Unicode names."""
        from hpc_gui.ui.models.remote_entry_helpers import file_type

        result = file_type("日本語.txt", is_dir=False)
        assert result, "file_type should return a non-empty string"


# ---------------------------------------------------------------------------
# 10. Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for Unicode remote operations."""

    def test_unicode_listing_roundtrip(self):
        """Unicode names should survive listing roundtrip."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        # Create Unicode entries
        for name in ALL_REMOTE_NAMES:
            path = f"/work/{name}"
            if "." in name:
                backend._files[path] = f"content of {name}".encode("utf-8")
            else:
                backend._dirs.add(path)

        # List entries
        entries = backend.listdir("/work")

        # Verify all names preserved
        for name in ALL_REMOTE_NAMES:
            assert name in entries, f"Name {name!r} missing"

    def test_unicode_crud_operations(self):
        """CRUD operations should preserve Unicode names."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        # Create
        backend.mkdir("/work/研究")
        assert backend.is_dir("/work/研究")

        # Write
        backend.write_text("/work/研究/結果.txt", "完了")
        assert backend.read_text("/work/研究/結果.txt") == "完了"

        # Rename
        backend.rename("/work/研究/結果.txt", "/work/研究/最終結果.txt")
        assert backend.read_text("/work/研究/最終結果.txt") == "完了"

        # List
        entries = backend.listdir("/work/研究")
        assert "最終結果.txt" in entries

        # Remove
        backend.remove("/work/研究/最終結果.txt")
        entries = backend.listdir("/work/研究")
        assert len(entries) == 0
