"""Headless preservation of legacy browser layout preferences in V2."""
import pytest

from hpc_gui import wx_shell_layout


@pytest.mark.parametrize("settings,key,default,expected", [
    ({"splitter_ratios": {"directories_remote_panels": 0.62}}, "directories_remote_panels", 0.5, 0.62),
    ({"splitter_ratios": {"files_local_remote": 0.7}}, "files_local_remote", 0.5, 0.7),
    ({"ftp_splitter_sizes": [300, 700]}, "files_local_remote", 0.5, 0.3),
    ({"ftp_splitter_sizes": [0, 0]}, "files_local_remote", 0.5, 0.5),
    ({"ftp_splitter_sizes": ["bad", 700]}, "files_local_remote", 0.5, 0.5),
    ({"ftp_splitter_sizes": [1, 1000]}, "files_local_remote", 0.5, 0.5),
    ({"splitter_ratios": {"files_local_remote": 0.65}, "ftp_splitter_sizes": [300, 700]}, "files_local_remote", 0.5, 0.65),
    ({"wx_splitter_ratios": {"files_local_remote": 0.55}, "splitter_ratios": {"files_local_remote": 0.65}}, "files_local_remote", 0.5, 0.55),
    ({"wx_splitter_ratios": {"files_local_remote": 1.7}, "splitter_ratios": {"files_local_remote": 0.65}}, "files_local_remote", 0.5, 0.5),
    ({"splitter_ratios": {"files_browser_transfers": 0.55}}, "files_browser_transfers", 0.72, 0.72),
])
def test_restore_legacy_layout_only_when_wx_value_absent(monkeypatch, settings, key, default, expected):
    monkeypatch.setattr(wx_shell_layout, "load_settings", lambda: settings)
    monkeypatch.setattr(wx_shell_layout, "update_settings", lambda *_: pytest.fail("restore must be read-only"))
    assert wx_shell_layout._saved_ratio(key, default) == pytest.approx(expected)
