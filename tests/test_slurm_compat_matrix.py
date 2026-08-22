"""Offline Slurm compatibility matrix.

Each fixture is fabricated data representing a materially different but valid
SSH+Slurm environment. The tests pin how far the generic parsers and the
configurable command templates reach, so compatibility claims stay evidence
based and site-independent.

No network access, no real scheduler, no credentials.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.services.slurm_models import (  # noqa: E402
    format_job_details,
    parse_sacct,
    parse_scontrol,
    parse_squeue,
)

SQUEUE_HEADER = "JOBID|PARTITION|NAME|USER|STATE|TIME|NODES|CPUS|REASON"


def _squeue_row(job_id="100001", partition="defq", name="job", user="researcher",
                state="RUNNING", elapsed="01:00:00", nodes="1", cpus="1",
                reason="", extra=""):
    return f"{job_id}|{partition}|{name}|{user}|{state}|{elapsed}|{nodes}|{cpus}|{reason}{extra}"


class SqueueMatrixTests(unittest.TestCase):
    def test_normal_queue(self) -> None:
        text = "\n".join([SQUEUE_HEADER, _squeue_row(state="RUNNING")])
        jobs = parse_squeue(text)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "100001")
        self.assertEqual(jobs[0].state, "RUNNING")
        self.assertEqual(jobs[0].partition, "defq")

    def test_empty_queue_has_no_rows(self) -> None:
        self.assertEqual(parse_squeue(SQUEUE_HEADER), [])
        self.assertEqual(parse_squeue(""), [])

    def test_long_job_names_and_reason_with_spaces_and_parentheses(self) -> None:
        name = "pipeline_stage_with_a_deliberately_long_descriptive_name"
        text = "\n".join([
            SQUEUE_HEADER,
            _squeue_row(name=name, state="PENDING",
                        reason="(Priority) waiting for resources"),
        ])
        jobs = parse_squeue(text)
        self.assertEqual(jobs[0].name, name)
        self.assertEqual(jobs[0].reason, "(Priority) waiting for resources")

    def test_array_jobs_keep_task_ids_as_strings(self) -> None:
        text = "\n".join([
            SQUEUE_HEADER,
            _squeue_row(job_id="200100_0", name="array-demo"),
            _squeue_row(job_id="200100_1", name="array-demo"),
            _squeue_row(job_id="200100", name="array-demo", state="PENDING"),
        ])
        jobs = parse_squeue(text)
        self.assertEqual([job.job_id for job in jobs], ["200100_0", "200100_1", "200100"])

    def test_banner_noise_lines_are_dropped_not_parsed_as_jobs(self) -> None:
        banner = "*** Authorized use only. All activity is monitored. ***"
        real_header = SQUEUE_HEADER
        text = "\n".join([
            banner,
            real_header,
            _squeue_row(),
        ])
        jobs = parse_squeue(text)
        # The banner becomes the synthetic header; the real header row is
        # recognised and skipped; only genuine rows survive.
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "100001")

    def test_site_specific_extra_columns_are_tolerated(self) -> None:
        text = "\n".join([
            SQUEUE_HEADER,
            _squeue_row() + "|gpu|normal-hourglass|team-x",
        ])
        jobs = parse_squeue(text)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "100001")
        self.assertEqual(jobs[0].state, "RUNNING")

    def test_repeated_headers_from_concatenated_outputs_are_skipped(self) -> None:
        header = SQUEUE_HEADER
        text = "\n".join([header, _squeue_row(), header, _squeue_row(job_id="100002")])
        jobs = parse_squeue(text)
        self.assertEqual({job.job_id for job in jobs}, {"100001", "100002"})


class SacctMatrixTests(unittest.TestCase):
    def test_completed_and_failed_states_parse(self) -> None:
        text = "\n".join([
            "JobID|JobName|State|Elapsed|MaxRSS|AllocTRES",
            "300001|analysis|COMPLETED|00:12:34|1.20G|cpu=4",
            "300002|fitting|FAILED|00:03:00|0|cpu=2",
        ])
        jobs = parse_sacct(text)
        self.assertEqual([job.state for job in jobs], ["COMPLETED", "FAILED"])
        self.assertEqual(jobs[0].max_rss, "1.20G")

    def test_array_accounting_rows_include_task_suffixes(self) -> None:
        text = "\n".join([
            "JobID|JobName|State|Elapsed|MaxRSS|AllocTRES",
            "400100|sweep|COMPLETED|00:30:00||",
            "400100.batch|batch|COMPLETED|00:30:00|900.0M|",
            "400100.extern|extern|COMPLETED|00:30:00||",
        ])
        jobs = parse_sacct(text)
        self.assertEqual(len(jobs), 3)
        self.assertTrue(all(job.state == "COMPLETED" for job in jobs))

    def test_whitespace_only_output_is_empty(self) -> None:
        self.assertEqual(parse_sacct("\n  \n"), [])


class ScontrolMatrixTests(unittest.TestCase):
    def test_key_value_fields_are_observed(self) -> None:
        text = "\n".join([
            "JobId=500001 JobName=demo",
            "   UserId=researcher(1000) GroupId=research(1001) MCS_label=N/A",
            "   Priority=4294901759 Nice=0 Account=(null) QOS=normal",
            "   JobState=RUNNING Reason=None Dependency=(null)",
            "   RunTime=00:10:00 TimeLimit=01:00:00 TimeMin=N/A",
            "   NodeList=n[01-02] NumNodes=2 NumCPUs=32 NumTasks=1",
            "   Command=/home/researcher/run.slurm",
            "   ExitCode=0:0",
        ])
        job = parse_scontrol(text, job_id="500001")
        self.assertEqual(job.job_id, "500001")
        self.assertEqual(job.nodelist, "n[01-02]")
        self.assertEqual(job.exit_code, "0:0")
        self.assertEqual(job.script_path, "/home/researcher/run.slurm")

    def test_details_format_lists_only_populated_fields(self) -> None:
        from hpc_gui.services.slurm_models import SlurmJob

        job = SlurmJob(job_id="42", nodelist="n01", exit_code="0:0")
        rendered = format_job_details(job)
        self.assertIn("Node list: n01", rendered)
        self.assertNotIn("Failure reason", rendered)


class MissingCapabilityMatrixTests(unittest.TestCase):
    """Sites without sacct/scontrol must surface errors, not fake data."""

    @staticmethod
    def _ssh_with(exit_code: int, out: str = "", err: str = ""):
        return SimpleNamespace(
            run=lambda *_args, **_kwargs: (exit_code, out, err),
        )

    def _backend(self, overrides: dict[str, str] | None = None):
        from hpc_gui.services.slurm_ssh import SSHSlurmBackend

        settings = {
            "scratch_dir": "/scratch/{user}",
            "home_dir": "/home/{user}",
            "system_name": "",
            "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
            "sbatch_command": "sbatch {script_path_q}",
            "scancel_command": "scancel {job_id_q}",
            "sacct_command": "sacct -u {user}",
            "scontrol_command": "scontrol show job {job_id_q}",
            "status_command": "sinfo",
            "active_job_ids_command": 'squeue -h -u {user} -o "%A"',
            "job_state_command": "sacct -n -X -j {job_id_q} -o State -P",
        }
        settings.update(overrides or {})
        return SSHSlurmBackend(self._ssh_with(127, "", "sacct: command not found"), settings)

    def test_missing_sacct_returns_error_text_not_empty_success(self) -> None:
        result = self._backend().sacct("researcher")
        self.assertIn("command not found", result)

    def test_missing_job_state_reports_failure_text(self) -> None:
        result = self._backend().job_state("500001")
        self.assertIn("command not found", result)

    def test_custom_site_commands_are_used_verbatim(self) -> None:
        captured: list[str] = []

        class Recorder:
            def run(self, cmd, log_output=False):
                captured.append(cmd)
                return 0, "RUNNING\n", ""

        from hpc_gui.services.slurm_ssh import SSHSlurmBackend

        backend = SSHSlurmBackend(
            Recorder(),
            {
                "scratch_dir": "/fast/{user}",
                "home_dir": "/home/{user}",
                "system_name": "site-x",
                "squeue_command": "/opt/slurm/bin/squeue --me --format=%i",
                "sbatch_command": "sbatch --parsable {script_path_q}",
                "scancel_command": "scancel {job_id_q}",
                "sacct_command": "sacct -u {user}",
                "scontrol_command": "scontrol show job {job_id_q}",
                "status_command": "sinfo -s",
                "active_job_ids_command": 'squeue -h -u {user} -o "%A"',
                "job_state_command": "sacct -n -X -j {job_id_q} -o State -P",
            },
        )
        backend.squeue("researcher")
        self.assertEqual(captured, ["/opt/slurm/bin/squeue --me --format=%i"])


if __name__ == "__main__":
    unittest.main()
