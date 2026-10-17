"""Wave 2 — Directories / Local Files Feature Parity and Unicode.

Make the new Directories local pane genuinely usable, including context menus,
pane operations, clear ergonomics, and full Unicode-safe wx→filesystem→UI
integration.
"""

from __future__ import annotations
from support.test_wave2_directories_local_files_shared import (
    pathlib,
    pytest,
    sys,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

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
