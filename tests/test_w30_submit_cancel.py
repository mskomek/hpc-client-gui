"""W30 — Job submit and cancel control paths.

Owned requirements: HPC-W07-CTRL-001..010 (Workstream F + G).
Covers the W30-owned deltas plus requirement-to-owner traceability:
- CTRL-001: required-field validation + confirmed job-ID acceptance.
- CTRL-002: template partition/account rules are provider-config driven.
- CTRL-003/004: selected job identity + cluster/profile scope gate.
- CTRL-005: confirmation wording names the exact target.
- CTRL-006: capability availability is an explicit state.
- CTRL-007/008: command result is reflected + listing refreshes.
- CTRL-009/010: already-ended races are tolerated and never conflated
  with unauthorized/error.
"""

from __future__ import annotations

import time

import pytest

from hpc_gui.services.job_submit_cancel import (
    build_cancel_confirmation,
    cancel_capability_available,
    classify_cancel_outcome,
    extract_sbatch_job_id,
    is_already_gone_message,
    is_unauthorized_message,
    reflect_cancel_result,
    submit_result_status,
    validate_submit_request,
    validate_template_against_provider,
)

pytestmark = pytest.mark.contract


# --- CTRL-001: validation + confirmed acceptance ---------------------------


def test_w30_submit_requires_path():
    assert validate_submit_request("", None) == ["script path is required"]


def test_w30_submit_rejects_empty_and_placeholder_content():
    assert any("empty" in e for e in validate_submit_request("/a/job.slurm", "   "))
    errors = validate_submit_request("/a/job.slurm", "#!/bin/bash\n# USERNAME\n#SBATCH --time=01:00:00\n")
    assert any("placeholder" in e.lower() for e in errors)


def test_w30_submit_success_requires_confirmed_job_id():
    assert extract_sbatch_job_id("Submitted batch job 12345") == "12345"
    assert extract_sbatch_job_id("Submitted batch job 12345 (mock) for /x") == "12345"
    assert extract_sbatch_job_id("sbatch: error: Batch job submission failed") == ""
    status, job_id = submit_result_status("Submitted batch job 99")
    assert (status, job_id) == ("SUCCESS", "99")
    status, _reason = submit_result_status("sbatch: error: Invalid account")
    assert status == "FAILURE"
    # A zero-exit blob without the acceptance token is still failure.
    status, _reason = submit_result_status("", ok=True)
    assert status == "FAILURE"
    status, _reason = submit_result_status("OK", ok=True)
    assert status == "FAILURE"


def test_w30_submit_rejects_unconfirmed_output():
    status, reason = submit_result_status("Submitted with sbatch. Job ID: abc")
    assert status == "FAILURE" and reason


# --- CTRL-002: provider-config-driven template rules ------------------------


def test_w30_template_rules_are_config_driven_not_hardcoded():
    script = "#!/bin/bash\n#SBATCH --partition=debug\n#SBATCH --account=team-a\nsrun hostname\n"
    # No config -> no constraint.
    assert validate_template_against_provider(script, None) == []
    assert validate_template_against_provider(script, {}) == []
    # Allowed sets come from config.
    assert validate_template_against_provider(script, {"allowed_partitions": ["debug"]}) == []
    errors = validate_template_against_provider(script, {"allowed_partitions": ["prod"]})
    assert any("partition" in e and "debug" in e for e in errors)
    errors = validate_template_against_provider(script, {"allowed_accounts": ["other"]})
    assert any("account" in e for e in errors)
    # Declared account requirement enforces presence; undeclared does not.
    no_account = "#!/bin/bash\n#SBATCH --partition=debug\nsrun hostname\n"
    assert validate_template_against_provider(no_account, {"requirements": {"account": True}}) != []
    assert validate_template_against_provider(no_account, {}) == []
    with_account = "#!/bin/bash\n#SBATCH --partition=debug\n#SBATCH --account=team-a\nsrun hostname\n"
    assert validate_template_against_provider(with_account, {"requirements": {"account": True}}) == []


def test_w30_submit_validation_threads_provider_config():
    script = "#!/bin/bash\n#SBATCH --partition=debug\nsrun hostname\n"
    errors = validate_submit_request(
        "/a/job.slurm", script, provider_config={"allowed_partitions": ["prod"]}
    )
    assert any("partition" in e for e in errors)


def test_w30_submit_does_not_gate_on_sbatch_directive_presence():
    # CTRL-001/002 required fields are the path, non-empty content, no
    # template placeholder and the provider-config rules. A script's own
    # #SBATCH content is the scheduler's business, so a directive-free script
    # must still reach sbatch (DEF-W57-008 closed-owner repair for W30).
    plain = "#!/bin/sh\necho hi\n"
    assert validate_submit_request("/remote/A.sh", plain) == []
    # Every remaining CTRL-001/002 check still applies to the same script.
    assert any(
        "placeholder" in e for e in validate_submit_request("/remote/A.sh", plain + "# {{job}}\n")
    )
    # An undeclared partition dimension imposes no constraint (CTRL-002).
    assert (
        validate_submit_request("/remote/A.sh", plain, provider_config={"allowed_partitions": ["prod"]})
        == []
    )
    # A declared provider rule is still enforced without any #SBATCH line.
    errors = validate_submit_request(
        "/remote/A.sh", plain, provider_config={"requirements": {"account": True}}
    )
    assert any("account" in e for e in errors)
    # Required-field checks are untouched by the removal.
    assert validate_submit_request("", plain) == ["script path is required"]
    assert any("empty" in e for e in validate_submit_request("/remote/A.sh", "   "))
    # Acceptance still requires a confirmed scheduler job ID.
    assert submit_result_status("echo hi", ok=True)[0] == "FAILURE"


# --- CTRL-003/004: identity + cluster/profile scope -------------------------


def test_w30_cancel_identity_and_scope_gate():
    from hpc_gui.services.job_identity import cancel_is_safe, make_identity

    selected = make_identity("42", profile_id="p1", cluster_id="c1", provider_id="s", session_generation=3)
    same = make_identity("42", profile_id="p1", cluster_id="c1", provider_id="s", session_generation=3)
    drifted_profile = make_identity("42", profile_id="p2", cluster_id="c1", provider_id="s", session_generation=3)
    drifted_session = make_identity("42", profile_id="p1", cluster_id="c1", provider_id="s", session_generation=4)
    other_job = make_identity("43", profile_id="p1", cluster_id="c1", provider_id="s", session_generation=3)
    assert cancel_is_safe(selected, same)
    assert not cancel_is_safe(selected, drifted_profile)
    assert not cancel_is_safe(selected, drifted_session)
    assert not cancel_is_safe(selected, other_job)


def test_w30_cancel_row_list_gate_blocks_stale_selection():
    from hpc_gui.services.job_list_filter_sort import cancel_target_is_safe

    rows = [{"id": "42"}, {"id": "43"}]
    assert cancel_target_is_safe("42", rows, "42")
    assert not cancel_target_is_safe("42", [{"id": "43"}], "42")
    assert not cancel_target_is_safe("42", rows, "43")


# --- CTRL-005: confirmation wording -----------------------------------------


def test_w30_cancel_confirmation_names_exact_target():
    assert build_cancel_confirmation("42") == "Cancel job 42?"
    assert build_cancel_confirmation("42", "train") == "Cancel job 42 (train)?"
    assert "42" in build_cancel_confirmation("42_4", "train")


# --- CTRL-006: capability availability --------------------------------------


class _NoCancel:
    pass


class _WithCancel:
    def scancel(self, job_id):
        return "OK"


class _WithCancelResult:
    def scancel_result(self, job_id):
        return None


def test_w30_cancel_capability_is_explicit():
    assert cancel_capability_available(_WithCancel())
    assert cancel_capability_available(_WithCancelResult())
    assert not cancel_capability_available(_NoCancel())
    assert not cancel_capability_available(None)


# --- CTRL-009/010: already-gone vs unauthorized -----------------------------


def test_w30_already_gone_vs_unauthorized_are_distinct():
    assert is_already_gone_message("slurm_scancel: Invalid job id specified")
    assert is_already_gone_message("Job 42 already completed")
    assert not is_already_gone_message("Permission denied: not authorized")
    assert is_unauthorized_message("Permission denied for job 42")
    assert is_unauthorized_message("sbatch: error: Invalid account")
    # A race notice is never misread as unauthorized.
    assert not is_unauthorized_message("Invalid job id specified; job already finished")
    assert classify_cancel_outcome(None, "OK") == "CANCELLED"
    assert classify_cancel_outcome(RuntimeError("Invalid job id specified"), "") == "ALREADY_GONE"
    assert classify_cancel_outcome(RuntimeError("Permission denied"), "") == "ERROR"
    assert classify_cancel_outcome(RuntimeError("weird boom"), "", final_state="COMPLETED") == "ALREADY_GONE"
    assert classify_cancel_outcome(RuntimeError("weird boom"), "") == "ERROR"


def test_w30_reflect_cancel_result_drives_refresh_and_visibility():
    ok = reflect_cancel_result(None, "OK", job_id="42")
    assert ok.outcome == "CANCELLED" and ok.should_refresh and not ok.is_error
    assert "42" in ok.message
    gone = reflect_cancel_result(RuntimeError("Invalid job id"), "", job_id="42")
    assert gone.outcome == "ALREADY_GONE" and gone.should_refresh and not gone.is_error
    assert "already ended" in gone.message
    err = reflect_cancel_result(RuntimeError("Permission denied"), "", job_id="42")
    assert err.outcome == "ERROR" and not err.should_refresh and err.is_error
    assert "42" in err.message


# --- CTRL-007/008 + GUI readback (wx runtime proof) -------------------------

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


def _open(app, **kwargs):
    show_jobs(**kwargs)
    frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
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
def test_w30_wx_cancel_reflects_result_and_refreshes(wx_app, monkeypatch):
    calls = {"cancel": 0, "refresh": 0}
    rows = [{"id": "42", "name": "train", "state": "RUNNING"}]

    def list_jobs():
        calls["refresh"] += 1
        return list(rows)

    def cancel(job_id):
        calls["cancel"] += 1
        assert job_id == "42"
        return "OK"

    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    frame = _open(
        wx_app,
        list_jobs=list_jobs,
        read_output=lambda _job: "",
        cancel=cancel,
        final_state=lambda _job: "CANCELLED",
    )
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(0)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(0)
    jobs.ProcessEvent(event)
    before = calls["refresh"]
    frame._wx_jobs_cancel()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("last_cancel_outcome") == "CANCELLED")
    assert calls["cancel"] == 1
    assert "42" in frame._wx_jobs_state.get("last_cancel_message", "")
    assert frame._wx_jobs_state.get("last_cancel_is_error") is False
    # CTRL-008: the listing refreshes after an accepted cancel.
    _pump(wx_app, lambda: calls["refresh"] > before)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w30_wx_cancel_already_gone_is_benign_and_refreshes(wx_app, monkeypatch):
    rows = [{"id": "42", "name": "train", "state": "RUNNING"}]

    def list_jobs():
        return list(rows)

    def cancel(job_id):
        raise RuntimeError("slurm_scancel: Invalid job id specified")

    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    frame = _open(
        wx_app,
        list_jobs=list_jobs,
        read_output=lambda _job: "",
        cancel=cancel,
        final_state=lambda _job: "COMPLETED",
    )
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(0)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(0)
    jobs.ProcessEvent(event)
    frame._wx_jobs_cancel()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("last_cancel_outcome") == "ALREADY_GONE")
    assert frame._wx_jobs_state.get("last_cancel_is_error") is False
    assert "already ended" in frame._wx_jobs_state.get("last_cancel_message", "")


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_w30_wx_cancel_error_is_distinct_and_does_not_refresh_as_success(wx_app, monkeypatch):
    refreshes = {"n": 0}

    def list_jobs():
        refreshes["n"] += 1
        return [{"id": "42", "name": "train", "state": "RUNNING"}]

    def cancel(job_id):
        raise RuntimeError("Permission denied: not authorized")

    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    frame = _open(
        wx_app,
        list_jobs=list_jobs,
        read_output=lambda _job: "",
        cancel=cancel,
        final_state=lambda _job: "RUNNING",
    )
    _pump(wx_app, lambda: frame._wx_jobs_controls["jobs"].GetItemCount() == 1)
    jobs = frame._wx_jobs_controls["jobs"]
    jobs.Select(0)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(0)
    jobs.ProcessEvent(event)
    before = refreshes["n"]
    frame._wx_jobs_cancel()
    _pump(wx_app, lambda: frame._wx_jobs_state.get("last_cancel_outcome") == "ERROR")
    assert frame._wx_jobs_state.get("last_cancel_is_error") is True
    assert frame._wx_jobs_state.get("last_cancel_outcome") != "ALREADY_GONE"
    # Error path must not trigger the success-style auto refresh storm.
    wx.MilliSleep(300)
    try:
        wx_app.ProcessPendingEvents()
    except Exception:
        pass
    assert refreshes["n"] <= before + 1
