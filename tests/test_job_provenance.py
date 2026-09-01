from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_record_store import JobRecordStore


def test_successful_submit_and_later_completion(tmp_path):
    store = JobRecordStore(tmp_path / "jobs.sqlite3")
    capture = JobProvenanceCapture(store)
    capture.submitted("12345", "#!/bin/bash\necho ok\n", profile_id="p", provider_id="truba", resources={"cpus": 4}, paths={"script": "/work/a.slurm", "stdout": "/work/a.out"})
    capture.observation("12345", state="COMPLETED", elapsed="00:02", exit_code="0:0", max_rss="2G", nodes="n01", completed_at=10)
    row = store.get("12345")
    assert row["profile_id"] == "p"
    assert row["state"] == "COMPLETED"
    assert row["exit_code"] == "0:0"
    assert row["timing"]["stdout"] == "/work/a.out"
    assert row["resources"]["max_rss"] == "2G"


def test_array_parent_identity_and_restart(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    first = JobRecordStore(path)
    capture = JobProvenanceCapture(first)
    capture.submitted("12345", "script")
    first.close()
    second = JobRecordStore(path)
    assert second.get("12345")["script_hash"]
    assert capture.analytics_job_id("12345_7") == "12345"
