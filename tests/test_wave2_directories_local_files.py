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


class TestDirectoryListingNavigation:
    pytestmark = pytest.mark.unit

    """Verify directory listing and navigation with Unicode names."""

    def test_list_entries_returns_unicode_names(self, tmp_path):
        """list_local_entries should return Unicode file names correctly."""
        from hpc_gui.services.local_files import list_local_entries

        # Create Unicode-named files and directories
        for name in ALL_UNICODE_NAMES:
            p = tmp_path / name
            if "." in name:
                p.write_text("test", encoding="utf-8")
            else:
                p.mkdir(exist_ok=True)

        entries = list_local_entries(str(tmp_path))
        names = [e.name for e in entries]

        # Verify all names are present
        for name in ALL_UNICODE_NAMES:
            assert name in names, f"Unicode name {name!r} not found in listing"

    def test_list_entries_preserves_path(self, tmp_path):
        """list_local_entries should preserve full Unicode paths."""
        from hpc_gui.services.local_files import list_local_entries

        test_file = tmp_path / "日本語_テスト.txt"
        test_file.write_text("content", encoding="utf-8")

        entries = list_local_entries(str(tmp_path))
        assert len(entries) == 1
        assert entries[0].name == "日本語_テスト.txt"
        assert "日本語_テスト.txt" in entries[0].path

    def test_list_entries_sorts_unicode_names(self, tmp_path):
        """list_local_entries should sort Unicode names correctly."""
        from hpc_gui.services.local_files import list_local_entries

        # Create files with Turkish characters
        names = ["çalışma.txt", "iş.txt", "ödev.txt", "şey.txt", "üretim.txt"]
        for name in names:
            (tmp_path / name).write_text("test", encoding="utf-8")

        entries = list_local_entries(str(tmp_path))
        entry_names = [e.name for e in entries]

        # Should be sorted by casefold()
        expected = sorted(names, key=lambda n: n.casefold())
        assert entry_names == expected

    def test_list_entries_dirs_first(self, tmp_path):
        """list_local_entries should list directories before files."""
        from hpc_gui.services.local_files import list_local_entries

        (tmp_path / "α_file.txt").write_text("test", encoding="utf-8")
        (tmp_path / "β_dir").mkdir()
        (tmp_path / "γ_file.txt").write_text("test", encoding="utf-8")

        entries = list_local_entries(str(tmp_path))
        assert entries[0].is_dir is True
        assert entries[1].is_dir is False
        assert entries[2].is_dir is False

    def test_safe_initial_directory_unicode(self, tmp_path):
        """safe_initial_local_directory should handle Unicode paths."""
        from hpc_gui.services.local_files import safe_initial_local_directory

        unicode_dir = tmp_path / "日本語_ディレクトリ"
        unicode_dir.mkdir()

        result = safe_initial_local_directory(str(unicode_dir))
        assert pathlib.Path(result).resolve() == unicode_dir.resolve()


class TestCRUDActions:
    pytestmark = pytest.mark.unit

    """Verify file operations with Unicode paths."""

    def test_create_directory_unicode(self, tmp_path):
        """Creating a Unicode-named directory should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)
        model.new_folder("İşler_Çağrı")

        target = tmp_path / "İşler_Çağrı"
        assert target.is_dir()

    def test_create_file_unicode(self, tmp_path):
        """Creating a Unicode-named file should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)
        # Create directory first
        model.new_folder("研究")
        target_dir = tmp_path / "研究"

        # Create file inside
        test_file = target_dir / "計算結果.txt"
        test_file.write_text("content", encoding="utf-8")
        assert test_file.exists()

    def test_rename_unicode_roundtrip(self, tmp_path):
        """Rename should preserve Unicode names through roundtrip."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create initial file
        initial = tmp_path / "result.txt"
        initial.write_text("test", encoding="utf-8")

        # Rename chain: result.txt → sonuç.txt → ölçüm_日本語.txt → 研究_İstanbul.txt → result.txt
        rename_chain = [
            "sonuç.txt",
            "ölçüm_日本語.txt",
            "研究_İstanbul.txt",
            "result.txt",
        ]

        current_name = "result.txt"
        for new_name in rename_chain:
            old_path = tmp_path / current_name
            model.rename(old_path, new_name)
            new_path = tmp_path / new_name
            assert new_path.exists(), f"Rename to {new_name!r} failed"
            assert not old_path.exists(), f"Old file {current_name!r} still exists"
            current_name = new_name

    def test_delete_unicode_file(self, tmp_path):
        """Deleting a Unicode-named file should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create Unicode-named file
        test_file = tmp_path / "★_Favorites.txt"
        test_file.write_text("test", encoding="utf-8")
        assert test_file.exists()

        # Delete it
        model.delete([test_file])
        assert not test_file.exists()

    def test_delete_unicode_directory(self, tmp_path):
        """Deleting a Unicode-named directory should work."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create Unicode-named directory with content
        test_dir = tmp_path / "Türkçe_日本語"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test", encoding="utf-8")

        # Delete it (delete only removes empty dirs, so delete file first)
        model.delete([(test_dir / "file.txt")])
        model.delete([test_dir])
        assert not test_dir.exists()


class TestContextMenus:
    pytestmark = pytest.mark.unit

    """Verify context menus are fully wired with Unicode support."""

    def test_context_actions_for_file(self):
        """Context actions should include expected items for files."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path="/tmp/test.txt",
            clicked_is_dir=False,
            selected_paths=("/tmp/test.txt",),
            selected_types=(False,),
        )
        actions = visible_actions(selection, remote=False)
        assert "open" in actions
        assert "rename" in actions
        assert "copy" in actions
        assert "cut" in actions
        assert "delete" in actions
        assert "copy_path" in actions

    def test_context_actions_for_directory(self):
        """Context actions should include expected items for directories."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path="/tmp/test_dir",
            clicked_is_dir=True,
            selected_paths=("/tmp/test_dir",),
            selected_types=(True,),
        )
        actions = visible_actions(selection, remote=False)
        assert "open" in actions
        assert "new_folder" in actions
        assert "copy" in actions
        assert "cut" in actions
        assert "delete" in actions
        assert "copy_path" in actions

    def test_context_actions_background(self):
        """Context actions for background should include paste and refresh."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path=None,
            clicked_is_dir=None,
            background=True,
        )
        actions = visible_actions(selection, remote=False)
        assert "new_folder" in actions
        assert "paste" in actions
        assert "refresh" in actions

    def test_context_actions_multi_select(self):
        """Context actions for multi-select should include bulk operations."""
        from hpc_gui.services.file_context_actions import visible_actions, context_selection

        selection = context_selection(
            clicked_path="/tmp/a.txt",
            clicked_is_dir=False,
            selected_paths=("/tmp/a.txt", "/tmp/b.txt", "/tmp/c.txt"),
            selected_types=(False, False, False),
        )
        actions = visible_actions(selection, remote=False)
        assert "copy" in actions
        assert "cut" in actions
        assert "delete" in actions
        assert "copy_path" in actions
        # Should NOT include open, rename (single-item only)
        assert "open" not in actions
        assert "rename" not in actions
