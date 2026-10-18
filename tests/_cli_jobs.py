from __future__ import annotations
import shlex
from _cli_test_support import (
    json,
    patch,
    pytest,
    ExitCode,
    run_cli,
    CLIConnectionError,
)

class _FakeJobsSSH:
    """Records every command string and returns a fixed run result."""

    def __init__(self, result):
        self.result = result
        self.commands = []

    def run(self, command, **kwargs):
        self.commands.append(command)
        return self.result


class _FakeJobsSession:
    def __init__(self, ssh):
        self.ssh = ssh

    def close(self):
        pass


def _fake_jobs_session(ssh):
    return _FakeJobsSession(ssh)


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_help_lists_all_four_subcommands(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_cli(["jobs", "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for name in ("list", "status", "accounting", "lssrv"):
        assert name in out


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_list_text_uses_default_squeue_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "JOBID STATE\n  123 RUNNING\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "--user", "alice", "jobs", "list"]) == 0
    assert fake_ssh.commands == ['squeue -h -u alice -o "%i|%P|%j|%u|%T|%M|%D|%C|%R|%V"']
    out = capsys.readouterr().out
    assert "JOBID STATE" in out
    assert "123 RUNNING" in out


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_list_json_envelope_matches_stdout(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "JOBID STATE\n  123 RUNNING\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "--user", "alice", "jobs", "list"]) == 0
    assert fake_ssh.commands == ['squeue -h -u alice -o "%i|%P|%j|%u|%T|%M|%D|%C|%R|%V"']
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": "JOBID STATE\n  123 RUNNING\n"}


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_list_username_falls_back_to_profile(capsys) -> None:
    profiles = [{"name": "alpha", "host": "cluster.example", "username": "profileuser"}]
    fake_ssh = _FakeJobsSSH((0, "JOBID STATE\n", ""))
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)
    ):
        assert run_cli(["--profile", "alpha", "jobs", "list"]) == 0
    assert fake_ssh.commands == ['squeue -h -u profileuser -o "%i|%P|%j|%u|%T|%M|%D|%C|%R|%V"']


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_status_uses_default_scontrol_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "JobId=123 JobName=test State=RUNNING\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "status", "123"]) == 0
    assert fake_ssh.commands == ["scontrol show job 123"]
    assert "JobId=123" in capsys.readouterr().out


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_status_requires_job_id_argument() -> None:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open:
        with pytest.raises(SystemExit) as excinfo:
            run_cli(["--host", "host", "jobs", "status"])
        assert excinfo.value.code == 2
        session_open.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_list_connection_failure_exit_three(capsys) -> None:
    with patch(
        "hpc_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "jobs", "list"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "host unreachable" in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_status_unexpected_exception_exit_one_jobs_prefix(capsys) -> None:
    class BoomSSH(_FakeJobsSSH):
        def run(self, command, **kwargs):
            raise RuntimeError("scheduler exploded")

    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(BoomSSH((0, "", "")))):
        assert run_cli(["--host", "host", "jobs", "status", "123"]) == 1
    captured = capsys.readouterr()
    assert "Jobs operation failed" in captured.err
    assert "scheduler exploded" in captured.err


_SACCT_COMMAND = (
    "sacct -n -P -S now-7days -u alice "
    "--format=JobIDRaw,JobName,Partition,State,Elapsed,AllocNodes,AllocCPUS,Reason,"
    "ExitCode,Submit,End,WorkDir,StdOut,StdErr"
)
_ACCOUNTING_STDOUT = (
    "JobID     JobName     State    Elapsed     MaxRSS   AllocTRES\n"
    "101       compute.cpu RUNNING  00:10:00        512K c01[1-2]\n"
    "102       solver.gpu  FAILED  00:00:05          8K c07[5-6]\n"
)
_LSSRV_STDOUT = "Login node         CPUs    Load\nnode1                32    0.12\n"


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_accounting_text_uses_default_sacct_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _ACCOUNTING_STDOUT, ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "--user", "alice", "jobs", "accounting"]) == 0
    assert fake_ssh.commands == [_SACCT_COMMAND]
    out = capsys.readouterr().out
    assert "101       compute.cpu RUNNING" in out
    assert "102       solver.gpu  FAILED" in out


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_accounting_json_envelope_matches_stdout(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _ACCOUNTING_STDOUT, ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "--user", "alice", "jobs", "accounting"]) == 0
    assert fake_ssh.commands == [_SACCT_COMMAND]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": _ACCOUNTING_STDOUT}


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_accounting_username_falls_back_to_profile(capsys) -> None:
    profiles = [{"name": "alpha", "host": "cluster.example", "username": "profileuser"}]
    fake_ssh = _FakeJobsSSH((0, "Account line\n", ""))
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)
    ):
        assert run_cli(["--profile", "alpha", "jobs", "accounting"]) == 0
    assert fake_ssh.commands == [
        "sacct -n -P -S now-7days -u profileuser "
        "--format=JobIDRaw,JobName,Partition,State,Elapsed,AllocNodes,AllocCPUS,Reason,"
        "ExitCode,Submit,End,WorkDir,StdOut,StdErr"
    ]


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_accounting_connection_failure_exit_three(capsys) -> None:
    with patch(
        "hpc_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "jobs", "accounting"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "host unreachable" in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_lssrv_uses_configured_status_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _LSSRV_STDOUT, ""))
    from hpc_gui.services.slurm_ssh import SSHSlurmBackend

    backend = SSHSlurmBackend(fake_ssh, system_settings={"status_command": "lssrv"})
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)), patch(
        "hpc_gui.cli.main.jobs_backend", return_value=backend
    ):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 0
    assert fake_ssh.commands == ["lssrv"]
    out = capsys.readouterr().out
    assert "node1                32    0.12" in out


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_lssrv_json_envelope_matches_stdout(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _LSSRV_STDOUT, ""))
    from hpc_gui.services.slurm_ssh import SSHSlurmBackend

    backend = SSHSlurmBackend(fake_ssh, system_settings={"status_command": "lssrv"})
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)), patch(
        "hpc_gui.cli.main.jobs_backend", return_value=backend
    ):
        assert run_cli(["--format", "json", "--host", "host", "jobs", "lssrv"]) == 0
    assert fake_ssh.commands == ["lssrv"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": _LSSRV_STDOUT}


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_lssrv_without_site_status_command_fails_cleanly(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 1
    captured = capsys.readouterr()
    assert "Jobs operation failed" in captured.err
    assert "No site status command" in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_lssrv_connection_failure_exit_three(capsys) -> None:
    with patch(
        "hpc_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "host unreachable" in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_jobs_lssrv_nonzero_exit_maps_to_operation_failed(capsys) -> None:
    fake_ssh = _FakeJobsSSH((1, "", "lssrv: command not found"))
    from hpc_gui.services.slurm_ssh import SSHSlurmBackend

    backend = SSHSlurmBackend(fake_ssh, system_settings={"status_command": "lssrv"})
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)), patch(
        "hpc_gui.cli.main.jobs_backend", return_value=backend
    ):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 1
    captured = capsys.readouterr()
    assert "Jobs operation failed" in captured.err
    assert "lssrv: command not found" in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_submit_yes_submits_script_and_exits_zero(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "Submitted batch job 12347\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "submit", "/home/alice/run.sh", "--yes"]) == 0
    assert fake_ssh.commands == ["cd -- /home/alice && sbatch -- run.sh"]
    assert "Submitted batch job 12347" in capsys.readouterr().out


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_submit_without_yes_exits_usage_no_session(capsys) -> None:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open:
        assert run_cli(["--host", "host", "jobs", "submit", "/home/alice/run.sh"]) == int(ExitCode.USAGE)
    session_open.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Refusing to submit a job without --yes." in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_submit_yes_json_envelope_has_result_key(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "Submitted batch job 12347\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "jobs", "submit", "/home/alice/run.sh", "--yes"]) == 0
    assert fake_ssh.commands == ["cd -- /home/alice && sbatch -- run.sh"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": "Submitted batch job 12347\n"}


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_cancel_yes_cancels_job_and_exits_zero(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "scancel: Terminated job 12345\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "cancel", "12345", "--yes"]) == 0
    assert fake_ssh.commands == ["scancel 12345"]
    assert "scancel: Terminated job 12345" in capsys.readouterr().out


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_cancel_without_yes_exits_usage_no_session(capsys) -> None:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open:
        assert run_cli(["--host", "host", "jobs", "cancel", "12345"]) == int(ExitCode.USAGE)
    session_open.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Refusing to cancel a job without --yes." in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_cancel_unsafe_job_id_exits_usage_no_session(capsys) -> None:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open:
        assert run_cli(["--host", "host", "jobs", "cancel", "12345; rm -rf /", "--yes"]) == int(
            ExitCode.USAGE
        )
    session_open.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Invalid job ID: 12345; rm -rf /" in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_cancel_array_task_id_accepted(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "scancel: Terminated job 12345_3\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "cancel", "12345_3", "--yes"]) == 0
    assert fake_ssh.commands == ["scancel 12345_3"]
    assert "scancel: Terminated job 12345_3" in capsys.readouterr().out


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_cancel_compact_array_and_heterogeneous_ids_are_accepted(capsys) -> None:
    for job_id in ("6810497_[0-3%4]", "93+0"):
        fake_ssh = _FakeJobsSSH((0, f"scancel: Terminated job {job_id}\n", ""))
        with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
            assert run_cli(["--host", "host", "jobs", "cancel", job_id, "--yes"]) == 0
        assert fake_ssh.commands == [f"scancel {shlex.quote(job_id)}"]
        assert f"scancel: Terminated job {job_id}" in capsys.readouterr().out


@pytest.mark.contract
@pytest.mark.semantic
def test_jobs_cancel_yes_json_envelope_has_result_key(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "scancel: Terminated job 12345\n", ""))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "jobs", "cancel", "12345", "--yes"]) == 0
    assert fake_ssh.commands == ["scancel 12345"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": "scancel: Terminated job 12345"}
