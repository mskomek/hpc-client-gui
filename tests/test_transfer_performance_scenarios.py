from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from truba_gui.core.i18n import load_language
from truba_gui.ui.dialogs.transfer_dialog import TransferDialog, TransferItem
from truba_gui.ui.widgets.ftp_widget import TransferActivityPanel


def _load_performance_probe():
    path = Path(__file__).resolve().parents[1] / "devtools" / "performance_probe.py"
    spec = importlib.util.spec_from_file_location("performance_probe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("performance probe could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TransferPerformanceScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        load_language("en")

    @staticmethod
    def _items(count: int) -> list[TransferItem]:
        return [
            TransferItem("upload", f"local-{index}.dat", f"remote-{index}.dat", cached_size=1)
            for index in range(count)
        ]

    def test_queue_sizes_keep_visible_rows_bounded(self) -> None:
        panel = TransferActivityPanel()
        for count in (100, 1000, 10000):
            with self.subTest(count=count):
                panel.record("queued", self._items(count))
                self.assertLessEqual(panel.queue_list.topLevelItemCount(), 501)
                self.assertLessEqual(len(panel._row_by_item_id), 500)
                self.assertLessEqual(len(panel._progress_bar_by_item_id), 500)

    def test_render_probe_records_no_slow_deterministic_ticks(self) -> None:
        probe = _load_performance_probe()
        with tempfile.TemporaryDirectory() as temp_dir:
            session = probe.PerformanceSession(
                Path(temp_dir), interval_ms=100, slow_ms=500, now=lambda: 0.0
            )
            session.start()
            session._expected_tick = 0.1
            panel = TransferActivityPanel()
            panel.record("queued", self._items(10000))
            for observed in (0.1, 0.2, 0.3):
                session.measure_tick(observed)
            session.finish(0)
            events = [
                json.loads(line)
                for line in session.report_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertFalse([event for event in events if event["event"] == "event_loop_delay"])
            self.assertLessEqual(panel.queue_list.topLevelItemCount(), 501)

    def test_burst_progress_throttles_and_publishes_final_update(self) -> None:
        item = self._items(1)[0]
        dialog = TransferDialog(title="test", items=[item], run_item=lambda _item: None)
        published: list[tuple[int, int]] = []
        dialog.transferProgressChanged.connect(
            lambda _item, done, total: published.append((done, total))
        )
        with patch(
            "truba_gui.ui.dialogs.transfer_dialog.time.monotonic",
            side_effect=[0.0] + [0.001] * 999,
        ):
            for done in range(1, 1001):
                dialog._on_transfer_progress(item, done, 1000)
        self.assertEqual(published, [(1, 1000), (1000, 1000)])

    def test_four_fake_transfers_finish_without_network(self) -> None:
        items = self._items(4)
        dialog = TransferDialog(
            title="test",
            items=items,
            run_item=lambda _item, progress=None: progress(1, 1) if progress else None,
            parallel_limit=4,
        )
        dialog.start()
        deadline = time.monotonic() + 3
        while not dialog.finished_cleanly() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertTrue(dialog.finished_cleanly())
        self.assertEqual(len(dialog._completed), 4)


if __name__ == "__main__":
    unittest.main()
