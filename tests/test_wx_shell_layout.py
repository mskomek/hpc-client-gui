from types import SimpleNamespace

import pytest

from hpc_gui import wx_shell_layout


class _Splitter:
    def __init__(self, width=1200, height=800):
        self.width = width
        self.height = height
        self.position = -1
        self.gravity = None
        self.handlers = {}

    def GetClientSize(self):
        return SimpleNamespace(width=self.width, height=self.height)

    def IsSplit(self):
        return True

    def GetMinimumPaneSize(self):
        return 150

    def SetSashPosition(self, position):
        self.position = position

    def GetSashPosition(self):
        return self.position

    def SetSashGravity(self, ratio):
        self.gravity = ratio

    def Bind(self, event_type, handler):
        self.handlers[event_type] = handler


def _wx():
    return SimpleNamespace(
        EVT_SIZE=object(),
        EVT_SPLITTER_SASH_POS_CHANGED=object(),
        EVT_WINDOW_DESTROY=object(),
        CallAfter=lambda callback: callback(),
    )


def test_saved_vertical_ratio_is_restored(monkeypatch):
    monkeypatch.setattr(
        wx_shell_layout,
        "load_settings",
        lambda: {"wx_splitter_ratios": {"directories": 0.63}},
    )
    splitter = _Splitter()

    wx_shell_layout.install_splitter_ratio(
        _wx(), splitter, key="directories", orientation="vertical"
    )

    assert splitter.position == 756
    assert splitter.gravity == 0.63


def test_sash_ratio_round_trips_through_settings(monkeypatch):
    settings = {}
    monkeypatch.setattr(wx_shell_layout, "load_settings", lambda: settings)

    def update_settings(patch):
        settings.update(patch)

    monkeypatch.setattr(wx_shell_layout, "update_settings", update_settings)
    wx = _wx()
    first = _Splitter(width=1200)
    wx_shell_layout.install_splitter_ratio(wx, first, key="files")
    first.position = 792
    first.handlers[wx.EVT_SPLITTER_SASH_POS_CHANGED](
        SimpleNamespace(Skip=lambda: None)
    )

    reopened = _Splitter(width=1500)
    wx_shell_layout.install_splitter_ratio(wx, reopened, key="files")

    assert settings["wx_splitter_ratios"]["files"] == 0.66
    assert reopened.position == 990
    assert reopened.gravity == 0.66


def test_saved_ratio_is_clamped_to_minimum_pane_size(monkeypatch):
    monkeypatch.setattr(
        wx_shell_layout,
        "load_settings",
        lambda: {"wx_splitter_ratios": {"narrow": 0.05}},
    )
    splitter = _Splitter()

    wx_shell_layout.install_splitter_ratio(_wx(), splitter, key="narrow")

    assert splitter.position == splitter.GetMinimumPaneSize()


def test_user_sash_change_persists_the_new_ratio(monkeypatch):
    saved = {}
    monkeypatch.setattr(wx_shell_layout, "load_settings", lambda: saved)

    def update_settings(patch):
        saved.update(patch)

    monkeypatch.setattr(wx_shell_layout, "update_settings", update_settings)
    wx = _wx()
    splitter = _Splitter()
    wx_shell_layout.install_splitter_ratio(
        wx, splitter, key="files", default_ratio=0.5
    )
    splitter.position = 720
    skipped = []

    splitter.handlers[wx.EVT_SPLITTER_SASH_POS_CHANGED](
        SimpleNamespace(Skip=lambda: skipped.append(True))
    )

    assert saved["wx_splitter_ratios"]["files"] == 0.6
    assert splitter.gravity == 0.6
    assert skipped == [True]


def test_saved_horizontal_ratio_uses_height_and_invalid_values_fall_back(monkeypatch):
    monkeypatch.setattr(
        wx_shell_layout,
        "load_settings",
        lambda: {"wx_splitter_ratios": {"transfers": 1.7}},
    )
    splitter = _Splitter(height=800)

    wx_shell_layout.install_splitter_ratio(
        _wx(),
        splitter,
        key="transfers",
        default_ratio=0.72,
        orientation="horizontal",
    )

    assert splitter.position == 576
    assert splitter.gravity == 0.72


@pytest.mark.parametrize(
    ("orientation", "saved_ratio", "sizes"),
    [
        ("vertical", 0.63, ((960, 700), (1200, 700), (1600, 700))),
        ("horizontal", 0.72, ((1200, 600), (1200, 700), (1200, 900))),
    ],
)
def test_native_splitter_restores_and_keeps_ratio_across_resizes(
    monkeypatch, orientation, saved_ratio, sizes
):
    wx = pytest.importorskip("wx")
    monkeypatch.setattr(
        wx_shell_layout,
        "load_settings",
        lambda: {"wx_splitter_ratios": {"native": saved_ratio}},
    )
    monkeypatch.setattr(wx_shell_layout, "update_settings", lambda _patch: None)
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, size=(1200, 700))
    splitter = wx.SplitterWindow(frame)
    first = wx.Panel(splitter)
    second = wx.Panel(splitter)
    splitter.SetMinimumPaneSize(150)
    if orientation == "vertical":
        splitter.SplitVertically(first, second, 500)
    else:
        splitter.SplitHorizontally(first, second, 350)
    frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
    frame.GetSizer().Add(splitter, 1, wx.EXPAND)
    wx_shell_layout.install_splitter_ratio(
        wx, splitter, key="native", orientation=orientation
    )
    frame.Show()

    try:
        app.ProcessPendingEvents()
        for frame_size in sizes:
            frame.SetSize(frame_size)
            frame.Layout()
            app.ProcessPendingEvents()
            client_size = splitter.GetClientSize()
            extent = client_size.width if orientation == "vertical" else client_size.height
            ratio = splitter.GetSashPosition() / extent
            assert abs(ratio - saved_ratio) <= 0.03, (
                frame_size,
                extent,
                splitter.GetSashPosition(),
                splitter.GetSashGravity(),
            )
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()
