from hpc_gui.services.jobs_history import merge_job_sources, parse_sacct_history
from hpc_gui.wx_shell_jobs import _jobs_callbacks
from hpc_gui.config import storage
from hpc_gui.services.slurm_ssh import SSHSlurmBackend


def test_parse_sacct_history_omits_step_rows_and_keeps_array_tasks():
    rows = parse_sacct_history(
        "123|array|gpu|COMPLETED|00:10|1|4||0:0|2026-10-01T10:00:00|2026-10-01T10:10:00|/work|/work/out|/work/err\n"
        "123_1|array|gpu|FAILED|00:05|1|4||1:0|2026-10-01T10:01:00|2026-10-01T10:06:00|/work|/work/out_1|/work/err_1\n"
        "123_1.batch|batch|gpu|FAILED|00:05|1|4||1:0||||\n"
    )
    assert [row["job_id"] for row in rows] == ["123", "123_1"]
    assert rows[1]["exit_code"] == "1:0"
    assert rows[1]["end_time"] == "2026-10-01T10:06:00"


def test_merge_keeps_compact_pending_array_summary():
    from hpc_gui.services.jobs_history import merge_job_sources

    rows = merge_job_sources(
        [{"id": "6810497_[0-3%4]", "name": "dataset_solver", "state": "PENDING"}],
        [],
    )
    assert [(row["job_id"], row["state"]) for row in rows] == [
        ("6810497_[0-3%4]", "PENDING")
    ]


def test_history_keeps_array_and_heterogeneous_jobs_but_drops_steps():
    rows = parse_sacct_history(
        "1080_[5-1024]|wide-array|gpu|FAILED|00:01|1|4||1:0|2026-10-01T10:00:00|2026-10-01T10:01:00||||\n"
        "93+0|heterogeneous|gpu|CANCELLED|00:01|1|4||0:0|2026-10-01T10:00:00|2026-10-01T10:01:00||||\n"
        "93+0.batch|batch|gpu|CANCELLED|00:01|1|4||0:0|||||\n"
        "93+1.extern|extern|gpu|CANCELLED|00:01|1|4||0:0|||||\n"
    )
    assert [row["job_id"] for row in rows] == ["1080_[5-1024]", "93+0"]


def test_merge_prefers_queue_row_and_sorts_active_then_recent_terminal():
    rows = merge_job_sources(
        [{"id": "12", "name": "live", "state": "RUNNING", "submit_time": "2026-10-18T09:00:00"}],
        [
            {"id": "11", "name": "old", "state": "FAILED", "end_time": "2026-10-10T10:00:00"},
            {"id": "12", "name": "accounting", "state": "RUNNING"},
            {"id": "13", "name": "new", "state": "CANCELLED", "end_time": "2026-10-17T10:00:00"},
            {"id": "13.batch", "state": "CANCELLED"},
        ],
    )
    assert [row["job_id"] for row in rows] == ["12", "13", "11"]
    assert rows[0]["name"] == "live"


def test_list_jobs_uses_and_retains_cached_sacct_when_temporarily_unavailable(monkeypatch):
    class Slurm:
        calls = 0
        queue = "9|cpu|live|alice|R|00:10|1|2||2026-10-17T10:00:00"

        def squeue(self, _user):
            return self.queue

        def sacct(self, _user):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("accounting unavailable")
            return "9|live|cpu|RUNNING|00:10|1|2||0:0|2026-10-17T10:00:00||/work|/work/o|/work/e"

    monotonic = {"value": 0.0}
    monkeypatch.setattr(
        "hpc_gui.wx_shell_jobs_history.time.monotonic",
        lambda: monotonic["value"],
    )
    slurm = Slurm()
    state = {"session": {"slurm": slurm, "profile": {"username": "alice", "id": "c1"}}}
    list_jobs = _jobs_callbacks(state, None, None)["list_jobs"]

    first = list_jobs()
    assert first["history_stale"] is False
    assert first["jobs"][0]["job_id"] == "9"
    slurm.queue = ""
    monotonic["value"] = 1.0
    second = list_jobs()
    assert second["history_stale"] is True
    assert "accounting unavailable" in second["history_error"]
    assert second["jobs"][0]["workdir"] == "/work"
    assert second["jobs"][0]["state"] == "RUNNING"


def test_hide_finished_jobs_setting_persists(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: path)
    assert storage.get_hide_finished_jobs_enabled() is False
    storage.set_hide_finished_jobs_enabled(True)
    assert storage.get_hide_finished_jobs_enabled() is True


def test_sacct_history_query_uses_bounded_rolling_window():
    class SSH:
        command = ""

        def run(self, command, *, log_output):
            self.command = command
            return 0, "", ""

    ssh = SSH()
    backend = SSHSlurmBackend(ssh)
    backend.sacct_history_result("alice", 30)
    assert "-S now-30days" in ssh.command
    assert "-S now-7days" not in ssh.command
    try:
        backend.sacct_history_result("alice", 31)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported history ranges must be rejected")
