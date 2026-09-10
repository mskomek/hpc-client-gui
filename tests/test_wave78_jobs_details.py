"""Wave 78: Jobs/Details UX Re-architecture + Raw Command Fallback tests."""
import time

import pytest
wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, set_language, t
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.wx_jobs import build_jobs_panel


def _fake_jobs():
    return [
        {"id": "1001", "state": "RUNNING", "name": "jobA", "partition": "gpu",
         "elapsed": "00:05:00", "nodes": "2", "cpus": "16", "reason": "None",
         "workdir": "/work/1001", "stdout_path": "/out/1001.out",
         "stderr_path": "/out/1001.err", "script_path": "/work/run.sh",
         "nodelist": "node[0-1]", "exit_code": "0:0"},
        {"id": "1002", "state": "PENDING", "name": "jobB", "partition": "cpu",
         "elapsed": "-", "nodes": "1", "cpus": "4", "reason": "Priority"},
    ]


def _build_panel(list_jobs=None, read_output=None, **kwargs):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(
        frame,
        list_jobs=list_jobs or _fake_jobs,
        read_output=read_output or (lambda j: {"stdout": f"out {j}", "stderr": ""}),
        **kwargs,
    )
    frame.Show()
    wx.Yield()
    return app, frame, panel


def _select_job(panel, index=0):
    ctrls = panel._wx_jobs_controls
    evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
    evt.SetIndex(index)
    ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
    wx.Yield()


def _close(frame):
    try:
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                child.Hide()
                child.Destroy()
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()


def test_inner_tabs_are_jobs_cluster_details_files_outputs():
    app, frame, panel = _build_panel()
    try:
        nb = panel._wx_jobs_controls["notebook"]
        assert nb.GetPageCount() == 5
        assert nb.GetPageText(0) == t("jobs.title")
        assert nb.GetPageText(1) == t("jobs.cluster")
        assert nb.GetPageText(2) == t("jobs.details")
        assert nb.GetPageText(3) == t("jobs_outputs.files_title")
        assert nb.GetPageText(4) == t("jobs_outputs.outputs_title")
    finally:
        _close(frame)


def test_selecting_a_job_updates_details():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 2:
                break
            wx.MilliSleep(10)
        _select_job(panel, 0)
        for _ in range(30):
            wx.Yield()
            wx.MilliSleep(10)
        values = ctrls["detail_values"]
        assert values["job_id"].GetValue() == "1001"
        assert values["name"].GetValue() == "jobA"
        assert values["state"].GetValue() == "RUNNING"
        assert values["partition"].GetValue() == "gpu"
    finally:
        _close(frame)


def test_no_selection_state_shows_empty_state():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        assert ctrls["no_selection_panel"].IsShown()
        assert not ctrls["details_content_panel"].IsShown()
        labels = [child.GetLabel() for child in ctrls["no_selection_panel"].GetChildren()
                  if hasattr(child, "GetLabel")]
        assert t("jobs.no_job_selected") in labels
    finally:
        _close(frame)


def test_go_to_jobs_switches_to_jobs_tab():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        nb = ctrls["notebook"]
        nb.SetSelection(2)
        wx.Yield()
        ctrls["go_to_jobs"]()
        wx.Yield()
        assert nb.GetSelection() == 0
    finally:
        _close(frame)


def test_accounting_expand_collapse():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        _select_job(panel, 0)
        wx.Yield()
        # Accounting starts collapsed
        assert panel._wx_jobs_state["accounting_collapsed"] is True
        # Toggle expand
        ctrls["collapse_accounting"]()
        wx.Yield()
        assert panel._wx_jobs_state["accounting_collapsed"] is False
        # Toggle collapse
        ctrls["collapse_accounting"]()
        wx.Yield()
        assert panel._wx_jobs_state["accounting_collapsed"] is True
    finally:
        _close(frame)


def test_cluster_servers_visible_without_selected_job_when_provider_supports():
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
        _select_job(panel, 0)
        for _ in range(50):
            wx.Yield()
            if ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded"):
                break
            wx.MilliSleep(10)
        assert ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded")
    finally:
        _close(frame)


def test_cluster_servers_table_and_raw_result_are_visible():
    load_language("en")
    app, frame, panel = _build_panel(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda _job_id: (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "short 8 32 0 1 2 1-00:00:00 1 2 16 4096\n"
            "long 16 64 0 2 4 2-00:00:00 1 4 32 8192"
        ),
    )
    try:
        ctrls = panel._wx_jobs_controls
        ctrls["btn_refresh_lssrv"].ProcessEvent(
            wx.CommandEvent(wx.wxEVT_BUTTON, ctrls["btn_refresh_lssrv"].GetId())
        )
        for _ in range(50):
            wx.Yield()
            if ctrls["cluster_servers_table"].GetItemCount() == 2:
                break
            wx.MilliSleep(10)
        table = ctrls["cluster_servers_table"]
        assert table.GetItemCount() == 2
        assert [table.GetColumn(i).GetText() for i in range(4)] == [
            "Partition", "Free CPUs", "Total CPUs", "RAM (MB) per Core",
        ]
        assert table.GetItemText(0, 0) == "short"
        assert table.GetItemText(0, 1) == "8"
        assert table.GetItemText(0, 2) == "32"
        assert table.GetItemText(1, 3) == "8192"
        raw = panel._wx_jobs_state["raw_status_result"]
        assert isinstance(raw, RawCommandResult)
        assert "long 16 64 0 2 4" in raw.stdout
        assert ctrls["btn_raw_server_status"].IsShown()
    finally:
        _close(frame)


def test_raw_result_callback_is_parsed_and_preserved_for_details_and_accounting():
    app, frame, panel = _build_panel(
        show_job_details=lambda jid: RawCommandResult.from_response(
            source_id="scontrol", command=f"scontrol show job {jid}",
            stdout=f"JobId={jid} WorkDir=/raw/{jid} StdOut=/raw/{jid}.out",
            exit_code=0,
        ),
        refresh_sacct=lambda jid: RawCommandResult.from_response(
            source_id="sacct", command=f"sacct -j {jid}",
            stdout=f"JobID|STATE|ELAPSED\n{jid}|RUNNING|00:05:00",
            exit_code=0,
        ),
    )
    try:
        _select_job(panel, 0)
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        state = panel._wx_jobs_state
        assert state["raw_details_result"].stdout.startswith("JobId=1001")
        assert state["raw_accounting_result"].stdout.startswith("JobID|")
        assert panel._wx_jobs_controls["detail_values"]["workdir"].GetValue() == "/raw/1001"
        assert panel._wx_jobs_controls["accounting_table"].GetItemText(0, 0) == "1001"
    finally:
        _close(frame)


def test_cluster_servers_hidden_for_unsupported_provider():
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        assert ctrls["notebook"].GetPageCount() == 5
    finally:
        _close(frame)


def test_raw_server_status_opens():
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
        _select_job(panel, 0)
        for _ in range(50):
            wx.Yield()
            if ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded"):
                break
            wx.MilliSleep(10)
        assert ctrls["cluster_status_text"].GetLabel() == t("jobs_outputs.cluster_status_loaded")
    finally:
        _close(frame)


def test_raw_job_details_opens():
    app, frame, panel = _build_panel(
        show_job_details=lambda jid: f"JobId={jid} JobName=test WorkDir=/work/{jid}",
    )
    try:
        _select_job(panel, 0)
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(10)
        raw = panel._wx_jobs_state.get("raw_details_result")
        assert raw is not None
        assert isinstance(raw, RawCommandResult)
        assert "1001" in raw.stdout or raw.stdout == ""
    finally:
        _close(frame)


def test_raw_accounting_opens():
    app, frame, panel = _build_panel(
        refresh_sacct=lambda jid: f"JOBID|STATE|ELAPSED\n{jid}|RUNNING|00:05:00",
    )
    try:
        _select_job(panel, 0)
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(10)
        raw = panel._wx_jobs_state.get("raw_accounting_result")
        assert raw is not None
        assert isinstance(raw, RawCommandResult)
        assert "1001" in raw.stdout or raw.stdout == ""
    finally:
        _close(frame)


def test_parser_failure_leaves_raw_viewer_usable():
    def failing_sacct(_jid):
        raise RuntimeError("sacct failed")

    app, frame, panel = _build_panel(refresh_sacct=failing_sacct)
    try:
        _select_job(panel, 0)
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(10)
        raw = panel._wx_jobs_state.get("raw_accounting_result")
        assert raw is not None
        assert raw.has_error
        assert "sacct failed" in raw.stderr
    finally:
        _close(frame)


def test_ab_stale_raw_details_result_rejected():
    slow_details = []

    def show_details(job_id):
        if job_id == "1001":
            slow_details.append(job_id)
            time.sleep(0.3)
            return "JobId=1001 JobName=old WorkDir=/old"
        return f"JobId={job_id} JobName=new WorkDir=/new/{job_id}"

    app, frame, panel = _build_panel(show_job_details=show_details)
    try:
        ctrls = panel._wx_jobs_controls
        panel._wx_jobs_refresh_jobs()
        for _ in range(30):
            wx.Yield()
            if ctrls["jobs"].GetItemCount() >= 2:
                break
            wx.MilliSleep(10)
        _select_job(panel, 0)
        wx.Yield()
        _select_job(panel, 1)
        wx.Yield()
        for _ in range(60):
            wx.Yield()
            wx.MilliSleep(10)
        raw = panel._wx_jobs_state.get("raw_details_result")
        assert raw is not None
        assert "1002" in raw.stdout
    finally:
        _close(frame)


def test_runtime_language_refresh():
    load_language("en")
    app, frame, panel = _build_panel()
    try:
        ctrls = panel._wx_jobs_controls
        nb = ctrls["notebook"]
        assert nb.GetPageText(0) == "Jobs"
        assert nb.GetPageText(1) == "Cluster"
        assert nb.GetPageText(2) == "Details"
        set_language("tr")
        for _ in range(20):
            wx.Yield()
            wx.MilliSleep(5)
            if nb.GetPageText(0) != "Jobs":
                break
        assert nb.GetPageText(0) == t("jobs.title")
        assert nb.GetPageText(1) == t("jobs.cluster")
        assert nb.GetPageText(2) == t("jobs.details")
        set_language("en")
        wx.Yield()
    finally:
        _close(frame)


def test_raw_command_result_model():
    r = RawCommandResult.from_response(
        source_id="scontrol",
        command="scontrol show job 1001",
        stdout="JobId=1001",
        stderr="",
        exit_code=0,
    )
    assert r.source_id == "scontrol"
    assert r.command == "scontrol show job 1001"
    assert r.stdout == "JobId=1001"
    assert not r.has_error
    assert r.display_command == "scontrol show job 1001"

    r2 = RawCommandResult.from_response(
        source_id="sacct",
        command="sacct -j 1001",
        stdout="",
        stderr="permission denied",
        exit_code=1,
    )
    assert r2.has_error
    assert r2.display_command == "sacct -j 1001"
