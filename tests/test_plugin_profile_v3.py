import pytest
from copy import deepcopy

from hpc_gui.plugins.loader import _build_profile
from hpc_gui.plugins.validator import validate_cluster_profile_dict


def _profile(**updates):
    value = {
        "schema_version": 3,
        "profile_id": "provider",
        "name": "Provider",
        "scheduler": "slurm",
    }
    value.update(updates)
    return value


def _stream(stream_id="stdout", resolver="slurm.stdout", **extra):
    value = {
        "id": stream_id,
        "role": "stdout",
        "labels": {"en": "Standard Output", "tr": "Standart Çıktı"},
        "resolver": resolver,
        "order": 10,
    }
    value.update(extra)
    return value


@pytest.mark.contract
def test_v1_v2_v3_profiles_remain_valid():
    assert validate_cluster_profile_dict({
        "schema_version": 1, "profile_id": "legacy", "name": "Legacy", "scheduler": "slurm",
    }) == []
    assert validate_cluster_profile_dict({
        "schema_version": 2, "profile_id": "structured", "name": "Structured", "scheduler": "slurm",
    }) == []
    assert validate_cluster_profile_dict(_profile()) == []


@pytest.mark.contract
def test_v3_empty_and_multiple_job_outputs_preserve_runtime_shape():
    empty = _profile(job_outputs={"streams": []})
    assert validate_cluster_profile_dict(empty) == []
    assert _build_profile(empty)[0].job_outputs == {"streams": []}

    multiple = _profile(job_outputs={"streams": [
        _stream(), _stream("stderr", "slurm.stderr", role="stderr", order=20),
        _stream("progress", "workdir.relative", role="custom", relative_path="progress-%x.log", order=30),
    ]})
    assert validate_cluster_profile_dict(multiple) == []
    profile, error = _build_profile(multiple)
    assert error is None
    assert [item["id"] for item in profile.job_outputs["streams"]] == ["stdout", "stderr", "progress"]


@pytest.mark.contract
def test_v3_file_filters_validate_and_reject_unsafe_fixtures():
    valid = _profile(file_filters=[{
        "id": "fluent", "labels": {"en": "Fluent", "tr": "Fluent"},
        "globs": ["*.cas.h5"], "suffixes": [".dat.h5"], "order": 100,
    }])
    assert validate_cluster_profile_dict(valid) == []

    cases = []
    duplicate = deepcopy(valid)
    duplicate["file_filters"].append(deepcopy(duplicate["file_filters"][0]))
    cases.append(duplicate)
    cases.append(_profile(file_filters=[{
        "id": "slurm", "labels": {"en": "Bad"}, "suffixes": [".bad"], "order": 1,
    }]))
    cases.append(_profile(job_outputs={"streams": [_stream("custom", "workdir.relative", role="custom", relative_path="/outside")]}))
    cases.append(_profile(job_outputs={"streams": [_stream("custom", "workdir.relative", role="custom", relative_path="../outside")]}))
    cases.append(_profile(job_outputs={"streams": [_stream(extra_property="bad")]}))
    cases.append(_profile(job_outputs={"streams": [_stream(resolver="provider.command")]}))
    cases.append(_profile(scheduler="pbs"))
    for case in cases:
        assert validate_cluster_profile_dict(case), case


@pytest.mark.contract
def test_v3_provider_template_is_preserved_for_connection_runtime():
    raw = _profile(job_outputs={"streams": [_stream()]})
    profile, error = _build_profile(raw)
    assert error is None
    settings = profile.to_system_settings()
    assert settings["provider_template"]["job_outputs"]["streams"][0]["resolver"] == "slurm.stdout"
