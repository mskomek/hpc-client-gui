import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_jobs import build_jobs_panel


def _pump(app, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.SafeYield()
        if predicate():
            return True
        wx.MilliSleep(10)
    return predicate()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.regression
def test_jobs_table_supports_bulk_delete_without_changing_primary_selection(monkeypatch):
    app = wx.App.Get() or wx.App(False)
    deleted = []
    rows = [
        {"job_id": "101", "name": "first", "state": "COMPLETED"},
        {"job_id": "102", "name": "second", "state": "FAILED"},
    ]
    frame = wx.Frame(None)
    panel = build_jobs_panel(frame,
        list_jobs=lambda: list(rows), read_output=lambda _job: "",
        cancel=lambda _job: "", generation=lambda: 1,
        delete_job_details=lambda job_ids: deleted.extend(job_ids) or len(job_ids),
    )
    controls = panel._wx_jobs_controls
    jobs = controls["jobs"]
    try:
        assert _pump(app, lambda: jobs.GetItemCount() == 2)
        assert not jobs.GetWindowStyleFlag() & wx.LC_SINGLE_SEL
        jobs.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        jobs.SetItemState(1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        panel._wx_jobs_state["bulk_selected_job_ids"] = {"101", "102"}
        panel._wx_jobs_state["selected_job"] = "101"
        monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
        controls["delete_selected_details"]()
        assert set(deleted) == {"101", "102"}
        assert panel._wx_jobs_state["selected_job"] == ""
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()
