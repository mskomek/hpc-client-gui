"""Wave 2 — Directories / Local Files Feature Parity and Unicode.

Make the new Directories local pane genuinely usable, including context menus,
pane operations, clear ergonomics, and full Unicode-safe wx→filesystem→UI
integration.
"""

from __future__ import annotations

import pytest

class TestClipboardOperations:
    """Verify clipboard operations preserve Unicode."""

    @pytest.mark.unit
    def test_copy_paste_unicode_file(self, tmp_path):
        """Copy/paste should preserve Unicode file names."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source file
        src = tmp_path / "source" / "日本語_ファイル.txt"
        src.parent.mkdir()
        src.write_text("content", encoding="utf-8")

        # Copy to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        model.copy([src], move=False)
        model.paste_into(dest_dir, model.clipboard, move=False)

        dest_file = dest_dir / "日本語_ファイル.txt"
        assert dest_file.exists()
        assert dest_file.read_text(encoding="utf-8") == "content"

    @pytest.mark.unit
    def test_cut_paste_unicode_file(self, tmp_path):
        """Cut/paste should preserve Unicode file names and remove source."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source file
        src = tmp_path / "source" / "İşler_Çağrı.txt"
        src.parent.mkdir()
        src.write_text("content", encoding="utf-8")

        # Cut to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        model.copy([src], move=True)
        model.paste_into(dest_dir, model.clipboard, move=True)

        dest_file = dest_dir / "İşler_Çağrı.txt"
        assert dest_file.exists()
        assert dest_file.read_text(encoding="utf-8") == "content"
        assert not src.exists()

    @pytest.mark.unit
    def test_copy_paste_multiple_unicode_files(self, tmp_path):
        """Copy/paste multiple Unicode files should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create source files
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        files = ["日本語.txt", "Türkçe.txt", "★.txt"]
        for name in files:
            (src_dir / name).write_text("test", encoding="utf-8")

        # Copy all to destination
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        src_paths = [src_dir / name for name in files]
        model.copy(src_paths, move=False)
        model.paste_into(dest_dir, model.clipboard, move=False)

        for name in files:
            assert (dest_dir / name).exists(), f"File {name!r} not pasted"

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_paste_directory_into_itself_is_rejected(self, tmp_path):
        """Pasting a directory into itself must not create recursive copies."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)
        source = tmp_path / "source"
        source.mkdir()
        (source / "payload.txt").write_text("content", encoding="utf-8")
        model.copy([source], move=False)

        with pytest.raises(ValueError, match="cannot paste a directory into itself"):
            model.paste_into(source, model.clipboard, move=False)

        assert (source / "payload.txt").read_text(encoding="utf-8") == "content"
        assert not (source / "source").exists()

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
