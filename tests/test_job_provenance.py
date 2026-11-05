import pytest

from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_record_store import JobRecordStore


@pytest.mark.integration
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


@pytest.mark.integration
def test_array_parent_identity_and_restart(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    first = JobRecordStore(path)
    capture = JobProvenanceCapture(first)
    capture.submitted("12345", "script")
    first.close()
    second = JobRecordStore(path)
    assert second.get("12345")["script_hash"]
    assert capture.analytics_job_id("12345_7") == "12345"


@pytest.mark.integration
def test_submission_redacts_secrets_without_changing_executed_script_hash(tmp_path):
    from hpc_gui.services.job_provenance import script_hash

    store = JobRecordStore(tmp_path / "provenance-redact.sqlite3")
    capture = JobProvenanceCapture(store)
    original_script = (
        '#!/bin/bash\nexport AWS_SECRET_ACCESS_KEY="fake-sentinel"\n'
        'python solve.py --token="two fake words" --mode=stable\n'
    )
    record = capture.submitted(
        "908", original_script, profile_id="profile-a", provider_id="truba",
    )
    saved = store.get("908")
    for secret in ("fake-sentinel", "two fake words"):
        assert secret not in saved["script_text"]
        assert secret not in record["script_text"]
    assert saved["script_text"].count("[REDACTED]") == 2
    assert "--mode=stable" in saved["script_text"]
    assert saved["script_hash"] == script_hash(original_script)
    assert record["script_hash"] == script_hash(original_script)
    assert saved["profile_id"] == "profile-a"
    assert saved["provider_id"] == "truba"
    assert store._db.execute("PRAGMA user_version").fetchone()[0] == 4
    store.close()


@pytest.mark.integration
def test_provenance_keeps_nonsecret_script_intact(tmp_path):
    store = JobRecordStore(tmp_path / "provenance-safe.sqlite3")
    script = "#!/bin/bash\n#SBATCH --output=slurm-%j.out\necho ok\n"
    JobProvenanceCapture(store).submitted("909", script)
    saved = store.get("909")
    assert saved["script_text"] == script
    assert saved["profile_id"] == ""
    store.close()


@pytest.mark.integration
def test_same_job_id_updates_only_explicit_profile_and_cluster(tmp_path):
    store = JobRecordStore(tmp_path / "separate-profiles.sqlite3")
    capture = JobProvenanceCapture(store)
    capture.submitted(
        "42", "echo first", profile_id="arf", cluster_id="cluster-one",
        provider_id="slurm",
    )
    capture.submitted(
        "42", "echo second", profile_id="arf2", cluster_id="cluster-two",
        provider_id="slurm",
    )

    assert store.get("42") is None  # ambiguous ID, never select another profile

    capture.observation(
        "42", profile_id="arf", cluster_id="cluster-one",
        provider_id="slurm", state="COMPLETED", exit_code="0:0",
        elapsed="00:03", max_rss="8G",
    )

    first = store.get(
        "42", profile_id="arf", cluster_id="cluster-one", provider_id="slurm",
    )
    second = store.get(
        "42", profile_id="arf2", cluster_id="cluster-two", provider_id="slurm",
    )
    assert first["state"] == "COMPLETED"
    assert first["exit_code"] == "0:0"
    assert first["resources"]["max_rss"] == "8G"
    assert second["state"] == "SUBMITTED"
    assert second["exit_code"] == ""
    assert second["script_text"] == "echo second"
    assert len(store.list()) == 2
    store.close()


@pytest.mark.integration
def test_unscoped_observation_does_not_update_ambiguous_job_id(tmp_path):
    store = JobRecordStore(tmp_path / "ambiguous-observation.sqlite3")
    capture = JobProvenanceCapture(store)
    capture.submitted("42", "echo one", profile_id="p1")
    capture.submitted("42", "echo two", profile_id="p2")
    capture.observation("42", state="FAILED", exit_code="1:0")
    assert {row["state"] for row in store.list()} == {"SUBMITTED"}
    store.close()
