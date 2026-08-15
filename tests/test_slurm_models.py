from hpc_gui.services.slurm_models import parse_sacct, parse_squeue


def test_parse_squeue_keeps_raw_rows_and_structured_fields() -> None:
    jobs = parse_squeue(
        "JOBID|PARTITION|NAME|USER|ST|TIME\n"
        "123|short|train|alice|R|00:12\n"
    )
    assert jobs[0].job_id == "123"
    assert jobs[0].partition == "short"
    assert jobs[0].state == "R"
    assert jobs[0].raw == "123|short|train|alice|R|00:12"


def test_parse_sacct_accepts_whitespace_columns_and_empty_output() -> None:
    jobs = parse_sacct(
        "JobID JobName State Elapsed MaxRSS\n"
        "123.batch train COMPLETED 00:10:12 1024M\n"
    )
    assert jobs[0].job_id == "123.batch"
    assert jobs[0].state == "COMPLETED"
    assert jobs[0].max_rss == "1024M"
    assert parse_sacct("") == []


def test_parse_sacct_reads_observed_scheduler_detail_fields() -> None:
    jobs = parse_sacct(
        "JobID|JobName|State|Elapsed|MaxRSS|ExitCode|NodeList|Reason|Command\n"
        "123|train|FAILED|00:01|1M|1:0|node[01-02]|OOM|/home/a/job.slurm\n"
    )
    assert jobs[0].exit_code == "1:0"
    assert jobs[0].nodelist == "node[01-02]"
    assert jobs[0].failure_reason == "OOM"
    assert jobs[0].script_path == "/home/a/job.slurm"

def test_parse_scontrol_extracts_detail_script_path() -> None:
    from hpc_gui.services.slurm_models import parse_scontrol

    job = parse_scontrol(
        "JobId=123 NodeList=node01 Reason=OOM ExitCode=1:0 Command=/home/a/job.slurm",
        "123",
    )
    assert job.nodelist == "node01"
    assert job.failure_reason == "OOM"
    assert job.exit_code == "1:0"
    assert job.script_path == "/home/a/job.slurm"