from truba_gui.services.slurm_models import parse_sacct, parse_squeue


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
