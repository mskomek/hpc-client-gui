"""Provider status rendering and stale-response GUI acceptance tests."""

import time

import pytest

wx = pytest.importorskip("wx")

from support.wx_jobs_test_harness import (  # noqa: E402
    build_workspace as _build,
    click_button as _click,
    close_frame as _close,
    pump_wx as _pump,
    select_job as _select,
)


@pytest.mark.gui
@pytest.mark.wx
def test_cluster_disconnected_and_unsupported_states_are_explicit():
    app, frame, panel = _build()
    try:
        controls = panel._wx_jobs_controls
        assert controls["notebook"].GetPageCount() == 5
        assert "No cluster connection" in controls["cluster_status_text"].GetLabel()
    finally:
        _close(frame)

    app, frame, panel = _build(provider_connected=True)
    try:
        assert "not available" in panel._wx_jobs_controls["cluster_status_text"].GetLabel()
    finally:
        _close(frame)


@pytest.mark.gui
@pytest.mark.wx
def test_cluster_status_needs_no_selected_job_and_uses_real_refresh_event():
    raw = (
        "Slurm partitions state\n"
        "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
        "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
        "short 8 32 0 1 2 1-00:00:00 1 2 16 4096"
    )
    app, frame, panel = _build(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda: raw,
    )
    try:
        controls = panel._wx_jobs_controls
        _click(controls["btn_refresh_lssrv"])
        assert _pump(lambda: controls["cluster_servers_table"].GetItemCount() == 1)
        assert panel._wx_jobs_state["selected_job"] == ""
        assert controls["cluster_servers_table"].GetItemText(0, 0) == "short"
    finally:
        _close(frame)


@pytest.mark.gui
@pytest.mark.wx
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
                "profile": {
                    "provider_template": {
                        "cluster_status": {
                            "adapter": "truba.lssrv",
                            "parser": "truba.lssrv.v1",
                        },
                    },
                },
            },
        },
        has_status_capability=lambda: True,
        refresh_lssrv=lambda: raw,
    )
    try:
        controls = panel._wx_jobs_controls
        _click(controls["btn_refresh_lssrv"])
        assert _pump(lambda: controls["cluster_servers_table"].GetItemCount() == 1)
        table = controls["cluster_servers_table"]
        assert [table.GetItemText(0, index) for index in range(4)] == [
            "short", "8", "32", "4096",
        ]
    finally:
        _close(frame)


@pytest.mark.gui
@pytest.mark.wx
def test_malformed_lssrv_warns_and_preserves_raw_status():
    raw = "this is not a valid lssrv response"
    app, frame, panel = _build(
        has_status_capability=lambda: True,
        refresh_lssrv=lambda: raw,
    )
    try:
        controls = panel._wx_jobs_controls
        _click(controls["btn_refresh_lssrv"])
        assert _pump(
            lambda: "could not be parsed" in controls["cluster_status_text"].GetLabel()
        )
        assert controls["cluster_servers_table"].GetItemCount() == 0
        assert panel._wx_jobs_state["raw_status_result"].stdout == raw
    finally:
        _close(frame)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.concurrency
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
        controls = panel._wx_jobs_controls
        _select(panel, 0)
        _select(panel, 1)
        table = controls["cluster_servers_table"]
        assert _pump(
            lambda: table.GetItemCount() > 0 and "part-A" in table.GetItemText(0, 0),
            100,
        )
        provider["value"] = "B"
        panel._wx_jobs_set_session(None)
        panel._wx_jobs_set_session({"id": "B"})
        assert _pump(
            lambda: table.GetItemCount() > 0 and "part-B" in table.GetItemText(0, 0),
            120,
        )
        assert "part-B" in panel._wx_jobs_state["raw_status_result"].stdout
        assert "part-A" not in panel._wx_jobs_state["raw_status_result"].stdout
        assert calls
    finally:
        _close(frame)
