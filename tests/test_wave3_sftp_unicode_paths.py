"""SFTP Unicode paths and safe editable-text decoding contracts."""

from __future__ import annotations

import io
import pytest

class TestSFTPUnicodePaths:
    """Verify SFTP operations handle Unicode paths correctly."""

    pytestmark = [pytest.mark.unit, pytest.mark.semantic]

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

    @pytest.mark.regression
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
            backend.read_text_for_edit("/work/legacy.txt")

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
