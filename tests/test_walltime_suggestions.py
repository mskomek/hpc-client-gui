from hpc_gui.services.walltime_suggestions import suggest_walltime


def _record(seconds, state="COMPLETED", cpus=4, gpus=0):
    return {"state": state, "provider_id": "p", "resources": {"partition": "short", "cpus": cpus, "gpus": gpus}, "timing": {"elapsed": f"00:{seconds // 60:02d}:{seconds % 60:02d}"}}


def test_insufficient_and_mixed_failures_return_no_suggestion():
    assert suggest_walltime([_record(60)] * 4, {"provider_id": "p", "partition": "short", "cpus": 4, "gpus": 0}) is None
    assert suggest_walltime([_record(60)] * 5 + [_record(999, "FAILED")], {"provider_id": "p", "partition": "short", "cpus": 4, "gpus": 0}) is not None


def test_outlier_and_cpu_gpu_mismatch_are_handled():
    records = [_record(600)] * 5 + [_record(3600)]
    target = {"provider_id": "p", "partition": "short", "cpus": 4, "gpus": 0}
    suggestion = suggest_walltime(records, target)
    assert suggestion.p90_seconds == 600
    assert suggestion.seconds == 900
    assert suggest_walltime(records, {**target, "cpus": 8}) is None
    assert suggest_walltime(records, {**target, "gpus": 1}) is None


def test_suggestion_is_deterministic_and_transparent():
    target = {"provider_id": "p", "partition": "short", "cpus": 4, "gpus": 0}
    records = [_record(600)] * 5
    first = suggest_walltime(records, target)
    second = suggest_walltime(reversed(records), target)
    assert first == second
    assert first.as_slurm_time() == "00:15:00"
