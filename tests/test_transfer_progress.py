"""Verify resume-aware progress estimates without GUI dependencies."""
from hpc_gui.services import transfer_progress as progress
from hpc_gui.services.transfer_controller import TransferItem


def test_resumed_progress_uses_only_observed_session_bytes(monkeypatch):
    monkeypatch.setattr(progress, "t", lambda _: "{item} {done}/{total} {speed} remaining {eta}")
    tracker = progress.ProgressSamples()
    item = TransferItem("upload", "big.bin", "/big.bin")
    assert "0 B/s remaining ?" in tracker.detail(item, 8_000_000, 10_000_000, now=100)
    assert "488.3 KB/s remaining 0:02" in tracker.detail(item, 9_000_000, 10_000_000, now=102)
    assert "remaining 0:00" in tracker.detail(item, 10_000_000, 10_000_000, now=104)
    tracker.reset(item)
    assert "0 B/s remaining ?" in tracker.detail(item, 9_000_000, 10_000_000, now=105)


def test_independent_samples_and_unknown_total(monkeypatch):
    monkeypatch.setattr(progress, "t", lambda _: "{item} {done}/{total} {speed} remaining {eta}")
    tracker = progress.ProgressSamples()
    first = TransferItem("download", "/a", "a")
    second = TransferItem("download", "/b", "b")
    tracker.detail(first, 0, 0, now=10)
    tracker.detail(second, 500, 1000, now=11)
    assert "1.0 KB/? 512 B/s remaining ?" in tracker.detail(first, 1024, 0, now=12)
    assert "100 B/s remaining 0:04" in tracker.detail(second, 600, 1000, now=12)
    tracker.reset()
    assert "0 B/s" in tracker.detail(second, 700, 1000, now=13)
