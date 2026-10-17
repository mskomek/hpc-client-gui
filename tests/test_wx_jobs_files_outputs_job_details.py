"""Wave 50 Jobs Files/Outputs tabs real-event tests."""
from support.test_wx_jobs_files_outputs_shared import (
    _build_panel,
    _close,
    definitions_from_provider,
    pytest,
    t,
    time,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_provider_status_is_visible_only_when_backend_supports_it():
    app, frame, panel = _build_panel(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda _job_id: (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
        ),
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
        for _ in range(50):
            wx.Yield()
            if ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded"):
                break
            wx.MilliSleep(10)
        assert ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded")
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_jobs_details_latest_selection_wins_over_slow_scontrol():
    def show_details(job_id):
        if job_id == "1001":
            time.sleep(0.25)
        return f"JobId={job_id} JobName={'old' if job_id == '1001' else 'new'} WorkDir=/work/{job_id} StdOut=/out/{job_id}.out"

    app, frame, panel = _build_panel(show_job_details=show_details)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 2:
                break
            wx.MilliSleep(10)
        for index in (0, 1):
            evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
            evt.SetIndex(index)
            ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
            wx.Yield()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        values = ctrls["detail_values"]
        assert values["job_id"].GetValue() == "1002"
        assert values["workdir"].GetValue() == "/work/1002"
        raw_result = panel._wx_jobs_state.get("raw_details_result")
        if raw_result is not None:
            assert "1001" not in raw_result.stdout
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
def test_wx_jobs_accounting_latest_selection_wins_over_slow_sacct():
    def refresh_sacct(job_id):
        if job_id == "1001":
            time.sleep(0.25)
        return f"JOBID|STATE|ELAPSED\n{job_id}|{'OLD' if job_id == '1001' else 'NEW'}|00:01:00"

    app, frame, panel = _build_panel(refresh_sacct=refresh_sacct)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 2:
                break
            wx.MilliSleep(10)
        for index in (0, 1):
            evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
            evt.SetIndex(index)
            ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
            wx.Yield()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        table = ctrls["accounting_table"]
        assert table.GetItemCount() >= 1
        assert table.GetItemText(0, 0) == "1002"
        assert "OLD" not in " ".join(table.GetItemText(0, column) for column in range(table.GetColumnCount()))
    finally:
        _close(frame)

@pytest.mark.gui
@pytest.mark.wx
def test_wx_jobs_provider_output_definitions_refresh_after_reconnect():
    definitions = [{
        "streams": [{
            "id": "stdout", "role": "stdout", "labels": {"en": "Output"},
            "resolver": "slurm.stdout", "order": 0,
        }, {
            "id": "stderr", "role": "stderr", "labels": {"en": "Error"},
            "resolver": "slurm.stderr", "order": 1,
        }],
    }]

    def current_defs():
        return definitions_from_provider(definitions[0])

    app, frame, panel = _build_panel(output_channel_defs_provider=current_defs)
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
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
            if set(ctrls["output_channels"]) == {"stdout", "stderr"}:
                break
        assert set(ctrls["output_channels"]) == {"stdout", "stderr"}

        definitions[0] = {"streams": []}
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
            if ctrls["output_channel_notebook"].GetPageCount() == 1:
                break
        assert ctrls["output_channel_notebook"].GetPageCount() == 1

        definitions[0] = None
        panel._wx_jobs_refresh_outputs()
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
            if set(ctrls["output_channels"]) == {"stdout", "stderr"}:
                break
        assert set(ctrls["output_channels"]) == {"stdout", "stderr"}
    finally:
        _close(frame)
