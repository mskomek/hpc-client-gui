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


class TestForwardNavigation:
    pytestmark = pytest.mark.unit

    """Verify forward navigation works correctly."""

    def test_forward_navigation_basic(self, tmp_path):
        """Forward navigation should work after back navigation."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create directories
        dir_a = tmp_path / "A"
        dir_b = tmp_path / "B"
        dir_a.mkdir()
        dir_b.mkdir()

        # Navigate: A → B
        model.navigate(dir_a)
        model.navigate(dir_b)

        # Go back: B → A
        model.go_back()
        assert model.current_path.resolve() == dir_a.resolve()

        # Go forward: A → B
        model.go_forward()
        assert model.current_path.resolve() == dir_b.resolve()

    def test_forward_cleared_on_new_navigation(self, tmp_path):
        """Forward history should be cleared when navigating to a new path."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Create directories
        dir_a = tmp_path / "A"
        dir_b = tmp_path / "B"
        dir_c = tmp_path / "C"
        dir_a.mkdir()
        dir_b.mkdir()
        dir_c.mkdir()

        # Navigate: A → B → C
        model.navigate(dir_a)
        model.navigate(dir_b)
        model.navigate(dir_c)

        # Go back twice: C → B → A
        model.go_back()
        model.go_back()

        # Navigate to C (new path, should clear forward)
        model.navigate(dir_c)

        # Forward should be empty
        assert not model.can_go_forward()

    def test_can_go_forward(self, tmp_path):
        """can_go_forward should return correct state."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # Initially no forward history
        assert not model.can_go_forward()

        # Create directories
        dir_a = tmp_path / "A"
        dir_b = tmp_path / "B"
        dir_a.mkdir()
        dir_b.mkdir()

        # Navigate and go back
        model.navigate(dir_a)
        model.navigate(dir_b)
        model.go_back()

        # Now should have forward history
        assert model.can_go_forward()

    def test_forward_raises_on_empty(self, tmp_path):
        """go_forward should raise IndexError when no forward history."""
        from hpc_gui.wx_local_files import LocalBrowserModel

        model = LocalBrowserModel(tmp_path)

        # No forward history
        with pytest.raises(IndexError):
            model.go_forward()
