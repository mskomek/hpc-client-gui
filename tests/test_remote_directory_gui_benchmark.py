from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import benchmark_remote_directory_gui  # noqa: E402


class RemoteDirectoryGuiBenchmarkGate(unittest.TestCase):
    def test_small_offscreen_listing_is_exact_and_terminates(self) -> None:
        app = QApplication.instance() or QApplication([])
        started = time.perf_counter()
        timings = benchmark_remote_directory_gui._measure(app, 120, timeout=30.0)
        elapsed = time.perf_counter() - started

        self.assertEqual(timings["rows"], 120)
        self.assertGreater(timings["first_batch_ms"], 0)
        self.assertGreater(timings["first_row_ms"], 0)
        self.assertLess(elapsed, 30.0)


if __name__ == "__main__":
    unittest.main()
