import time
import threading
from unittest.mock import patch

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language, set_language, t
from hpc_gui.services.output_channel_resolver import OutputChannelDefinition
from hpc_gui.wx_jobs import build_jobs_panel
from mock_hpc_files import MockRemoteFilesBackend


def _jobs():
    return [{
        "id": "1001", "name": "jobA", "state": "RUNNING", "partition": "gpu",
        "elapsed": "00:05:00", "nodes": "2", "cpus": "16", "reason": "None",
        "workdir": "/work/1001", "stdout_path": "/work/1001/out.txt",
        "stderr_path": "/work/1001/err.txt",
    }, {
        "id": "1002", "name": "jobB", "state": "PENDING", "partition": "cpu",
        "elapsed": "-", "nodes": "1", "cpus": "4", "reason": "Priority",
        "workdir": "/work/1002",
    }]


def _build(**kwargs):
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(frame, list_jobs=kwargs.pop("list_jobs", _jobs), **kwargs)
    frame.Show()
    wx.Yield()
    return app, frame, panel


def _pump(predicate, rounds=80):
    for _ in range(rounds):
        wx.Yield()
        if predicate():
            return True
        wx.MilliSleep(10)
    return bool(predicate())


def _select(panel, index=0):
    jobs = panel._wx_jobs_controls["jobs"]
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(index)
    jobs.GetEventHandler().ProcessEvent(event)
    wx.Yield()


def _click(control):
    event = wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId())
    event.SetEventObject(control)
    control.GetEventHandler().ProcessEvent(event)
    wx.Yield()


def _close(frame):
    try:
        frame.Close()
    except Exception:
        pass
    for _ in range(4):
        wx.Yield()


@pytest.mark.wx
@pytest.mark.gui
def test_inner_notebook_has_exact_order_and_language_refresh():
    app, frame, panel = _build()
    try:
        nb = panel._wx_jobs_controls["notebook"]
        assert [nb.GetPageText(i) for i in range(nb.GetPageCount())] == [
            "Jobs", "Cluster", "Details", "Files", "Outputs",
        ]
        set_language("tr")
        wx.Yield()
        assert nb.GetPageText(1) == t("jobs.cluster")
        assert nb.GetPageText(3) == t("jobs_outputs.files_title")
        set_language("en")
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_outputs_pause_all_and_accounting_labels_reset_and_localize():
    app, frame, panel = _build()
    try:
        ctrls = panel._wx_jobs_controls
        pause_all = ctrls["outputs_pause"]
        ctrls["outputs_follow"].SetValue(False)
        _click(pause_all)
        assert pause_all.GetLabel() == t("jobs_outputs.resume_all")
        panel._wx_jobs_set_session({"id": "new-session"})
        assert panel._wx_jobs_state["outputs_paused"] is False
        assert pause_all.GetLabel() == t("jobs_outputs.pause_all")
        assert ctrls["outputs_follow"].GetValue() is False
        assert ctrls["accounting_box"].GetLabel() == "▸ Accounting"
        set_language("tr")
        wx.Yield()
        assert pause_all.GetLabel() == "Tümünü Duraklat"
        _click(pause_all)
        assert pause_all.GetLabel() == "Tümüne Devam Et"
        assert ctrls["accounting_box"].GetLabel() == "▸ Muhasebe"
        set_language("en")
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_cluster_disconnected_and_unsupported_states_are_explicit():
    app, frame, panel = _build()
    try:
        ctrls = panel._wx_jobs_controls
        assert ctrls["notebook"].GetPageCount() == 5
        assert "No cluster connection" in ctrls["cluster_status_text"].GetLabel()
    finally:
        _close(frame)

    app, frame, panel = _build(provider_connected=True)
    try:
        assert "not available" in panel._wx_jobs_controls["cluster_status_text"].GetLabel()
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_cluster_status_needs_no_selected_job_and_uses_real_refresh_event():
    app, frame, panel = _build(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda: (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
        ),
    )
    try:
        ctrls = panel._wx_jobs_controls
        _click(ctrls["btn_refresh_lssrv"])
        assert _pump(lambda: ctrls["cluster_servers_table"].GetItemCount() == 1)
        assert panel._wx_jobs_state["selected_job"] == ""
        assert ctrls["cluster_servers_table"].GetItemText(0, 0) == "short"
    finally:
        _close(frame)


@pytest.mark.contract
def test_provider_contract_lssrv_parser_reaches_visible_cluster_cells():
    raw = (
        "Slurm partitions state\n"
        "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
        "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
        "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
    )
    app, frame, panel = _build(
        session_state={
            "session": {
                "id": "provider-session",
                "profile": {"provider_template": {
                    "cluster_status": {"adapter": "truba.lssrv", "parser": "truba.lssrv.v1"},
                }},
            },
        },
        has_status_capability=lambda: True,
        refresh_lssrv=lambda: raw,
    )
    try:
        _click(panel._wx_jobs_controls["btn_refresh_lssrv"])
        assert _pump(lambda: panel._wx_jobs_controls["cluster_servers_table"].GetItemCount() == 1)
        table = panel._wx_jobs_controls["cluster_servers_table"]
        assert [table.GetItemText(0, index) for index in range(4)] == ["short", "8", "32", "4096"]
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_malformed_lssrv_warns_and_preserves_raw_status():
    raw = "this is not a valid lssrv response"
    app, frame, panel = _build(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda: raw,
    )
    try:
        _click(panel._wx_jobs_controls["btn_refresh_lssrv"])
        assert _pump(lambda: "could not be parsed" in panel._wx_jobs_controls["cluster_status_text"].GetLabel())
        assert panel._wx_jobs_controls["cluster_servers_table"].GetItemCount() == 0
        assert panel._wx_jobs_state["raw_status_result"].stdout == raw
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_cluster_result_survives_job_selection_and_reconnect_rejects_old_result():
    calls = []
    provider = {"value": "A"}

    def refresh_lssrv():
        current = provider["value"]
        calls.append(current)
        if current == "A":
            time.sleep(0.15)
        return (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            f"part-{current} 2 4 0 1 1 1-00:00:00 1 1 4 2048"
        )

    app, frame, panel = _build(
        session_state={"session": {"id": "A"}},
        has_status_capability=lambda: True,
        refresh_lssrv=refresh_lssrv,
    )
    try:
        ctrls = panel._wx_jobs_controls
        _select(panel, 0)
        _select(panel, 1)
        assert _pump(lambda: "part-A" in ctrls["cluster_servers_table"].GetItemText(0, 0), 100)
        provider["value"] = "B"
        panel._wx_jobs_set_session(None)
        panel._wx_jobs_set_session({"id": "B"})
        assert _pump(lambda: "part-B" in ctrls["cluster_servers_table"].GetItemText(0, 0), 120)
        assert panel._wx_jobs_state["raw_status_result"].stdout.find("part-B") >= 0
        assert "part-A" not in panel._wx_jobs_state["raw_status_result"].stdout
        assert calls
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_details_compact_fields_and_parse_warning():
    app, frame, panel = _build(show_job_details=lambda _job: "not scheduler output")
    try:
        ctrls = panel._wx_jobs_controls
        _select(panel)
        assert _pump(lambda: ctrls["details_warning"].IsShown())
        assert ctrls["detail_values"]["resources"].GetValue() == "2 nodes, 16 CPUs"
        assert ctrls["detail_labels"]["nodes"].GetParent() is ctrls["advanced_box"]
        assert ctrls["detail_values"]["workdir"].GetValue() == "/work/1001"
        assert panel._wx_jobs_state["raw_details_result"].source_id == "scontrol"
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_accounting_parse_warning_keeps_raw_result():
    app, frame, panel = _build(refresh_sacct=lambda _job: "malformed accounting")
    try:
        ctrls = panel._wx_jobs_controls
        _select(panel)
        assert _pump(lambda: ctrls["accounting_warning"].IsShown())
        assert panel._wx_jobs_state["raw_accounting_result"].source_id == "sacct"
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_files_no_selection_reset_and_language_preserve_workdir():
    backend = MockRemoteFilesBackend()
    session = {"session": {"files": backend, "profile": {"profile_id": "final-files"}}}
    app, frame, panel = _build(session_state=session, remote_files_callbacks={"loader": backend.iterdir_entries})
    try:
        ctrls = panel._wx_jobs_controls
        assert ctrls["files_no_selection_panel"].IsShown()
        assert not ctrls["files_browser"].IsShown()
        _select(panel)
        assert _pump(lambda: "/work/1001" in ctrls["files_workdir_label"].GetLabel())
        assert ctrls["files_browser"].IsShown()
        set_language("tr")
        wx.Yield()
        assert "/work/1001" in ctrls["files_workdir_label"].GetLabel()
        panel._wx_jobs_set_session(None)
        assert not ctrls["files_browser"].IsShown()
        assert ctrls["files_no_selection_panel"].IsShown()
        assert "/work/1001" not in ctrls["files_workdir_label"].GetLabel()
        set_language("en")
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_outputs_no_job_zero_channels_waiting_and_pause_reset():
    defs = [OutputChannelDefinition(
        id="stdout", role="stdout", label_en="Standard Output",
        label_tr="Standart Çıktı", resolver="workdir.relative", relative_path="out.txt",
    )]

    app, frame, panel = _build(output_channel_defs=[])
    try:
        ctrls = panel._wx_jobs_controls
        assert ctrls["outputs_no_selection_panel"].IsShown()
        assert not ctrls["output_channel_notebook"].IsShown()
        ctrls["notebook"].SetSelection(4)
        _select(panel)
        assert _pump(lambda: not ctrls["outputs_no_selection_panel"].IsShown())
        assert ctrls["output_channel_notebook"].GetPageCount() == 1
        assert ctrls["output_no_channels_label"].IsShown()
        assert "No output channels" in ctrls["output_no_channels_label"].GetLabel()
    finally:
        _close(frame)

    app, frame, panel = _build(
        output_channel_defs=defs,
        read_remote_path=lambda _path: (_ for _ in ()).throw(FileNotFoundError()),
        session_state={"session": {"id": "A"}},
    )
    try:
        ctrls = panel._wx_jobs_controls
        _select(panel)
        assert _pump(lambda: bool(ctrls["output_channel_status"]))
        assert not ctrls["output_no_channels_label"].IsShown()
        assert _pump(lambda: "Waiting for file" in next(iter(ctrls["output_channel_status"].values())).GetLabel())
        assert next(iter(ctrls["output_channels"].values())).GetValue() == ""
        _click(ctrls["outputs_pause"])
        assert panel._wx_jobs_state["outputs_paused"] is True
        panel._wx_jobs_set_session({"id": "B"})
        assert panel._wx_jobs_state["outputs_paused"] is False
        assert panel._wx_jobs_state["_timer_paused"] is False
        assert ctrls["outputs_no_selection_panel"].IsShown()
        assert ctrls["output_channel_notebook"].GetPageCount() == 1
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_show_in_files_and_raw_buttons_use_real_wx_events():
    defs = [OutputChannelDefinition(
        id="stdout", role="stdout", label_en="Standard Output",
        resolver="workdir.relative", relative_path="out.txt",
    )]
    with patch("hpc_gui.wx_raw_viewer.show_raw_viewer") as viewer:
        app, frame, panel = _build(
            output_channel_defs=defs,
            refresh_sacct=lambda _job: "1001|RUNNING|00:05:00|1G|cpu=1|0:0",
            has_status_capability=lambda: True,
            refresh_lssrv=lambda: (
                "Slurm partitions state\n"
                "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
                "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
                "short 2 4 0 1 1 1-00:00:00 1 1 4 2048"
            ),
        )
        try:
            ctrls = panel._wx_jobs_controls
            _select(panel)
            assert _pump(lambda: bool(ctrls["output_channels"]))
            ctrls["notebook"].SetSelection(4)
            wx.Yield()
            _click(ctrls["btn_raw_job_details"])
            _click(ctrls["btn_raw_accounting"])
            assert _pump(lambda: ctrls["cluster_servers_table"].GetItemCount() == 1)
            ctrls["notebook"].SetSelection(1)
            _click(ctrls["btn_raw_server_status"])
            assert viewer.called
            assert viewer.call_count >= 3
            _click(ctrls["output_show_files"])
            assert ctrls["notebook"].GetSelection() == 3
            file_tab = ctrls["files_browser"]._wx_remote_tabs[
                ctrls["files_browser"]._wx_remote_notebook.GetSelection()
            ]
            assert file_tab["highlight_path"].endswith("/work/1001/out.txt")
        finally:
            _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_go_to_jobs_buttons_use_real_wx_events():
    app, frame, panel = _build()
    try:
        ctrls = panel._wx_jobs_controls
        for page, button in (
            (2, ctrls["details_go_to_jobs"]),
            (3, ctrls["files_go_to_jobs"]),
            (4, ctrls["outputs_go_to_jobs"]),
        ):
            ctrls["notebook"].SetSelection(page)
            _click(button)
            assert ctrls["notebook"].GetSelection() == 0
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_open_in_main_files_uses_real_wx_event():
    opened = []
    app, frame, panel = _build(open_main_files=opened.append)
    try:
        ctrls = panel._wx_jobs_controls
        _select(panel)
        _click(ctrls["open_main_files"])
        assert opened == ["/work/1001"]
    finally:
        _close(frame)


@pytest.mark.wx
@pytest.mark.gui
def test_stale_raw_exceptions_do_not_cross_job_or_provider():
    details_started = threading.Event()
    details_release = threading.Event()
    details_calls = []

    def show_details(job_id):
        details_calls.append(job_id)
        if job_id == "1001":
            details_started.set()
            details_release.wait(2)
            raise RuntimeError("late details A")
        return f"JobId={job_id} WorkDir=/work/{job_id}"

    app, frame, panel = _build(show_job_details=show_details)
    try:
        _select(panel, 0)
        assert details_started.wait(2)
        _select(panel, 1)
        details_release.set()
        assert _pump(lambda: panel._wx_jobs_state["raw_details_result"] is not None)
        assert "1002" in panel._wx_jobs_state["raw_details_result"].stdout
    finally:
        details_release.set()
        _close(frame)

    accounting_started = threading.Event()
    accounting_release = threading.Event()

    def refresh_accounting(job_id):
        if job_id == "1001":
            accounting_started.set()
            accounting_release.wait(2)
            raise RuntimeError("late accounting A")
        return f"{job_id}|RUNNING|00:01:00|1G|cpu=1|0:0"

    app, frame, panel = _build(refresh_sacct=refresh_accounting)
    try:
        _select(panel, 0)
        assert accounting_started.wait(2)
        _select(panel, 1)
        accounting_release.set()
        assert _pump(lambda: panel._wx_jobs_state["raw_accounting_result"] is not None)
        assert "1002" in panel._wx_jobs_state["raw_accounting_result"].stdout
    finally:
        accounting_release.set()
        _close(frame)

    cluster_started = threading.Event()
    cluster_release = threading.Event()
    provider = {"id": "A"}

    def refresh_cluster():
        if provider["id"] == "A":
            cluster_started.set()
            cluster_release.wait(2)
            raise RuntimeError("late cluster A")
        return (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "part-B 2 4 0 1 1 1-00:00:00 1 1 4 2048"
        )

    app, frame, panel = _build(
        session_state={"session": {"id": "A"}},
        has_status_capability=lambda: True,
        refresh_lssrv=refresh_cluster,
    )
    try:
        assert cluster_started.wait(2)
        provider["id"] = "B"
        panel._wx_jobs_set_session(None)
        panel._wx_jobs_set_session({"id": "B"})
        cluster_release.set()
        ctrls = panel._wx_jobs_controls
        assert _pump(lambda: "part-B" in ctrls["cluster_servers_table"].GetItemText(0, 0), 120)
        assert "part-B" in panel._wx_jobs_state["raw_status_result"].stdout
    finally:
        cluster_release.set()
        _close(frame)
