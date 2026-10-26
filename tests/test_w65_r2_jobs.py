"""W65r2 F5: restart-safe job links + host Jobs wiring (G39/G42)."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.hpc import MultiFileCommit
from hpc_gui.plugins.openfoam_studio.job_links import JobLinkStore
from hpc_gui.services import job_record_store


def _commit(files, committed):
    from hpc_gui.plugins.openfoam_studio.hpc import FileStage
    return MultiFileCommit([FileStage(f, "a", "b", c) for f, c in
                            zip(files, committed)])


def test_partial_never_green_semantics():
    assert _commit(["a", "b"], [True, True]).overall() == "COMMITTED"
    partial = _commit(["a", "b"], [True, False]).overall()
    assert partial.startswith("PARTIAL") and "b" in partial
    assert _commit(["a"], [False]).overall() == "FAILED"


def test_link_verify_persist_across_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(job_record_store, "default_job_record_path",
                        lambda: tmp_path / "host-jobs.sqlite3")
    store = JobLinkStore(str(tmp_path / "links.json"))
    entry = store.link("slurm-42", "/cases/cavity", b"case-bytes-v1",
                       log_paths=["slurm-42.out"], result_paths=["postProcessing/sets"])
    assert entry.case_hash and store.verify_case("slurm-42", b"case-bytes-v1") == "MATCH"
    assert store.verify_case("slurm-42", b"changed") == "STALE-CASE"
    assert store.verify_case("ghost", b"x") == "UNKNOWN-JOB"
    reopened = JobLinkStore(str(tmp_path / "links.json"))
    assert reopened.get("slurm-42").case_hash == entry.case_hash
    assert reopened.get("slurm-42").log_paths == ["slurm-42.out"]
    with pytest.raises(ValueError):
        store.link("bad id;", "/cases/c", b"x")


def test_host_mirror_uses_public_store_and_isolated_path(tmp_path, monkeypatch):
    host_path = tmp_path / "host-jobs.sqlite3"
    monkeypatch.setattr(job_record_store, "default_job_record_path", lambda: host_path)
    links = JobLinkStore(str(tmp_path / "links.json"))
    links.link("slurm-7", "/cases/c", b"bytes", log_paths=["slurm-7.out"],
               result_paths=["postProcessing/sets"])
    host = job_record_store.JobRecordStore(host_path)
    try:
        row = host.get("slurm-7")
        assert row is not None
        assert row["component_id"] == "openfoam-studio"
        assert row["paths"]["case_path"] == "/cases/c"
        assert row["outputs"]["log_paths"] == ["slurm-7.out"]
        assert row["outputs"]["result_paths"] == ["postProcessing/sets"]
    finally:
        host.close()
