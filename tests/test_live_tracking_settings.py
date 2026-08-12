from __future__ import annotations

from truba_gui.config import storage


def test_live_tracking_warning_interval_defaults_and_allows_disable(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: config_path)
    monkeypatch.setattr(storage, "_config_dir", lambda: tmp_path)
    storage.save_config({"profiles": [], "settings": {}})
    assert storage.get_live_tracking_warning_interval_seconds() == 60
    assert storage.set_live_tracking_warning_interval_seconds(0) == 0
    assert storage.get_live_tracking_warning_interval_seconds() == 0
    assert storage.set_live_tracking_warning_interval_seconds(99999) == 3600
