"""Wave 2 — Directories / Local Files Feature Parity and Unicode.

Make the new Directories local pane genuinely usable, including context menus,
pane operations, clear ergonomics, and full Unicode-safe wx→filesystem→UI
integration.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Golden Fixtures — Unicode file names for testing
# ---------------------------------------------------------------------------

TURKISH_NAMES = [
    "İşler_Çağrı_Ölçüm",
    "Isı_İstanbul_Şehir",
    "Üniversite_Kümesi",
    "çalışma.txt",
    "şğüöçıİ.dat",
    "Ölçüm_Sonucu.txt",
    "O'Brien_Çalışma.txt",
]

JAPANESE_NAMES = [
    "研究_ジョブ",
    "計算_結果",
    "日本語_ディレクトリ",
    "日本語_計算結果.txt",
    "ジョブ結果.slurm",
    "研究_スクリプト.sh",
]

MIXED_NAMES = [
    "Türkçe_日本語",
    "iş_日本語_δ.txt",
    "Çalışma_Sonucu_日本語.txt",
]

SYMBOL_NAMES = [
    "★_Favorites.txt",
    "ΔPressure_ölçüm.txt",
    "🚀_job.txt",
]

ALL_UNICODE_NAMES = TURKISH_NAMES + JAPANESE_NAMES + MIXED_NAMES + SYMBOL_NAMES


# ---------------------------------------------------------------------------
# 1. Directory Listing/Navigation
# ---------------------------------------------------------------------------


class TestSearchFilter:
    pytestmark = pytest.mark.unit

    """Verify search/filter functionality with Unicode names."""

    def test_search_turkish_names(self, tmp_path):
        """Search should find Turkish names with case-insensitive match."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files with Turkish names
        (tmp_path / "çalışma.txt").write_text("test", encoding="utf-8")
        (tmp_path / "iş.txt").write_text("test", encoding="utf-8")
        (tmp_path / "ödev.txt").write_text("test", encoding="utf-8")

        # Search for "çalış"
        results = model.search("çalış")
        names = [e.path.name for e in results]
        assert "çalışma.txt" in names
        assert "iş.txt" not in names

    def test_search_japanese_names(self, tmp_path):
        """Search should find Japanese names with substring match."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files with Japanese names
        (tmp_path / "日本語.txt").write_text("test", encoding="utf-8")
        (tmp_path / "計算.txt").write_text("test", encoding="utf-8")
        (tmp_path / "研究.txt").write_text("test", encoding="utf-8")

        # Search for "日本"
        results = model.search("日本")
        names = [e.path.name for e in results]
        assert "日本語.txt" in names
        assert "計算.txt" not in names

    def test_search_case_insensitive(self, tmp_path):
        """Search should be case-insensitive."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create file
        (tmp_path / "README.txt").write_text("test", encoding="utf-8")

        # Search with different cases
        results_lower = model.search("readme")
        results_upper = model.search("README")
        results_mixed = model.search("ReAdMe")

        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1

    def test_search_no_results(self, tmp_path):
        """Search with no matches should return empty tuple."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create file
        (tmp_path / "test.txt").write_text("test", encoding="utf-8")

        # Search for non-existent pattern
        results = model.search("nonexistent")
        assert results == ()

    def test_search_empty_query(self, tmp_path):
        """Search with empty query should return all entries."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files
        (tmp_path / "a.txt").write_text("test", encoding="utf-8")
        (tmp_path / "b.txt").write_text("test", encoding="utf-8")

        # Search with empty query
        results = model.search("")
        assert len(results) == 2


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
