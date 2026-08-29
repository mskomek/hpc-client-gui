from __future__ import annotations

import importlib

import hpc_gui.core.terminal_graphics as graphics


def test_invalid_policy_falls_back_to_auto():
    assert graphics.normalize_settings({}) == ("auto", False)
    assert graphics.normalize_settings({"terminal_graphics_mode": "bogus"}) == ("auto", False)
    assert graphics.normalize_settings({"terminal_graphics_auto_compatibility": "yes"}) == ("auto", False)


def test_flag_matching_is_token_based():
    assert graphics.has_flag('--foo "two words" --disable-gpu')
    assert not graphics.has_flag("--disable-gpu-helper")


def test_gbm_tracker_requires_three_recent_linux_warnings(monkeypatch):
    monkeypatch.setattr(graphics.sys, "platform", "linux")
    tracker = graphics.GbmWarningTracker(threshold=3, window_seconds=30)
    warning = graphics.GBM_WARNING
    assert not tracker.record(warning, now=0)
    assert not tracker.record(warning, now=10)
    assert tracker.record(warning, now=20)
    assert not tracker.record("QSystemTrayIcon::setVisible: No Icon set", now=21)


def test_gbm_tracker_drops_expired_warnings(monkeypatch):
    monkeypatch.setattr(graphics.sys, "platform", "linux")
    tracker = graphics.GbmWarningTracker(threshold=3, window_seconds=30)
    assert not tracker.record(graphics.GBM_WARNING, now=0)
    assert not tracker.record(graphics.GBM_WARNING, now=1)
    assert not tracker.record(graphics.GBM_WARNING, now=32)


def test_restart_environment_removes_only_application_flag(monkeypatch):
    monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", '--foo "two words"')
    module = importlib.reload(graphics)
    module.apply_bootstrap({"terminal_graphics_mode": "compatibility"})
    assert module.restart_environment()["QTWEBENGINE_CHROMIUM_FLAGS"] == '--foo "two words"'
