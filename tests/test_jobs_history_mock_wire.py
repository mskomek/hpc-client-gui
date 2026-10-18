"""Jobs list round trip over the local mock Slurm SSH server."""

from __future__ import annotations

import sys
import time

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

from hpc_gui.services.slurm_ssh import SSHSlurmBackend  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402
from hpc_gui.wx_shell_jobs import _jobs_callbacks  # noqa: E402


def test_jobs_list_round_trip_shows_live_and_finished_jobs(tmp_path):
    import pytest

    wx = pytest.importorskip("wx")
    from hpc_gui.wx_jobs import show_jobs

    with MockSSHServer(tmp_path) as server:
        ssh = SSHClientWrapper()
        ssh.connect(
            SSHConnInfo(
                host="127.0.0.1",
                port=server.port,
                username=MOCK_USERNAME,
                password=MOCK_PASSWORD,
                host_key_policy="accept-new",
                known_hosts_path=str(tmp_path / "known_hosts"),
            )
        )
        try:
            backend = SSHSlurmBackend(ssh)
            state = {
                "session": {
                    "slurm": backend,
                    "profile": {"username": MOCK_USERNAME, "id": "mock-cluster"},
                }
            }
            callbacks = _jobs_callbacks(state, None, None)
            result = callbacks["list_jobs"]()
            app = wx.App.Get() or wx.App(False)
            show_jobs(**callbacks)
            frames = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_jobs_controls")]
            assert frames
            frame = frames[-1]
            deadline = time.monotonic() + 10
            while frame._wx_jobs_controls["jobs"].GetItemCount() != 4 and time.monotonic() < deadline:
                app.ProcessPendingEvents()
                wx.SafeYield()
                wx.MilliSleep(10)
            jobs = frame._wx_jobs_controls["jobs"]
            assert [jobs.GetItemText(index) for index in range(4)] == [
                "6810497_[0-3%4]", "12345", "12344", "12343"
            ]

            # Older saved profiles may use default Slurm table output.
            legacy_backend = SSHSlurmBackend(
                ssh,
                system_settings={
                    "squeue_command": "squeue -u {user}",
                    "sacct_command": "sacct -u {user}",
                },
            )
            state["session"]["slurm"] = legacy_backend
            state["session"]["profile"]["id"] = "mock-legacy"
            legacy = _jobs_callbacks(state, None, None)["list_jobs"]()
            assert [(row["job_id"], row["state"]) for row in legacy["jobs"]] == [
                ("6810497_[0-3%4]", "PENDING"),
                ("12345", "R"),
                ("12344", "COMPLETED"),
                ("12343", "FAILED"),
            ]
            previous_seq = frame._wx_jobs_state.get("jobs_refresh_applied_seq", 0)
            frame._wx_jobs_refresh_jobs()
            deadline = time.monotonic() + 10
            while frame._wx_jobs_state.get("jobs_refresh_applied_seq", 0) <= previous_seq and time.monotonic() < deadline:
                app.ProcessPendingEvents()
                wx.SafeYield()
                wx.MilliSleep(10)
            assert [jobs.GetItemText(index) for index in range(4)] == [
                "6810497_[0-3%4]", "12345", "12344", "12343"
            ]

            # Published TRUBA profiles use a 9-column squeue command and the
            # older 7-column sacct accounting format.
            truba_backend = SSHSlurmBackend(
                ssh,
                system_settings={
                    "squeue_command": (
                        'squeue -h -u {user} '
                        '-o "%i|%P|%j|%u|%T|%M|%D|%C|%R"'
                    ),
                    "sacct_command": (
                        "sacct -n -P -u {user} "
                        "--format=JobIDRaw,JobName,State,Elapsed,MaxRSS,AllocTRES,ExitCode"
                    ),
                },
            )
            state["session"]["slurm"] = truba_backend
            state["session"]["profile"]["id"] = "truba"
            truba_callbacks = _jobs_callbacks(state, None, None)
            truba_result = truba_callbacks["list_jobs"]()
            assert [(row["job_id"], row["state"]) for row in truba_result["jobs"]] == [
                ("6810497_[0-3%4]", "PENDING"),
                ("12345", "RUNNING"),
                ("12344", "COMPLETED"),
                ("12343", "FAILED"),
            ]
            previous_seq = frame._wx_jobs_state.get("jobs_refresh_applied_seq", 0)
            frame._wx_jobs_refresh_jobs()
            deadline = time.monotonic() + 10
            while frame._wx_jobs_state.get("jobs_refresh_applied_seq", 0) <= previous_seq and time.monotonic() < deadline:
                app.ProcessPendingEvents()
                wx.SafeYield()
                wx.MilliSleep(10)
            assert [jobs.GetItemText(index) for index in range(4)] == [
                "6810497_[0-3%4]", "12345", "12344", "12343"
            ]
        finally:
            for window in list(wx.GetTopLevelWindows()):
                try:
                    window.Destroy()
                except Exception:
                    pass
            try:
                wx.SafeYield()
            except Exception:
                pass
            ssh.close()

    assert [(row["job_id"], row["state"]) for row in result["jobs"]] == [
        ("6810497_[0-3%4]", "PENDING"),
        ("12345", "RUNNING"),
        ("12344", "COMPLETED"),
        ("12343", "FAILED"),
    ]
    assert result["history_stale"] is False


def test_mock_wire_keeps_array_heterogeneous_and_multiword_reason_shapes(tmp_path):
    with MockSSHServer(tmp_path) as server:
        ssh = SSHClientWrapper()
        ssh.connect(
            SSHConnInfo(
                host="127.0.0.1",
                port=server.port,
                username=MOCK_USERNAME,
                password=MOCK_PASSWORD,
                host_key_policy="accept-new",
                known_hosts_path=str(tmp_path / "known_hosts"),
            )
        )
        try:
            backend = SSHSlurmBackend(
                ssh,
                system_settings={
                    "squeue_command": "squeue --mock-shapes -u {user}",
                    "sacct_command": "sacct --mock-shapes -u {user}",
                },
            )
            state = {
                "session": {
                    "slurm": backend,
                    "profile": {"username": MOCK_USERNAME, "id": "mock-shapes"},
                }
            }
            result = _jobs_callbacks(state, None, None)["list_jobs"]()
            jobs = result["jobs"]
            assert [(job["job_id"], job["state"]) for job in jobs] == [
                ("93+0", "R"),
                ("1080_[5-1024]", "PD"),
                ("90003", "CANCELLED"),
            ]
            assert jobs[1]["reason"] == "(ReqNodeNotAvail, UnavailableNodes:nid[001-002])"
            assert jobs[0]["nodes"] == "2"
            assert result["history_stale"] is False
        finally:
            ssh.close()
