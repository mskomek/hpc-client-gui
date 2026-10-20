from hpc_gui.jobs.job_rows import parse_job_row, prepare_job_list


def test_parse_job_row_preserves_scheduler_fields_and_failure_reason():
    row = parse_job_row({"job_id": 42, "name": "solve", "state": "FAILED", "failure_reason": "OOM"})

    assert row["job_id"] == "42"
    assert row["name"] == "solve"
    assert row["state"] == "FAILED"
    assert row["reason"] == "OOM"
    assert row["partition"] == ""


def test_parse_job_row_accepts_pipe_and_whitespace_rows():
    pipe_row = parse_job_row("42|compute|solve|user|RUNNING|00:01|1|8|None")
    whitespace_row = parse_job_row("42 compute solve user RUNNING 00:01 1 8 None")

    assert pipe_row == whitespace_row
    assert pipe_row["partition"] == "compute"
    assert pipe_row["cpus"] == "8"
    assert pipe_row["reason"] == "None"


def test_prepare_job_list_keeps_source_immutable_and_hides_terminal_rows():
    rows = [
        {"job_id": "10", "name": "solve", "state": "COMPLETED", "end_time": "2026-10-20T12:00:00"},
        {"job_id": "11", "name": "solve", "state": "RUNNING", "submit_time": "2026-10-20T13:00:00"},
        {"job_id": "12", "name": "other", "state": "PENDING", "submit_time": "2026-10-20T13:30:00"},
    ]

    visible = prepare_job_list(rows, query="solve", hide_finished=True)

    assert [row["job_id"] for row in visible] == ["11"]
    assert [row["job_id"] for row in rows] == ["10", "11", "12"]


def test_prepare_job_list_places_active_before_completed():
    rows = [
        {"job_id": "99", "state": "COMPLETED", "end_time": "2026-10-20T13:00:00"},
        {"job_id": "1", "state": "RUNNING", "submit_time": "2026-10-20T10:00:00"},
    ]

    assert [row["job_id"] for row in prepare_job_list(rows)] == ["1", "99"]
