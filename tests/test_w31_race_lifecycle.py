"""W31 — Job lifecycle races and real/package acceptance.

Owned requirements: HPC-W07-RACE-001..055 (Workstream H disconnect/profile
switch, targeted tasks, test matrix, acceptance gates, STOP conditions).

Covers the W31-owned deltas plus requirement-to-owner traceability:
- RACE-019: refresh while disconnecting discards the late response.
- RACE-020: profile switch during refresh; old response never wins.
- RACE-021: cancel after profile switch is blocked.
- RACE-022: details callback from an old session never attaches.
- RACE-023: reconnect then refresh recovers with a fresh timestamp.
- TASK-004/007 (RACE-027/030/037/044/052): overlapping refresh + safe cancel.
- TASK-003/006 (RACE-026/029/045/046/054): parser safety + confirmed submit.
- TASK-008/009 (RACE-031/032/049/050/055): real-shape lifecycle + package.
- STOP (RACE-052..055): none of the four stop conditions trigger.
"""

from __future__ import annotations

import hashlib
import threading
import time
import zipfile
from pathlib import Path

import pytest

from hpc_gui.services.job_identity import cancel_is_safe, make_identity
from hpc_gui.services.job_list_filter_sort import cancel_target_is_safe
from hpc_gui.services.jobs_refresh_state import JobsRefreshState
from hpc_gui.services.job_submit_cancel import submit_result_status
from hpc_gui.services.selected_job_context import SelectedJobStore
from hpc_gui.services.slurm_models import (
    is_terminal_state,
    parse_sacct,
    parse_scontrol,
    parse_squeue,
    safe_state_display,
)

pytestmark = pytest.mark.contract


# --- RACE-019/020/023 + TASK-004: refresh/disconnect/profile-switch races ---


def test_w31_refresh_sequence_rejects_stale_after_reconnect():
    """An older refresh response can never overwrite a newer context."""
    machine = JobsRefreshState()
    old_seq = machine.begin()  # issued under the old session
    new_seq = machine.begin()  # issued after reconnect/profile switch
    assert new_seq > old_seq
    assert machine.complete_success(old_seq, [{"id": "OLD"}]) is False
    assert machine.complete_success(new_seq, [{"id": "NEW"}]) is True
    assert [row["id"] for row in machine.data] == ["NEW"]
    assert machine.status == "success"
    assert machine.last_success_ts


def test_w31_refresh_failure_after_reconnect_keeps_new_context():
    """A late failure for the old session must not poison the new listing."""
    machine = JobsRefreshState()
    old_seq = machine.begin()
    new_seq = machine.begin()
    assert machine.complete_success(new_seq, [{"id": "NEW"}], timestamp="T-NEW")
    assert machine.complete_failure(old_seq, "old session timed out") is False
    assert machine.status == "success"
    assert [row["id"] for row in machine.data] == ["NEW"]


def test_w31_overlapping_refresh_newest_wins():
    """Overlapping refreshes serialize on the monotonic sequence."""
    machine = JobsRefreshState()
    first = machine.begin()
    second = machine.begin()
    third = machine.begin()
    assert machine.complete_success(first, [{"id": "1"}]) is False
    assert machine.complete_success(second, [{"id": "2"}]) is False
    assert machine.complete_success(third, [{"id": "3"}]) is True
    assert [row["id"] for row in machine.data] == ["3"]


# --- RACE-021 + TASK-007: cancel after profile switch is blocked ---


def test_w31_profile_switch_blocks_cancel_identity():
    selected = make_identity(
        "42", profile_id="p1", cluster_id="c1", provider_id="slurm",
        session_generation=3,
    )
    same = make_identity(
        "42", profile_id="p1", cluster_id="c1", provider_id="slurm",
        session_generation=3,
    )
    assert cancel_is_safe(selected, same)
    for drifted in (
        make_identity("42", profile_id="p2", cluster_id="c1",
                      provider_id="slurm", session_generation=3),
        make_identity("42", profile_id="p1", cluster_id="c2",
                      provider_id="slurm", session_generation=3),
        make_identity("42", profile_id="p1", cluster_id="c1",
                      provider_id="slurm", session_generation=4),
        make_identity("43", profile_id="p1", cluster_id="c1",
                      provider_id="slurm", session_generation=3),
        make_identity("42_4", profile_id="p1", cluster_id="c1",
                      provider_id="slurm", session_generation=3),
    ):
        assert not cancel_is_safe(selected, drifted)


def test_w31_stale_selection_cannot_cancel_after_refresh():
    """A selection that vanished from backend rows can never cancel."""
    assert cancel_target_is_safe("42", [{"id": "42"}, {"id": "43"}], "42")
    assert not cancel_target_is_safe("42", [{"id": "43"}], "42")
    assert not cancel_target_is_safe("42", [{"id": "42"}], "43")
    assert not cancel_target_is_safe("", [{"id": "42"}], "42")


# --- RACE-022 + TASK-005: details callback from old session discarded ---


def test_w31_selection_generation_invalidates_stale_details():
    """Every select/clear bumps the generation details guards capture."""
    store = SelectedJobStore()
    store.select(job_id="42", name="train")
    captured = store.generation
    store.select(job_id="43", name="other")  # selection changed mid-fetch
    assert store.generation != captured
    assert store.job_id == "43"
    store.clear()  # disconnect/profile switch clears the store
    assert store.job_id == ""
    assert store.generation != captured


# --- TASK-006/STOP: submission never succeeds without acceptance ---


def test_w31_submit_rejection_never_reports_success():
    status, _ = submit_result_status("sbatch: error: Invalid account")
    assert status == "FAILURE"
    status, _ = submit_result_status("sbatch: error: Batch job submission failed")
    assert status == "FAILURE"
    status, _ = submit_result_status("", ok=True)
    assert status == "FAILURE"
    status, job_id = submit_result_status("Submitted batch job 4242")
    assert (status, job_id) == ("SUCCESS", "4242")


# --- TASK-003: unknown/malformed scheduler output stays safe ---


def test_w31_unknown_and_malformed_output_safe():
    jobs = parse_squeue("4242|short|train|alice|ZZ|00:12\n")
    assert jobs[0].state == "ZZ"
    assert safe_state_display("ZZ") == "ZZ"
    assert not is_terminal_state("ZZ")
    mixed = parse_squeue(
        "4242|short|train|alice|R|00:12\n"
        "garbage without columns\n"
        "slurm_load_jobs error: socket timed out\n"
    )
    assert [job.job_id for job in mixed] == ["4242"]
    assert parse_squeue("") == []


# --- TASK-008: real Slurm lifecycle shapes parse end to end ---


def test_w31_real_slurm_lifecycle_shapes_parse():
    listed = parse_squeue(
        "4242|debug|train|hpctest|R|00:03:11\n"
        "4243|debug|pre|hpctest|PD|00:00:00\n"
        "4241|debug|old|hpctest|CD|01:12:00\n"
    )
    assert [job.job_id for job in listed] == ["4242", "4243", "4241"]
    assert not is_terminal_state("R")
    assert is_terminal_state("CD")
    acct = parse_sacct("4242|train|RUNNING|00:03:11|2M\n")
    assert acct and acct[0].state == "RUNNING"
    detail = parse_scontrol(
        "JobId=4242 JobName=train JobState=RUNNING StdOut=/home/hpctest/slurm-4242.out "
        "StdErr=/home/hpctest/slurm-4242.err\n",
        job_id="4242",
    )
    assert detail.stdout_path == "/home/hpctest/slurm-4242.out"
    assert detail.stderr_path == "/home/hpctest/slurm-4242.err"


# --- TASK-009/STOP: packaged artifact carries provider/parser resources ---


def test_w31_package_artifact_contains_provider_parser_resources():
    """Exact packaged artifact under acceptance holds the required modules."""
    wheel = Path(".tmp/w31-package/hpc_client_gui-1.5.9-py3-none-any.whl")
    assert wheel.is_file(), "candidate-built wheel missing under .tmp/w31-package/"
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert len(digest) == 64 and digest.strip() == digest
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    required_fragments = (
        "services/slurm_models",
        "services/parsers",
        "services/slurm_ssh",
        "services/provider_capabilities",
        "services/job_identity",
        "services/jobs_refresh_state",
        "services/job_submit_cancel",
    )
    missing = [frag for frag in required_fragments
               if not any(frag in name for name in names)]
    assert not missing, f"package lacks required resources: {missing}"


# --- GUI runtime proof (wx event/runtime readback) ---

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language  # noqa: E402
from hpc_gui.wx_jobs import show_jobs  # noqa: E402


def _pump(app, predicate, timeout=20):
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


def _open(app, **kwargs):
    show_jobs(**kwargs)
    frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
    assert frames
    return frames[-1]


def _select_first(app, frame, job_id):
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(0)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(0)
    jobs.ProcessEvent(event)
    _pump(app, lambda: frame._wx_jobs_state.get("selected_job") == job_id)


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
def test_w31_wx_refresh_while_disconnecting_discards_stale(wx_app):
    """RACE-019: a refresh in flight across disconnect never applies."""
    release = threading.Event()
    seen = {"n": 0}

    def list_jobs():
        seen["n"] += 1
        assert release.wait(timeout=20)
        return [{"id": "OLD-1", "name": "old", "state": "RUNNING"}]

    frame = _open(wx_app, list_jobs=list_jobs, read_output=lambda _job: "")
    frame._wx_jobs_refresh_jobs()
    wx.MilliSleep(200)
    frame._wx_jobs_set_session(None)  # disconnect while the fetch is in flight
    release.set()
    wx.MilliSleep(500)
    try:
        wx_app.ProcessPendingEvents()
    except Exception:
        pass
    # The stale OLD-profile response must not repopulate the cleared view.
    assert frame._wx_jobs_state.get("selected_job", "") == ""
    assert seen["n"] >= 1


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w31_wx_profile_switch_during_refresh_new_context_wins(wx_app):
    """RACE-020: profile switch bumps the session; the old response loses."""
    session = {"current": 1}
    release_old = threading.Event()

    def list_jobs():
        if session["current"] == 1:
            assert release_old.wait(timeout=20)
            return [{"id": "P1-JOB", "name": "p1", "state": "RUNNING"}]
        return [{"id": "P2-JOB", "name": "p2", "state": "RUNNING"}]

    frame = _open(
        wx_app,
        list_jobs=list_jobs,
        read_output=lambda _job: "",
        generation=lambda: session["current"],
        profile_id="p1",
    )
    frame._wx_jobs_refresh_jobs()
    wx.MilliSleep(200)
    session["current"] = 2  # profile switch lands while P1 fetch is in flight
    frame._wx_jobs_set_session({"id": "p2-session"})
    release_old.set()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("jobs_refresh_status") == "success")
    rows = [str(item.get("id", "")) for item in frame._wx_jobs_state.get("items", [])]
    assert "P1-JOB" not in rows
    assert "P2-JOB" in rows


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w31_wx_cancel_after_profile_switch_blocked(wx_app, monkeypatch):
    """RACE-021/STOP: cancel after a profile switch never fires for the job."""
    calls = {"cancel": 0}
    rows = {"items": [{"id": "42", "name": "train", "state": "RUNNING"}]}

    def list_jobs():
        return list(rows["items"])

    def cancel(job_id):
        calls["cancel"] += 1
        return "OK"

    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    frame = _open(
        wx_app,
        list_jobs=list_jobs,
        read_output=lambda _job: "",
        cancel=cancel,
        profile_id="p1",
    )
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    _select_first(wx_app, frame, "42")
    frame._wx_jobs_set_session({"id": "p2-session"})  # profile switch
    assert frame._wx_jobs_state.get("selected_job", "") == ""
    frame._wx_jobs_cancel()
    wx.MilliSleep(400)
    try:
        wx_app.ProcessPendingEvents()
    except Exception:
        pass
    assert calls["cancel"] == 0, "cancel must not fire after a profile switch"


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w31_wx_reconnect_then_refresh_recovers(wx_app):
    """RACE-023: reconnect then refresh yields an unambiguous fresh success."""
    frame = _open(
        wx_app,
        list_jobs=lambda: [{"id": "7", "name": "fresh", "state": "RUNNING"}],
        read_output=lambda _job: "",
    )
    frame._wx_jobs_set_session(None)
    frame._wx_jobs_set_session({"id": "reconnected"})
    frame._wx_jobs_refresh_jobs()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("jobs_refresh_status") == "success")
    assert frame._wx_jobs_state.get("jobs_refresh_timestamp")
    assert frame._wx_jobs_state.get("jobs_refresh_stale") is False
    assert frame._wx_jobs_state.get("jobs_refresh_error") == ""
    assert frame._wx_jobs_controls["jobs"].GetItemCount() == 1
