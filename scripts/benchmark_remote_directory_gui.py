"""Measure offline Qt rendering for progressive remote-directory listings."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.services.files_base import RemoteEntry  # noqa: E402
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel  # noqa: E402


class _BenchmarkFiles:
    supports_progressive_listing = True

    def __init__(self, count: int) -> None:
        self.entries = [
            RemoteEntry(
                name=f"{'folder' if index % 3 == 0 else 'entry'}-{index:05d}",
                path=f"/work/entry-{index:05d}",
                is_dir=index % 3 == 0,
                size=index * 1024,
                mtime=1_700_000_000 + index,
            )
            for index in range(count)
        ]

    def iterdir_entries(self, _path: str):
        yield from self.entries


def _measure(app: QApplication, count: int, timeout: float) -> dict[str, float | int]:
    files = _BenchmarkFiles(count)
    panel = RemoteDirPanel()
    panel.set_session({"connected": True, "files": files})
    timings: dict[str, float | int] = {"entries": count}
    started = time.perf_counter()
    first_batch = None
    first_row = None
    original_batch = panel._on_listing_batch

    def on_batch(token, entries):
        nonlocal first_batch, first_row
        if first_batch is None:
            first_batch = (time.perf_counter() - started) * 1000
        original_batch(token, entries)
        if first_row is None and panel.views["all"].topLevelItemCount() > 1:
            first_row = (time.perf_counter() - started) * 1000

    panel._on_listing_batch = on_batch  # type: ignore[method-assign]
    panel.set_dir("/work")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if panel._listing_worker is None and panel.views["all"].topLevelItemCount() == count + 1:
            break
    else:
        raise TimeoutError(f"listing did not finish for {count} entries")
    timings.update({
        "first_batch_ms": round(float(first_batch or 0), 3),
        "first_row_ms": round(float(first_row or 0), 3),
        "full_render_ms": round((time.perf_counter() - started) * 1000, 3),
        "rows": panel.views["all"].topLevelItemCount() - 1,
    })
    panel.deleteLater()
    app.processEvents()
    return timings


def run(repeats: int, timeout: float) -> dict:
    app = QApplication.instance() or QApplication([])
    measurements = [_measure(app, count, timeout) for count in (100, 1000, 10000) for _ in range(repeats)]
    return {
        "schema": 1,
        "label": "synthetic-offscreen-gui",
        "description": "Fabricated progressive entries rendered by the real RemoteDirPanel; excludes SSH and SFTP.",
        "repeats": repeats,
        "timeout_seconds": timeout,
        "measurements": measurements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.repeats < 1 or args.timeout <= 0:
        parser.error("--repeats and --timeout must be positive")
    report = run(args.repeats, args.timeout)
    for count in (100, 1000, 10000):
        rows = [m for m in report["measurements"] if m["entries"] == count]
        print(f"{count:>5} entries: first row {statistics.median(m['first_row_ms'] for m in rows):.2f} ms, full {statistics.median(m['full_render_ms'] for m in rows):.2f} ms")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
