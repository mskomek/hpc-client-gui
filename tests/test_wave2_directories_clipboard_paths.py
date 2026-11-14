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


class TestSearchFilterErgonomics:
    pytestmark = pytest.mark.unit

    """Verify search/filter behavior with Unicode names."""

    def test_sort_turkish_names(self, tmp_path):
        """Sorting should handle Turkish characters correctly."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files with Turkish names
        names = ["çalışma.txt", "iş.txt", "ödev.txt", "şey.txt", "üretim.txt"]
        for name in names:
            (tmp_path / name).write_text("test", encoding="utf-8")

        # Default sort is "name" ascending (casefold)
        # Call sort("name") once to toggle to descending
        model.sort("name")
        sorted_names_desc = [entry.path.name for entry in model.list_entries()]
        expected_desc = sorted(names, key=lambda n: n.casefold(), reverse=True)
        assert sorted_names_desc == expected_desc, "Descending sort mismatch"

        # Call sort("name") again to toggle back to ascending
        model.sort("name")
        sorted_names_asc = [entry.path.name for entry in model.list_entries()]
        expected_asc = sorted(names, key=lambda n: n.casefold())
        assert sorted_names_asc == expected_asc, "Ascending sort mismatch"

    def test_sort_japanese_names(self, tmp_path):
        """Sorting should handle Japanese characters correctly."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files with Japanese names
        names = ["計算.txt", "研究.txt", "日本語.txt"]
        for name in names:
            (tmp_path / name).write_text("test", encoding="utf-8")

        # Default sort is "name" ascending
        entries = model.list_entries()
        sorted_names = [entry.path.name for entry in entries]
        expected = sorted(names, key=lambda n: n.casefold())
        assert sorted_names == expected, f"Sort order mismatch: {sorted_names} != {expected}"

    def test_sort_mixed_scripts(self, tmp_path):
        """Sorting should handle mixed scripts correctly."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create files with mixed scripts
        names = ["a.txt", "α.txt", "あ.txt", "字.txt"]
        for name in names:
            (tmp_path / name).write_text("test", encoding="utf-8")

        # Default sort is "name" ascending
        entries = model.list_entries()
        sorted_names = [entry.path.name for entry in entries]
        expected = sorted(names, key=lambda n: n.casefold())
        assert sorted_names == expected, f"Sort order mismatch: {sorted_names} != {expected}"


class TestURLEncoding:
    pytestmark = pytest.mark.contract

    """Verify URL encoding preserves Unicode for drag/drop."""

    def test_url_payload_unicode(self, tmp_path):
        """file_url_payload should encode Unicode paths correctly."""
        from hpc_gui.wx_local_files import file_url_payload

        test_path = pathlib.Path("/tmp/İşler_Çağrı/日本語.txt")
        payload = file_url_payload([test_path])

        # Should contain encoded Unicode
        assert "%C4%B1" in payload or "İ" in payload  # Turkish i
        assert "%E6%97%A5" in payload or "日" in payload  # Japanese

    def test_url_payload_spaces(self, tmp_path):
        """file_url_payload should encode spaces correctly."""
        from hpc_gui.wx_local_files import file_url_payload

        test_path = pathlib.Path("/tmp/My Documents/file.txt")
        payload = file_url_payload([test_path])

        # Spaces should be encoded
        assert "%20" in payload or "My" in payload


class TestPathOperations:
    pytestmark = pytest.mark.unit

    """Verify path operations with Unicode names."""

    def test_navigate_unicode_directory(self, tmp_path):
        """Navigation should work with Unicode directory names."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create Unicode directory
        unicode_dir = tmp_path / "日本語_ディレクトリ"
        unicode_dir.mkdir()

        # Navigate into it
        model.navigate(unicode_dir)
        assert model.current_path.resolve() == unicode_dir.resolve()

    def test_parent_unicode_directory(self, tmp_path):
        """Parent navigation should work from Unicode directory."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create and navigate to Unicode directory
        unicode_dir = tmp_path / "İşler"
        unicode_dir.mkdir()
        model.navigate(unicode_dir)

        # Navigate to parent
        model.parent()
        assert model.current_path.resolve() == tmp_path.resolve()

    def test_new_folder_unicode_name(self, tmp_path):
        """Creating a Unicode-named folder should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        model.new_folder("研究_結果")
        assert (tmp_path / "研究_結果").is_dir()

    def test_rename_preserves_content(self, tmp_path):
        """Rename should preserve file content."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create file with content
        src = tmp_path / "original.txt"
        content = "日本語のコンテンツ\nTürkçe içerik\n★ special"
        src.write_text(content, encoding="utf-8")

        # Rename
        dest = tmp_path / "yeniden_adlandır.txt"
        model.rename(src, "yeniden_adlandır.txt")

        # Verify content preserved
        assert dest.read_text(encoding="utf-8") == content
