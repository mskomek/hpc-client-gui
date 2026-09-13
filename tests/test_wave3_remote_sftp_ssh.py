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


@pytest.fixture(autouse=True)
def _restore_language_after_test():
    from hpc_gui.core.i18n import current_language, load_language

    previous_language = current_language()
    load_language("en")
    try:
        yield
    finally:
        load_language(previous_language)


# ---------------------------------------------------------------------------
# 1. SSH Command Construction Safety
# ---------------------------------------------------------------------------

class TestSSHCommandConstruction:
    """Verify SSH commands are safely constructed with proper quoting."""

    @pytest.mark.contract
    @pytest.mark.semantic
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
        remote_paths = [
            "Çalışmalar/test.txt",
            "日本語/計算結果.txt",
            "Türkçe_日本語/file.txt",
            "O'Brien.txt",
            "file with spaces.txt",
            "file$pecial.txt",
            "file(parentheses).txt",
            "file[brackets].txt",
            "file&ampersand.txt",
            "★_Favorites.txt",
            "/scratch/Çalışma O'Brien/$(touch sentinel).txt",
        ]

        for remote_path in remote_paths:
            backend.remove(remote_path)

        assert commands == [f"rm -f {shlex.quote(path)}" for path in remote_paths]
        assert [shlex.split(command) for command in commands] == [
            ["rm", "-f", path] for path in remote_paths
        ]


# ---------------------------------------------------------------------------
# 2. SFTP Unicode Path Handling
# ---------------------------------------------------------------------------

@pytest.mark.semantic
class TestSFTPUnicodePaths:
    """Verify SFTP operations handle Unicode paths correctly."""

    @pytest.mark.unit
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

    @pytest.mark.unit
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

    @pytest.mark.contract
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

    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_mock_backend_unicode_mkdir(self):
        """Mock backend should create Unicode-named directories."""
        from hpc_gui.services.files_mock import MockFilesBackend

        backend = MockFilesBackend()
        backend._dirs.add("/work")

        backend.mkdir("/work/日本語_ディレクトリ")
        assert backend.is_dir("/work/日本語_ディレクトリ")

    @pytest.mark.unit
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

    @pytest.mark.contract
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

    @pytest.mark.contract
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

    @pytest.mark.unit
    def test_navigate_increments_generation(self):
        """navigate() should increment generation counter."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        req1 = controller.navigate("/work/dir1")
        req2 = controller.navigate("/work/dir2")

        assert req2.generation > req1.generation
        assert req1.path == "/work/dir1"
        assert req2.path == "/work/dir2"

    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_back_navigates_to_previous(self):
        """back() should navigate to previous directory."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        controller.navigate("/work/dir1")
        controller.navigate("/work/dir2")

        req = controller.back()
        assert req.path == "/work/dir1"

    @pytest.mark.unit
    def test_normalize_strips_trailing_slash(self):
        """_normalize should strip trailing slashes."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        assert controller._normalize("/work/dir/") == "/work/dir"
        assert controller._normalize("/work/dir//") == "/work/dir"
        assert controller._normalize("/") == "/"

    @pytest.mark.unit
    def test_normalize_defaults_to_root(self):
        """_normalize should default to '/' for empty/None."""
        from hpc_gui.services.remote_directory_controller import RemoteDirectoryController

        controller = RemoteDirectoryController("/work")
        assert controller._normalize(None) == "/"
        assert controller._normalize("") == "/"


# ---------------------------------------------------------------------------
# 5. Shell Session UTF-8 Decoding
# ---------------------------------------------------------------------------

@pytest.mark.semantic
class TestShellSessionDecoding:
    """Verify shell session handles UTF-8 decoding correctly."""

    @pytest.mark.unit
    def test_incremental_decoder_unicode(self):
        """Incremental decoder should handle Unicode characters."""
        from hpc_gui.ssh.shell_session import InteractiveShellSession

        output = []
        session = InteractiveShellSession(invoke_shell=lambda **_kwargs: None, on_output=output.append)
        text = "İş tamamlandı ✓"
        session.decode_bytes(text.encode("utf-8"), final=True)
        assert "".join(output) == text

    @pytest.mark.unit
    def test_incremental_decoder_split_bytes(self):
        """Incremental decoder should handle split multi-byte sequences."""
        from hpc_gui.ssh.shell_session import InteractiveShellSession

        # Japanese character は (U+540D) is 3 bytes in UTF-8
        text = "日本語"
        encoded = text.encode("utf-8")

        # Split at each byte boundary
        for i in range(1, len(encoded)):
            output = []
            session = InteractiveShellSession(invoke_shell=lambda **_kwargs: None, on_output=output.append)
            session.decode_bytes(encoded[:i])
            session.decode_bytes(encoded[i:], final=True)
            assert "".join(output) == text, f"Split at byte {i} lost output: {output!r}"

    @pytest.mark.unit
    def test_incremental_decoder_emoji(self):
        """Incremental decoder should handle emoji (4-byte UTF-8)."""
        from hpc_gui.ssh.shell_session import InteractiveShellSession

        output = []
        session = InteractiveShellSession(invoke_shell=lambda **_kwargs: None, on_output=output.append)

        text = "🚀_job.txt"
        session.decode_bytes(text.encode("utf-8"), final=True)
        assert "".join(output) == text

    @pytest.mark.unit
    def test_incremental_decoder_turkish_dotless_i(self):
        """Incremental decoder should handle Turkish dotless i."""
        from hpc_gui.ssh.shell_session import InteractiveShellSession

        output = []
        session = InteractiveShellSession(invoke_shell=lambda **_kwargs: None, on_output=output.append)

        # Turkish: İ (U+0130) and ı (U+0131)
        text = "İstanbul_ırmak"
        session.decode_bytes(text.encode("utf-8"), final=True)
        assert "".join(output) == text


# ---------------------------------------------------------------------------
# 6. Unicode File Content Roundtrip
# ---------------------------------------------------------------------------

@pytest.mark.semantic
class TestUnicodeFileContentRoundtrip:
    """Verify file content survives Unicode roundtrip through backends."""

    @pytest.mark.unit
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

    @pytest.mark.unit
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

# ---------------------------------------------------------------------------
# 8. SSH Client Unicode Handling
# ---------------------------------------------------------------------------

class TestSSHClientUnicode:
    """Verify SSH client handles Unicode correctly."""

    @pytest.mark.contract
    @pytest.mark.semantic
    def test_remote_display_decoder_is_explicit_utf8_with_safe_fallback(self):
        """SSH command/banner display output uses an explicit UTF-8 policy."""
        from hpc_gui.ssh.client import _decode_remote_text

        assert _decode_remote_text("çıktı 日本語".encode("utf-8")) == "çıktı 日本語"
        assert _decode_remote_text(b"bad\xff") == "bad\ufffd"

    @pytest.mark.contract
    def test_ssh_client_exists(self):
        """SSHClientWrapper should be importable."""
        from hpc_gui.ssh.client import SSHClientWrapper
        assert SSHClientWrapper is not None

    @pytest.mark.contract
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

    @pytest.mark.unit
    def test_file_type_directory(self):
        """file_type should detect directories correctly."""
        from hpc_gui.ui.models.remote_entry_helpers import file_type

        assert file_type("test", is_dir=True) == "Folder"

    @pytest.mark.unit
    def test_file_type_file(self):
        """file_type should detect files correctly."""
        from hpc_gui.ui.models.remote_entry_helpers import file_type

        assert file_type("test.txt", is_dir=False) == "TXT File"

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_file_type_unicode_name(self):
        """file_type should handle Unicode names."""
        from hpc_gui.ui.models.remote_entry_helpers import file_type

        assert file_type("日本語.txt", is_dir=False) == "TXT File"


# ---------------------------------------------------------------------------
# 10. Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for Unicode remote operations."""

    @pytest.mark.semantic
    @pytest.mark.unit
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

    @pytest.mark.semantic
    @pytest.mark.unit
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
