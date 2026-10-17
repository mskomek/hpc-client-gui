"""Wave 50 Jobs Files/Outputs tabs real-event tests."""
from support.test_wx_jobs_files_outputs_shared import (
    _build_panel,
    _close,
    pytest,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_output_scroll_does_not_force_user_back_to_latest():
    contents = {"/work/stdout.log": "".join(f"line-{index}\n" for index in range(300))}
    jobs = [{"id": "1001", "state": "RUNNING", "name": "solver", "workdir": "/work",
             "stdout_path": "/work/stdout.log"}]
    app, frame, panel = _build_panel(
        list_jobs=lambda: jobs, read_remote_path=lambda path: contents.get(path, ""),
    )
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 1:
                break
            wx.MilliSleep(10)
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
        evt.SetIndex(0)
        ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
        ctrls["notebook"].SetSelection(4)
        panel._wx_jobs_refresh_outputs()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            if ctrls["output_channels"] and any("line-299" in tc.GetValue() for tc in ctrls["output_channels"].values()):
                break
        output = next(iter(ctrls["output_channels"].values()))
        output.ShowPosition(0)
        contents["/work/stdout.log"] += "line-300\n"
        panel._wx_jobs_refresh_outputs()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
            if "line-300" in output.GetValue():
                break
        assert "line-300" in output.GetValue()
        assert output.GetScrollPos(wx.VERTICAL) < output.GetScrollRange(wx.VERTICAL)
    finally:
        _close(frame)
