from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.services.files_base import RemoteEntry  # noqa: E402
from hpc_gui.ui.models import remote_entry_helpers as helpers  # noqa: E402


class FmtSizeTests(unittest.TestCase):
    def test_formats_bytes_without_decimals(self) -> None:
        self.assertEqual(helpers.fmt_size(0), "0 B")
        self.assertEqual(helpers.fmt_size(1023), "1023 B")

    def test_formats_higher_units_with_one_decimal(self) -> None:
        self.assertEqual(helpers.fmt_size(1024), "1.0 KB")
        self.assertEqual(helpers.fmt_size(1536), "1.5 KB")
        self.assertEqual(helpers.fmt_size(1024**3), "1.0 GB")

    def test_caps_at_the_largest_unit(self) -> None:
        self.assertEqual(helpers.fmt_size(1024**4 * 8), "8.0 TB")
        self.assertEqual(helpers.fmt_size(1024**5 * 8), "8192.0 TB")

    def test_non_numeric_input_yields_empty_string(self) -> None:
        self.assertEqual(helpers.fmt_size("bad"), "")


class FileTypeTests(unittest.TestCase):
    def test_directories_use_translated_folder_label(self) -> None:
        self.assertEqual(helpers.file_type("anything", True), "Klasör")

    def test_known_extensions_map_to_descriptions(self) -> None:
        self.assertEqual(helpers.file_type("a.ISO", False), "Disc Image File")
        self.assertEqual(helpers.file_type("b.zip", False), "WinRAR ZIP archive")
        self.assertEqual(helpers.file_type("c.tar.gz", False), "TAR archive")

    def test_unknown_extension_uppercases_the_suffix(self) -> None:
        self.assertEqual(helpers.file_type("data.CsV", False), "CSV File")
        self.assertEqual(helpers.file_type("README", False), "File")


class CategoryTests(unittest.TestCase):
    def test_entries_are_bucketed_by_kind(self) -> None:
        def entry(name: str, is_dir: bool = False) -> RemoteEntry:
            return RemoteEntry(name=name, path=f"/work/{name}", is_dir=is_dir, size=1, mtime=1)

        self.assertEqual(helpers.category(entry("d", is_dir=True)), "folders")
        self.assertEqual(helpers.category(entry("x.iso")), "iso")
        self.assertEqual(helpers.category(entry("y.tgz")), "archives")
        self.assertEqual(helpers.category(entry("run.sh")), "shell")
        self.assertEqual(helpers.category(entry("job.slurm")), "slurm")
        self.assertEqual(helpers.category(entry("notes.txt")), "other")


class NaturalSortKeyTests(unittest.TestCase):
    def test_numeric_runs_sort_numerically(self) -> None:
        names = ["entry10", "entry2", "entry1"]
        self.assertEqual(sorted(names, key=helpers.natural_sort_key), ["entry1", "entry2", "entry10"])

    def test_case_is_folded(self) -> None:
        self.assertEqual(
            sorted(["BETA", "alpha"], key=helpers.natural_sort_key),
            ["alpha", "BETA"],
        )

    def test_empty_and_none_like_values_are_safe(self) -> None:
        self.assertEqual(helpers.natural_sort_key(""), ())


if __name__ == "__main__":
    unittest.main()
