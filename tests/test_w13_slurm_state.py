"""W13 — Real Slurm, failure and cross-protocol state validation.

Laboratory: authorized containerized single-node Slurm (``hpclab``,
``127.0.0.1:2222``) for the external matrix plus the loopback fakes below,
which stand in only for the paramiko transport (same ``(code, stdout,
stderr)`` triples the real controller returned in ``EV-W13-BEFORE-001``).

Requirement map (all owned by W13, ``HPC-W03-SLURM-*``):
  013  Slurm list/details/submit/cancel where provider declares support
  016  parsing must prefer structured formats over human display text
  014/017..023  error handling / failure simulation
  024..028  state coherency (no stale/misleading views)

Counted W13 remediations:
  DEF-W13-001  headerless scheduler output lost its first data row
               (``_rows`` always dropped line 1 assuming a header).
  DEF-W13-002  empty successful scheduler output rendered as ``[exit=0]``,
               a pseudo-error token shown to users for an empty queue.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.services.slurm_models import parse_sacct, parse_squeue  # noqa: E402
from hpc_gui.services.slurm_ssh import SSHSlurmBackend, SlurmCommandResult  # noqa: E402

# Exact headerless bytes observed on the real lab controller
# (``squeue -h -u hpctest -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"`` with one RUNNING
# job; see EV-W13-BEFORE-001).
LAB_SINGLE_ROW = "4|short|w13probe|hpctest|RUNNING|0:03|1|1|None"
LAB_TWO_ROWS = (
    "4|short|w13probe|hpctest|RUNNING|0:03|1|1|None\n"
    "5|short|other|hpctest|PENDING|0:00|1|1|Priority"
)
LAB_SACCT_SINGLE_ROW = "4|w13probe|CANCELLED|00:00:03||0:0"


class _FakeSSH:
    """Minimal transport double: replays one real ``(code,out,err)`` triple."""

    def __init__(self, result):
        self.result = result
        self.commands: list[str] = []

    def run(self, command: str, **_kwargs):
        self.commands.append(command)
        return self.result


def _job_dicts(text: str) -> list[dict]:
    """Product chain: scheduler text -> structured rows -> wx row dicts."""
    from hpc_gui.wx_jobs import _parse_job_row

    return [
        _parse_job_row(
            {
                "id": job.job_id,
                "name": job.name,
                "state": job.state,
                "partition": job.partition,
                "elapsed": job.elapsed,
                "nodes": job.nodes,
                "cpus": job.cpus,
                "reason": job.reason,
            }
        )
        for job in parse_squeue(text)
    ]


# ---------------------------------------------------------------------------
# DEF-W13-001: headerless scheduler output keeps every data row
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.regression
@pytest.mark.semantic
def test_headerless_single_job_squeue_row_is_kept():
    """DEF-W13-001 / REQ HPC-W03-SLURM-013+016: one RUNNING row parses to one job."""
    jobs = parse_squeue(LAB_SINGLE_ROW)
    assert len(jobs) == 1
    assert jobs[0].job_id == "4"
    assert jobs[0].state == "RUNNING"
    assert jobs[0].raw == LAB_SINGLE_ROW


@pytest.mark.contract
@pytest.mark.regression
@pytest.mark.semantic
def test_headerless_multi_job_squeue_keeps_first_row():
    """DEF-W13-001: the first of N headerless rows is not discarded."""
    jobs = parse_squeue(LAB_TWO_ROWS)
    assert [job.job_id for job in jobs] == ["4", "5"]
    assert [job.state for job in jobs] == ["RUNNING", "PENDING"]


@pytest.mark.contract
@pytest.mark.semantic
def test_headed_squeue_still_skips_header():
    """CON-W13-001: headed output keeps skipping exactly the header row."""
    jobs = parse_squeue("JOBID|PARTITION|NAME|USER|ST|TIME\n" + LAB_SINGLE_ROW + "\n")
    assert [job.job_id for job in jobs] == ["4"]


@pytest.mark.contract
@pytest.mark.semantic
def test_banner_before_header_is_tolerated():
    """CON-W13-002: one MOTD/banner line ahead of the header is still tolerated."""
    jobs = parse_squeue(
        "Welcome to the cluster\nJOBID|PARTITION|NAME|USER|ST|TIME\n" + LAB_SINGLE_ROW + "\n"
    )
    assert [job.job_id for job in jobs] == ["4"]


@pytest.mark.contract
@pytest.mark.regression
@pytest.mark.semantic
def test_headerless_sacct_single_row_is_kept():
    """DEF-W13-001 / REQ HPC-W03-SLURM-013: one accounting row parses to one job."""
    jobs = parse_sacct(LAB_SACCT_SINGLE_ROW)
    assert len(jobs) == 1
    assert jobs[0].job_id == "4"
    assert jobs[0].state == "CANCELLED"


@pytest.mark.contract
@pytest.mark.semantic
def test_empty_scheduler_output_parses_to_no_jobs():
    """NEG-W13-001: empty output is zero jobs, never a phantom row."""
    assert parse_squeue("") == []
    assert parse_sacct("") == []


# ---------------------------------------------------------------------------
# DEF-W13-002: empty success renders as empty, failures keep diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.semantic
def test_empty_success_renders_empty_text_not_exit_token():
    """DEF-W13-002: an empty queue is ``\"\"``, not a pseudo-error ``[exit=0]``."""
    result = SlurmCommandResult(code=0, stdout="", stderr="")
    assert result.ok is True
    assert result.text == ""


@pytest.mark.unit
@pytest.mark.semantic
def test_failure_empty_output_keeps_exit_token():
    """NEG-W13-002: failures without output still carry a diagnostic token."""
    assert SlurmCommandResult(code=2, stdout="", stderr="").text == "[exit=2]"
    assert SlurmCommandResult(code=1, stdout="", stderr="boom").text == "boom"
    assert SlurmCommandResult(code=1, stdout="", stderr="boom").ok is False


@pytest.mark.unit
@pytest.mark.semantic
def test_squeue_failure_text_does_not_parse_as_job():
    """NEG-W13-003 (HPC-W03-SLURM-014/020): scheduler errors never become job rows."""
    ssh = _FakeSSH(
        (
            1,
            "",
            "squeue: error: Unable to contact slurm controller (connect failure)\n"
            "slurm_load_jobs error: Invalid job id specified",
        )
    )
    backend = SSHSlurmBackend(ssh)
    result = backend.squeue_result("hpctest")
    assert result.ok is False
    assert "Invalid job id" in result.message
    assert parse_squeue(result.text) == []


@pytest.mark.unit
@pytest.mark.semantic
def test_scontrol_unknown_job_result_is_not_ok():
    """NEG-W13-004 (HPC-W03-SLURM-014): unknown-job details fail with a message."""
    ssh = _FakeSSH((1, "", "slurm_load_jobs error: Invalid job id specified"))
    backend = SSHSlurmBackend(ssh)
    result = backend.scontrol_show_job_result("99999999")
    assert result.ok is False
    assert "Invalid job id" in result.message


@pytest.mark.unit
@pytest.mark.semantic
def test_sbatch_failure_result_is_not_ok():
    """NEG-W13-005 (HPC-W03-SLURM-021): failed submit is an error, not a job ID."""
    ssh = _FakeSSH((1, "", "sbatch: error: Batch job submission failed: Invalid partition"))
    backend = SSHSlurmBackend(ssh)
    result = backend.sbatch_result("/tmp/job.slurm")
    assert result.ok is False
    assert "Invalid partition" in result.message


@pytest.mark.unit
@pytest.mark.semantic
def test_cancel_empty_success_reports_ok():
    """CON-W13-003: silent scheduler cancel (exit 0, no output) reports ``OK``."""
    ssh = _FakeSSH((0, "", ""))
    assert SSHSlurmBackend(ssh).scancel("4") == "OK"


# ---------------------------------------------------------------------------
# GUI proof: real wx.App + Frame, real event dispatch, observable table
# ---------------------------------------------------------------------------


def _pump_until(predicate, timeout_s=20.0):
    import time as _time

    import wx

    deadline = _time.monotonic() + timeout_s
    while _time.monotonic() < deadline:
        try:
            wx.Yield()
        except Exception:
            pass
        try:
            if predicate():
                return True
        except Exception:
            pass
        _time.sleep(0.05)
    try:
        return bool(predicate())
    except Exception:
        return False


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.semantic
def test_wx_jobs_panel_lists_headerless_lab_job():
    """GUI-001 (DEF-W13-001 / HPC-W03-SLURM-013+028): the RUNNING lab job is visible.

    Real ``wx.App`` + ``Frame`` + ``build_jobs_panel``; the Refresh click
    travels through a real posted ``wx`` command event and the worker thread;
    the observable jobs table is the verdict. Pre-fix the headerless row was
    dropped by the parser, so the table stayed empty.
    """
    import wx

    from hpc_gui.wx_jobs import build_jobs_panel

    ssh = _FakeSSH((0, LAB_SINGLE_ROW + "\n", ""))
    backend = SSHSlurmBackend(ssh)

    def _list_jobs():
        return _job_dicts(backend.squeue("hpctest"))

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w13-lab-job-visible")
    try:
        host = build_jobs_panel(frame, list_jobs=_list_jobs)
        ctrls = host._wx_jobs_controls
        table, refresh = ctrls["jobs"], ctrls["refresh"]
        refresh.SetFocus()
        evt = wx.CommandEvent(wx.wxEVT_BUTTON, refresh.GetId())
        evt.SetEventObject(refresh)
        wx.PostEvent(refresh, evt)
        assert _pump_until(lambda: table.GetItemCount() == 1, timeout_s=20.0)
        assert table.GetItemText(0) == "4"
        assert table.GetItem(0, 2).GetText() == "RUNNING"
    finally:
        frame.Destroy()
        time.sleep(0.2)
        try:
            wx.Yield()
        except Exception:
            pass


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.semantic
def test_wx_jobs_panel_empty_queue_shows_no_rows_and_no_exit_token():
    """GUI-002 (DEF-W13-002 / HPC-W03-SLURM-028): empty queue, honest empty view.

    The full product chain (``SSHSlurmBackend.squeue`` -> ``parse_squeue`` ->
    panel) must show zero rows for an empty queue, and the scheduler text fed
    to the view must not contain the ``[exit=0]`` pseudo-error token.
    """
    import wx

    from hpc_gui.wx_jobs import build_jobs_panel

    ssh = _FakeSSH((0, "", ""))
    backend = SSHSlurmBackend(ssh)

    def _list_jobs():
        text = backend.squeue("hpctest")
        assert text == "", f"empty queue must render empty, got {text!r}"
        assert "[exit=" not in text
        return _job_dicts(text)

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w13-lab-queue-empty")
    try:
        host = build_jobs_panel(frame, list_jobs=_list_jobs)
        ctrls = host._wx_jobs_controls
        table, refresh = ctrls["jobs"], ctrls["refresh"]
        evt = wx.CommandEvent(wx.wxEVT_BUTTON, refresh.GetId())
        evt.SetEventObject(refresh)
        wx.PostEvent(refresh, evt)
        assert _pump_until(lambda: table.GetItemCount() == 0, timeout_s=20.0)
        assert table.GetItemCount() == 0
    finally:
        frame.Destroy()
        time.sleep(0.2)
        try:
            wx.Yield()
        except Exception:
            pass
