from hpc_gui.services.job_history_dashboard import JobHistoryDashboard


def _record(job_id, state="COMPLETED", provider="p", elapsed="00:10:00", resources=None):
    return {"job_id": job_id, "state": state, "provider_id": provider, "submitted_at": 1, "timing": {"elapsed": elapsed}, "resources": resources or {}}


def test_empty_and_mixed_provider_filters():
    dashboard = JobHistoryDashboard()
    assert dashboard.summarize([]).total == 0
    summary = dashboard.summarize([_record("1", provider="a"), _record("2", provider="b")], provider_id="a")
    assert summary.total == 1 and summary.states == {"COMPLETED": 1}


def test_arrays_default_to_parent_and_can_be_expanded():
    records = [_record("10"), _record("10_1"), _record("10_2", state="FAILED")]
    assert JobHistoryDashboard().summarize(records).total == 1
    assert JobHistoryDashboard().summarize(records, aggregate_arrays=False).total == 3


def test_runtime_partitions_and_complete_cpu_hours():
    records = [_record("1", resources={"cpus": 2, "partition": "short"}), _record("2", elapsed="00:20:00", resources={"cpus": 2, "partition": "short"})]
    summary = JobHistoryDashboard().summarize(records)
    assert summary.median_runtime_seconds == 900
    assert summary.partitions == {"short": 2}
    assert summary.cpu_hours == 1


def test_missing_resources_omit_resource_hours_and_bound_large_input():
    records = [_record(str(index)) for index in range(500)]
    summary = JobHistoryDashboard().summarize(records, limit=10)
    assert summary.cpu_hours is None
    assert len(summary.recent_runs) == 10
