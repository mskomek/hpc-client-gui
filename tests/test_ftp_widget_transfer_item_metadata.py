"""Focused FTP widget tests split by transfer responsibility."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from hpc_gui.ui.dialogs.transfer_dialog import TransferItem
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel, _PlannedOp
from ftp_widget_test_support import FtpWidgetTestCase, _CountingFiles


class FtpWidgetTransferItemMetadataTests(FtpWidgetTestCase):
    @pytest.mark.unit
    def test_transfer_item_trailing_cached_size_keeps_positional_construction(self) -> None:
        plain = TransferItem("download", "/remote/a.txt", "a.txt")
        self.assertIsNone(plain.cached_size)
        self.assertFalse(plain.recursive)
        self.assertEqual(plain.priority, "Normal")

        sized = TransferItem("upload", "local.bin", "/remote/local.bin", False, "High", 2048)
        self.assertEqual(sized.cached_size, 2048)
        self.assertEqual(sized.priority, "High")

        keyword = TransferItem("download", "/remote/b.bin", "b.bin", cached_size=777)
        self.assertEqual(keyword.cached_size, 777)

    @pytest.mark.unit
    def test_transfer_item_size_prefers_cached_size_without_repeat_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.bin"
            source.write_bytes(b"x" * 512)
            item = TransferItem(
                "upload",
                str(source),
                "/remote/data.bin",
                cached_size=128,
            )
            with patch(
                "pathlib.Path.stat",
                side_effect=AssertionError("cached size must avoid a stat"),
            ):
                self.assertEqual(
                    self.widget.transfer_activity._item_size(item),
                    128,
                )

    @pytest.mark.unit
    def test_transfer_item_size_falls_back_to_stat_when_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "data.bin"
            source.write_bytes(b"x" * 333)
            item = TransferItem("upload", str(source), "/remote/data.bin")
            self.assertEqual(self.widget.transfer_activity._item_size(item), 333)

    @pytest.mark.integration
    def test_download_plan_carries_listed_remote_size(self) -> None:
        files = _CountingFiles()
        panel = self.widget.panel_scratch
        panel.session = {"connected": True, "files": files}
        with tempfile.TemporaryDirectory() as tmp:
            result = panel._build_remote_download_plan_background(
                SimpleNamespace(cancelled=False),
                files,
                ["/remote"],
                tmp,
            )
        plan = result.get("plan") or []
        transfers = [op for op in plan if op.op == "download"]
        sizes = {op.src: op.size for op in transfers}
        self.assertEqual(sizes.get("/remote/root.txt"), 4)
        self.assertEqual(sizes.get("/remote/child/nested.txt"), 6)
        self.assertNotIn("/remote/child", sizes)

    @pytest.mark.unit
    def test_transfer_items_from_plan_preserve_known_size_and_leave_unknown_none(self) -> None:
        plan = [
            _PlannedOp("download", "/remote/a.bin", "a.bin", size=4096),
            _PlannedOp("upload", "local.txt", "/remote/local.txt"),
            _PlannedOp("mkdir_local", "", r"D:\target\folder"),
        ]
        items = RemoteDirPanel._transfer_items_from_plan(plan)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].cached_size, 4096)
        self.assertIsNone(items[1].cached_size)
        self.assertIsNone(items[2].cached_size)
