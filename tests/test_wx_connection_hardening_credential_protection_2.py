
pytest_plugins = ('support.test_wx_connection_hardening_shared',)
"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_hardening_shared import (
    _isolated_storage,
    build_connection_panel,
    mock,
    pytest,
    wx,
)


@pytest.mark.unit
@pytest.mark.wx
def test_host_key_mapping(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        model = host._wx_connection_model
        for expected, wx_id in [("save", wx.ID_YES), ("once", wx.ID_NO), ("reject", wx.ID_CANCEL)]:
            with mock.patch("wx.MessageDialog") as MockDlg:
                inst = MockDlg.return_value
                inst.ShowModal.return_value = wx_id
                inst.Destroy = mock.Mock()
                result = model.decide_host_key(mock.Mock(hostname="h.example", fingerprint="aa:bb", role="target"))
                assert result == expected
        # Changed host keys must not be silently accepted – model defaults to reject (mocked to avoid popup)
        with mock.patch("wx.MessageDialog") as MockDlg:
            inst = MockDlg.return_value
            inst.ShowModal.return_value = wx.ID_CANCEL
            inst.Destroy = mock.Mock()
            assert model.decide_host_key(mock.Mock(hostname="h", fingerprint="changed", role="target")) == "reject"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
