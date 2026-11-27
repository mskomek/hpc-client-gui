from __future__ import annotations

import importlib.util
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

import pytest


def _load_probe_module():
    path = Path(__file__).resolve().parents[1] / "devtools" / "performance_probe.py"
    spec = importlib.util.spec_from_file_location("test_performance_probe_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("performance probe could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PerformanceProbeTests(unittest.TestCase):
    @pytest.mark.gui
    @pytest.mark.wx
    @pytest.mark.subprocess
    @pytest.mark.performance
    def test_wx_event_loop_block_is_detected(self):
        root = Path(__file__).resolve().parents[1]
        script = """
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import wx

spec = importlib.util.spec_from_file_location('probe', Path('devtools/performance_probe.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'src' / 'hpc_gui').mkdir(parents=True)
    app = wx.App(False)
    frame = wx.Frame(None)
    frame.Show()
    session = module.PerformanceSession(root, interval_ms=20, slow_ms=30)
    session.start()
    session.attach_to_app(app)
    session.attach_to_app(app)  # idempotent
    blocked = []
    def block():
        blocked.append(True)
        time.sleep(.15)
    wx.CallLater(80, block)
    wx.CallLater(420, app.ExitMainLoop)
    app.MainLoop()
    session.finish(0)
    session.finish(9)
    events = [json.loads(line) for line in session.report_path.read_text(encoding='utf-8').splitlines()]
    delays = [event['delay_ms'] for event in events if event['event'] == 'event_loop_delay']
    assert blocked and delays and max(delays) >= 80, delays
    assert sum(e.get('name') == 'event_loop_monitor_attached' for e in events) == 1
    assert [e['exit_code'] for e in events if e['event'] == 'session_end'] == [0]
    assert session._stop_timer is None
    assert not any(m.split('.')[0] in {'PySide6','PyQt5','PyQt6','shiboken6'} for m in sys.modules)
    frame.Destroy()
    app.ProcessPendingEvents()
"""
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=root, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.performance
    def test_slow_event_loop_tick_is_recorded(self):
        module = _load_probe_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src" / "hpc_gui").mkdir(parents=True)
            session = module.PerformanceSession(
                root,
                interval_ms=100,
                slow_ms=200,
                now=lambda: 10.0,
            )
            session._expected_tick = 10.1

            delay_ms = session.measure_tick(10.35)

            self.assertAlmostEqual(delay_ms, 250.0)
            events = [
                json.loads(line)
                for line in session.report_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(events[0]["event"], "event_loop_delay")
            self.assertEqual(events[0]["delay_ms"], 250.0)

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.performance
    def test_fast_event_loop_tick_does_not_write_delay(self):
        module = _load_probe_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src" / "hpc_gui").mkdir(parents=True)
            session = module.PerformanceSession(
                root,
                interval_ms=100,
                slow_ms=200,
                now=lambda: 10.0,
            )
            session._expected_tick = 10.1

            delay_ms = session.measure_tick(10.15)

            self.assertAlmostEqual(delay_ms, 50.0)
            self.assertFalse(session.report_path.exists())


if __name__ == "__main__":
    unittest.main()
