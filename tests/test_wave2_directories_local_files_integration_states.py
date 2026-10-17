"""Wave 2 — Directories / Local Files Feature Parity and Unicode.

Make the new Directories local pane genuinely usable, including context menus,
pane operations, clear ergonomics, and full Unicode-safe wx→filesystem→UI
integration.
"""

from __future__ import annotations
from support.test_wave2_directories_local_files_shared import (
    ALL_UNICODE_NAMES,
    pathlib,
    pytest,
    sys,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

class TestIntegration:
    """Integration tests for Unicode local file operations."""

    @pytest.mark.integration
    def test_full_workflow_unicode(self, tmp_path):
        """Full workflow: create, list, rename, copy, delete with Unicode names."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # 1. Create directories
        model.new_folder("İşler")
        model.new_folder("研究")
        assert (tmp_path / "İşler").is_dir()
        assert (tmp_path / "研究").is_dir()

        # 2. Create files
        (tmp_path / "İşler" / "sonuç.txt").write_text("sonuç", encoding="utf-8")
        (tmp_path / "研究" / "計算結果.txt").write_text("結果", encoding="utf-8")

        # 3. List entries
        entries = model.list_entries()
        names = [entry.path.name for entry in entries]
        assert "İşler" in names
        assert "研究" in names

        # 4. Navigate into directory
        model.navigate(tmp_path / "İşler")
        entries = model.list_entries()
        names = [entry.path.name for entry in entries]
        assert "sonuç.txt" in names

        # 5. Rename
        model.rename(
            tmp_path / "İşler" / "sonuç.txt",
            "ölçüm.txt"
        )
        assert (tmp_path / "İşler" / "ölçüm.txt").exists()

        # 6. Copy
        model.copy([tmp_path / "İşler" / "ölçüm.txt"], move=False)
        model.paste_into(tmp_path / "研究", model.clipboard, move=False)
        assert (tmp_path / "研究" / "ölçüm.txt").exists()

        # 7. Delete
        model.delete([tmp_path / "İşler" / "ölçüm.txt"])
        assert not (tmp_path / "İşler" / "ölçüm.txt").exists()

        # 8. Navigate back
        model.parent()
        assert model.current_path.resolve() == tmp_path.resolve()

    @pytest.mark.unit
    def test_unicode_directory_listing(self, tmp_path):
        """Listing a directory with many Unicode names should work."""
        from hpc_gui.services.local_files import list_local_entries

        # Create many Unicode-named files
        for name in ALL_UNICODE_NAMES:
            p = tmp_path / name
            if "." in name:
                p.write_text("test", encoding="utf-8")
            else:
                p.mkdir(exist_ok=True)

        # List should return all entries
        entries = list_local_entries(str(tmp_path))
        assert len(entries) == len(ALL_UNICODE_NAMES)

        # All names should be preserved
        entry_names = {e.name for e in entries}
        for name in ALL_UNICODE_NAMES:
            assert name in entry_names, f"Name {name!r} missing from listing"

class TestErrorHandling:
    pytestmark = pytest.mark.unit

    """Verify error handling for edge cases."""

    def test_list_entries_permission_error(self, tmp_path, monkeypatch):
        """list_entries should handle permission errors gracefully."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create a file and a directory
        (tmp_path / "file.txt").write_text("test", encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        denied = tmp_path / "denied.txt"
        denied.write_text("secret", encoding="utf-8")

        original_stat = pathlib.Path.stat
        denied_stat_calls = []

        def permission_denied(path, *args, **kwargs):
            if path == denied:
                denied_stat_calls.append(path)
                raise PermissionError("metadata access denied")
            return original_stat(path, *args, **kwargs)

        monkeypatch.setattr(pathlib.Path, "stat", permission_denied)
        entries = model.list_entries()

        by_name = {entry.path.name: entry for entry in entries}
        assert by_name["file.txt"].size == 4
        assert by_name["subdir"].is_dir
        assert by_name["denied.txt"].size == 0
        assert not by_name["denied.txt"].is_dir
        assert denied_stat_calls == [denied]

    def test_navigate_nonexistent_directory(self, tmp_path):
        """navigate should raise NotADirectoryError for non-existent paths."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        with pytest.raises(NotADirectoryError):
            model.navigate(tmp_path / "nonexistent")

    def test_navigate_file_not_directory(self, tmp_path):
        """navigate should raise NotADirectoryError for files."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create a file
        test_file = tmp_path / "file.txt"
        test_file.write_text("test", encoding="utf-8")

        with pytest.raises(NotADirectoryError):
            model.navigate(test_file)

    def test_rename_invalid_name(self, tmp_path):
        """rename should raise ValueError for invalid names."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test", encoding="utf-8")

        # Try to rename with invalid names
        with pytest.raises(ValueError):
            model.rename(test_file, "")  # Empty name

        with pytest.raises(ValueError):
            model.rename(test_file, "path/separator")  # Path separator

    def test_delete_nonexistent_file(self, tmp_path):
        """delete should handle non-existent files gracefully."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # delete should not crash on non-existent files
        # (it silently skips them)
        result = model.delete([tmp_path / "nonexistent.txt"])
        # Result should be empty tuple (no files deleted)
        assert result == ()

class TestEmptyLoadingErrorStates:
    pytestmark = pytest.mark.unit

    """Verify empty, loading, and error states."""

    def test_empty_directory(self, tmp_path):
        """Empty directory should return empty tuple."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        entries = model.list_entries()
        assert entries == ()

    def test_single_file_directory(self, tmp_path):
        """Directory with single file should return one entry."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        (tmp_path / "file.txt").write_text("test", encoding="utf-8")

        entries = model.list_entries()
        assert len(entries) == 1
        assert entries[0].path.name == "file.txt"

    def test_directories_before_files(self, tmp_path):
        """Directories should be listed before files."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files and directories
        (tmp_path / "file1.txt").write_text("test", encoding="utf-8")
        (tmp_path / "dir1").mkdir()
        (tmp_path / "file2.txt").write_text("test", encoding="utf-8")
        (tmp_path / "dir2").mkdir()

        entries = model.list_entries()
        # First two should be directories
        assert entries[0].is_dir is True
        assert entries[1].is_dir is True
        # Last two should be files
        assert entries[2].is_dir is False
        assert entries[3].is_dir is False

class TestConflictHandling:
    pytestmark = pytest.mark.unit

    """Verify conflict handling during file operations."""

    def test_rename_conflict(self, tmp_path):
        """rename should raise FileExistsError if target exists."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create two files
        (tmp_path / "file1.txt").write_text("test1", encoding="utf-8")
        (tmp_path / "file2.txt").write_text("test2", encoding="utf-8")

        # Try to rename file1 to file2 (should fail)
        with pytest.raises(FileExistsError):
            model.rename(tmp_path / "file1.txt", "file2.txt")

    def test_paste_conflict(self, tmp_path):
        """paste_into should handle conflicts by raising FileExistsError."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source and destination directories
        src_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        src_dir.mkdir()
        dest_dir.mkdir()

        # Create file in both locations
        (src_dir / "file.txt").write_text("source", encoding="utf-8")
        (dest_dir / "file.txt").write_text("dest", encoding="utf-8")

        # Copy source file
        model.copy([src_dir / "file.txt"], move=False)

        # Try to paste into destination (should fail because file exists)
        with pytest.raises(FileExistsError):
            model.paste_into(dest_dir, model.clipboard, move=False)
