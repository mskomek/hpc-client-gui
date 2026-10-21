"""Wave 2 — Directories / Local Files Feature Parity and Unicode.

Make the new Directories local pane genuinely usable, including context menus,
pane operations, clear ergonomics, and full Unicode-safe wx→filesystem→UI
integration.
"""

from __future__ import annotations

import pathlib

import pytest

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
