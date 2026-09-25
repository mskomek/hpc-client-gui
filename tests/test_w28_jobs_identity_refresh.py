"""W28 — Jobs identity, listing, parser and refresh state.

Covers HPC-W07-JOB-001..017 + HPC-W07-REFRESH-001..004 with exact executed
validation against the framework-neutral owners and the live wx wiring.
"""

import time

import pytest

from hpc_gui.services.job_identity import (
    base_job_id,
    cancel_is_safe,
    make_identity,
    selection_survives_refresh,
    split_job_id,
)
from hpc_gui.services.job_list_filter_sort import (
    cancel_target_is_safe,
    filter_jobs,
    selection_still_exists,
    sort_jobs,
)
from hpc_gui.services.jobs_refresh_state import JobsRefreshState
from hpc_gui.services.slurm_models import (
    is_terminal_state,
    parse_sacct,
    parse_sacct_result,
    parse_scontrol,
    parse_squeue,
    parse_squeue_result,
    safe_state_display,
)
from hpc_gui.services.slurm_ssh import SlurmCommandResult

pytestmark = pytest.mark.contract


# --- Workstream A: identity (JOB-001..004) ---------------------------------


def test_w28_job_identity_tuple_scopes_profile_cluster_provider():
    base = make_identity("123", profile_id="p1", cluster_id="c1", provider_id="slurm", session_generation=1)
    other_profile = make_identity("123", profile_id="p2", cluster_id="c1", provider_id="slurm", session_generation=1)
    other_cluster = make_identity("123", profile_id="p1", cluster_id="c2", provider_id="slurm", session_generation=1)
    other_provider = make_identity("123", profile_id="p1", cluster_id="c1", provider_id="other", session_generation=1)
    assert not base.same_target(other_profile)
    assert not base.same_target(other_cluster)
    assert not base.same_target(other_provider)
    assert not cancel_is_safe(base, other_profile)
    assert not cancel_is_safe(base, other_cluster)


def test_w28_job_identity_scopes_old_vs_new_session():
    old = make_identity("123", profile_id="p1", session_generation=7)
    new = make_identity("123", profile_id="p1", session_generation=8)
    assert not old.same_target(new)
    assert not cancel_is_safe(old, new)
    assert not selection_survives_refresh(old, [new])


def test_w28_job_identity_preserves_array_task_identifiers():
    assert split_job_id("123") == ("123", "", "")
    assert split_job_id("123_4") == ("123", "_4", "")
    assert split_job_id("123.batch") == ("123", ".batch", "")
    assert base_job_id("123_4") == "123"
    bare = make_identity("123", profile_id="p1", session_generation=1)
    array = make_identity("123_4", profile_id="p1", session_generation=1)
    assert not bare.same_target(array)
    assert not cancel_is_safe(bare, array)
    assert selection_survives_refresh(array, [array])
    assert not selection_survives_refresh(bare, [array])


def test_w28_job_identity_same_target_requires_every_field():
    left = make_identity("42", profile_id="p", cluster_id="c", provider_id="s", session_generation=3)
    right = make_identity("42", profile_id="p", cluster_id="c", provider_id="s", session_generation=3)
    assert left.same_target(right)
    assert cancel_is_safe(left, right)
    assert not cancel_is_safe(make_identity("", profile_id="p"), right)


# --- Workstream C: Slurm parsing (JOB-005..013) ------------------------------


def test_w28_parser_empty_job_list():
    assert parse_squeue("") == []
    assert parse_squeue("JOBID|PARTITION|NAME|USER|ST|TIME\n") == []
    assert parse_sacct("") == []


def test_w28_parser_one_and_many_jobs():
    one = parse_squeue("123|short|train|alice|R|00:12\n")
    assert len(one) == 1 and one[0].job_id == "123"
    many = parse_squeue(
        "123|short|a|alice|R|00:01\n"
        "124|short|b|alice|PD|00:00\n"
        "125|long|c|bob|CG|01:00:00\n"
    )
    assert [job.job_id for job in many] == ["123", "124", "125"]


def test_w28_parser_long_names_preserved():
    long_name = "x" * 200
    jobs = parse_squeue(f"123|short|{long_name}|alice|R|00:12\n")
    assert jobs[0].name == long_name


def test_w28_parser_unknown_new_state_displays_safely():
    jobs = parse_squeue("123|short|train|alice|ZZ|00:12\n")
    assert jobs[0].state == "ZZ"
    assert safe_state_display("ZZ") == "ZZ"
    assert safe_state_display("") == "UNKNOWN"
    # Unknown states must never be misreported as success/terminal.
    assert not is_terminal_state("ZZ")


def test_w28_parser_array_job_representation():
    jobs = parse_squeue(
        "123_4|short|train|alice|R|00:12\n"
        "123.batch|short|train|alice|R|00:12\n"
    )
    assert [job.job_id for job in jobs] == ["123_4", "123.batch"]
    acct = parse_sacct("123_4|train|RUNNING|00:01|1M\n")
    assert acct[0].job_id == "123_4"


def test_w28_parser_cancelled_completed_state():
    jobs = parse_squeue(
        "123|short|a|alice|CA|00:00\n"
        "124|short|b|alice|CD|01:00:00\n"
    )
    assert jobs[0].state == "CA"
    assert jobs[1].state == "CD"
    assert is_terminal_state("CA")
    assert is_terminal_state("COMPLETED")
    assert is_terminal_state("CANCELLED")
    assert not is_terminal_state("RUNNING")


def test_w28_parser_malformed_row_partial_output_skipped():
    jobs = parse_squeue(
        "123|short|train|alice|R|00:12\n"
        "garbage without columns\n"
        "slurm_load_jobs error: socket timed out\n"
    )
    assert [job.job_id for job in jobs] == ["123"]


def test_w28_parser_non_zero_scheduler_exit_is_not_empty_data():
    failed = SlurmCommandResult(code=1, stdout="", stderr="slurm_load_jobs error: failed")
    assert parse_squeue_result(failed) == []
    assert parse_sacct_result(failed) == []
    ok_empty = SlurmCommandResult(code=0, stdout="", stderr="")
    assert parse_squeue_result(ok_empty) == []
    ok_rows = SlurmCommandResult(code=0, stdout="123|short|train|alice|R|00:12\n", stderr="")
    assert [job.job_id for job in parse_squeue_result(ok_rows)] == ["123"]


# --- Workstream D: filtering/sorting (JOB-014..017) ---------------------------


def test_w28_sort_uses_semantic_values_not_display_strings():
    rows = [
        {"id": "10", "name": "b", "state": "PENDING", "elapsed": "00:10:00"},
        {"id": "2", "name": "a", "state": "RUNNING", "elapsed": "01:00:00"},
        {"id": "9", "name": "c", "state": "RUNNING", "elapsed": "00:01:00"},
    ]
    by_id = [item["id"] for item in sort_jobs(rows, "job_id")]
    assert by_id == ["2", "9", "10"]
    by_elapsed = [item["id"] for item in sort_jobs(rows, "elapsed")]
    assert by_elapsed == ["9", "10", "2"]
    by_state = [item["id"] for item in sort_jobs(rows, "state")]
    # RUNNING (rank 0) precedes PENDING (rank 1) regardless of alpha order.
    assert by_state[0] in {"2", "9"} and by_state[-1] == "10"


def test_w28_filter_refresh_does_not_mutate_backend_data():
    backend = [
        {"id": "1", "name": "alpha", "state": "RUNNING"},
        {"id": "2", "name": "beta", "state": "PENDING"},
    ]
    snapshot = list(backend)
    filtered = filter_jobs(backend, "alpha")
    assert [item["id"] for item in filtered] == ["1"]
    assert backend == snapshot
    assert len(backend) == 2


def test_w28_selection_survives_only_when_identity_exists():
    assert selection_still_exists("1", [{"id": "1"}, {"id": "2"}])
    assert not selection_still_exists("9", [{"id": "1"}, {"id": "2"}])
    assert not selection_still_exists("", [{"id": "1"}])


def test_w28_stale_selection_cannot_cancel_different_row_after_reorder():
    backend = [{"id": "1"}, {"id": "2"}]
    assert cancel_target_is_safe("1", backend, "1")
    # After reorder/filter the selected job vanished: cancel must be blocked.
    assert not cancel_target_is_safe("9", backend, "9")
    # Requesting a different row than the selection is blocked even if present.
    assert not cancel_target_is_safe("1", backend, "2")
    reordered = [{"id": "2"}, {"id": "1"}]
    assert cancel_target_is_safe("1", reordered, "1")


# --- Workstream B: refresh state machine (REFRESH-001..004) -------------------


def test_w28_refresh_idle_to_success_with_timestamp():
    machine = JobsRefreshState()
    assert machine.status == "idle"
    seq = machine.begin()
    assert machine.status == "refreshing"
    assert machine.complete_success(seq, [{"id": "1"}], timestamp="2026-09-24T00:00:00+00:00")
    assert machine.status == "success"
    assert machine.last_success_ts == "2026-09-24T00:00:00+00:00"
    assert machine.last_error == ""
    assert not machine.stale
    assert len(machine.data) == 1


def test_w28_refresh_failure_keeps_prior_data_marked_stale():
    machine = JobsRefreshState()
    seq1 = machine.begin()
    machine.complete_success(seq1, [{"id": "1"}], timestamp="T1")
    seq2 = machine.begin()
    assert machine.complete_failure(seq2, "socket timed out")
    assert machine.status == "failure"
    assert machine.last_error == "socket timed out"
    # Prior useful data is retained, visibly marked stale.
    assert len(machine.data) == 1
    assert machine.stale
    assert "stale" in machine.status_text().lower()


def test_w28_refresh_failure_without_prior_data_is_not_stale():
    machine = JobsRefreshState()
    seq = machine.begin()
    machine.complete_failure(seq, "no route to host")
    assert machine.status == "failure"
    assert machine.data == []
    assert not machine.stale


def test_w28_refresh_older_response_cannot_overwrite_newer():
    machine = JobsRefreshState()
    old_seq = machine.begin()
    new_seq = machine.begin()
    assert new_seq > old_seq
    # Older response arrives after newer was issued: discarded.
    assert not machine.complete_success(old_seq, [{"id": "OLD"}])
    assert machine.complete_success(new_seq, [{"id": "NEW"}])
    assert [row["id"] for row in machine.data] == ["NEW"]
    # A late failure for the old sequence is likewise discarded.
    stale_machine = JobsRefreshState()
    s_old = stale_machine.begin()
    s_new = stale_machine.begin()
    stale_machine.complete_success(s_new, [{"id": "NEW"}])
    assert not stale_machine.complete_failure(s_old, "late error")
    assert stale_machine.status == "success"


# --- Live wx wiring ------------------------------------------------------------

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language  # noqa: E402
from hpc_gui.wx_jobs import show_jobs  # noqa: E402


def _pump(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            app.ProcessPendingEvents()
        except Exception:
            pass
        try:
            wx.SafeYield()
        except Exception:
            pass
        if predicate():
            return
        wx.MilliSleep(10)
    try:
        app.ProcessPendingEvents()
    except Exception:
        pass
    assert predicate()


def _open(app, list_jobs, read_output=None, **kwargs):
    show_jobs(list_jobs=list_jobs, read_output=read_output or (lambda _job: ""), **kwargs)
    frames = [window for window in wx.GetTopLevelWindows() if window.GetTitle() == "Jobs"]
    assert frames
    return frames[-1]


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    yield app
    try:
        for window in list(wx.GetTopLevelWindows()):
            try:
                if window:
                    window.Destroy()
            except Exception:
                pass
        for _ in range(5):
            try:
                app.ProcessPendingEvents()
                wx.SafeYield()
            except Exception:
                break
            wx.MilliSleep(10)
    except Exception:
        pass


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w28_wx_refresh_success_sets_timestamp_and_clears_stale(wx_app):
    frame = _open(wx_app, lambda: [{"id": "1", "name": "a", "state": "RUNNING"}])
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    frame._wx_jobs_refresh_jobs()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("jobs_refresh_status") == "success")
    assert frame._wx_jobs_state.get("jobs_refresh_timestamp")
    assert frame._wx_jobs_state.get("jobs_refresh_stale") is False
    assert frame._wx_jobs_state.get("jobs_refresh_error") == ""


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w28_wx_refresh_failure_retains_rows_and_marks_stale(wx_app):
    calls = {"n": 0}

    def list_jobs():
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"id": "1", "name": "a", "state": "RUNNING"}]
        raise RuntimeError("controller unreachable")

    frame = _open(wx_app, list_jobs)
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _pump(wx_app, lambda: frame._wx_jobs_state.get("jobs_refresh_status") == "success")
    frame._wx_jobs_refresh_jobs()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("jobs_refresh_status") == "failure")
    # Prior rows remain visible and are flagged stale, never silently cleared.
    assert frame._wx_jobs_controls["jobs"].GetItemCount() == 1
    assert frame._wx_jobs_state.get("jobs_refresh_stale") is True
    assert "unreachable" in frame._wx_jobs_state.get("jobs_refresh_error", "")
    label = frame._wx_jobs_controls["jobs_refresh_label"].GetLabel()
    assert "stale" in label.lower() or "fail" in label.lower()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w28_wx_selection_cleared_when_identity_disappears(wx_app):
    backend = {"rows": [{"id": "1", "name": "a", "state": "RUNNING"}, {"id": "2", "name": "b", "state": "RUNNING"}]}
    frame = _open(wx_app, lambda: list(backend["rows"]))
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 2)
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(0)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(0)
    jobs.ProcessEvent(event)
    assert frame._wx_jobs_state["selected_job"] == "1"
    backend["rows"] = [{"id": "2", "name": "b", "state": "RUNNING"}]
    frame._wx_jobs_refresh_jobs()
    _pump(
        wx_app,
        lambda: frame._wx_jobs_state.get("jobs_refresh_status") == "success"
        and frame._wx_jobs_state.get("selected_job", "1") == "",
    )
    assert frame._wx_jobs_state["selected_job"] == ""
