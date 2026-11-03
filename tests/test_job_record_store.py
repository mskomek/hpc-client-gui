import pytest

import sqlite3

from hpc_gui.services.job_record_store import JobRecordStore


@pytest.mark.integration
def test_create_insert_update_query_and_empty_db(tmp_path):
    store = JobRecordStore(tmp_path / "jobs.sqlite3")
    assert store.list() == []
    store.upsert({"job_id": "123", "profile_id": "p", "state": "PENDING", "resources": {"cpus": 4}})
    store.upsert({"job_id": "123", "state": "COMPLETED"})
    row = store.get("123")
    assert row["state"] == "COMPLETED"
    assert row["profile_id"] == "p"
    assert row["scope"] == "app-submitted"
    store.close()


@pytest.mark.integration
def test_migration_and_corruption_fallback(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version = 0")
    db.commit()
    db.close()
    store = JobRecordStore(path)
    assert store.get("missing") is None
    store.close()
    path.write_bytes(b"not sqlite")
    repaired = JobRecordStore(path)
    repaired.upsert({"job_id": "1"})
    assert repaired.get("1")["job_id"] == "1"
    repaired.close()


def test_scoped_identity_separates_same_scheduler_id(tmp_path):
    store = JobRecordStore(tmp_path / "scoped.sqlite3")
    store.upsert({"job_id": "42", "profile_id": "p1", "cluster_id": "c1",
                  "provider_id": "slurm", "state": "RUNNING"})
    store.upsert({"job_id": "42", "profile_id": "p2", "cluster_id": "c2",
                  "provider_id": "truba", "state": "COMPLETED"})
    assert store.get("42", profile_id="p1", cluster_id="c1", provider_id="slurm")["state"] == "RUNNING"
    assert store.get("42", profile_id="p2", cluster_id="c2", provider_id="truba")["state"] == "COMPLETED"
    assert store.get("42") is None
    store.close()


def test_empty_observation_keeps_last_good_paths_and_details(tmp_path):
    store = JobRecordStore(tmp_path / "preserve.sqlite3")
    identity = {"job_id": "8", "profile_id": "p", "cluster_id": "c", "provider_id": "slurm"}
    store.record_observation({**identity, "source": "scontrol", "state": "RUNNING",
                              "paths": {"workdir": "/work/8", "stdout_path": "/work/8/out"},
                              "details": {"raw": "JobId=8 WorkDir=/work/8"}})
    store.record_observation({**identity, "source": "squeue", "state": "RUNNING",
                              "paths": {"workdir": ""}, "details": {"raw": ""}})
    row = store.get("8", **{k: identity[k] for k in ("profile_id", "cluster_id", "provider_id")})
    assert row["paths"]["workdir"] == "/work/8"
    assert row["details"]["raw"] == "JobId=8 WorkDir=/work/8"
    store.close()


def test_delete_details_tombstone_prevents_observation_resurrection(tmp_path):
    store = JobRecordStore(tmp_path / "delete.sqlite3")
    identity = {"job_id": "9", "profile_id": "p", "cluster_id": "c", "provider_id": "slurm"}
    store.upsert({**identity, "state": "COMPLETED", "paths": {"workdir": "/work/9"}})
    assert store.delete_details([identity]) == 1
    assert store.get("9", profile_id="p", cluster_id="c", provider_id="slurm") is None
    assert not store.record_observation({**identity, "state": "COMPLETED", "paths": {"workdir": "/work/9"}})
    assert store.list(profile_id="p", cluster_id="c", provider_id="slurm") == []
    store.upsert({**identity, "source": "submitted", "state": "SUBMITTED"})
    assert store.get("9", profile_id="p", cluster_id="c", provider_id="slurm")["state"] == "SUBMITTED"
    store.close()


def test_output_snapshots_are_bounded_and_reloadable(tmp_path):
    store = JobRecordStore(tmp_path / "outputs.sqlite3")
    identity = {"job_id": "17", "profile_id": "p", "cluster_id": "c", "provider_id": "slurm"}
    content = "x" * 300_000
    store.record_observation({**identity, "outputs": {"stdout": {
        "text": content, "captured_at": 123, "source": "remote",
    }}})
    store.close()
    reopened = JobRecordStore(tmp_path / "outputs.sqlite3")
    snapshot = reopened.get("17", profile_id="p", cluster_id="c", provider_id="slurm")["outputs"]["stdout"]
    assert len(snapshot["text"]) == 256_000
    assert snapshot["text"] == content[-256_000:]
    assert snapshot["captured_at"] == 123
    reopened.close()


def test_snapshot_redacts_secret_values(tmp_path):
    store = JobRecordStore(tmp_path / "redact.sqlite3")
    store.record_observation({"job_id": "18", "outputs": {
        "stdout": {"text": "API_TOKEN=do-not-store password: hidden"},
    }})
    text = store.get("18")["outputs"]["stdout"]["text"]
    assert "do-not-store" not in text
    assert "hidden" not in text
    assert text.count("[REDACTED]") == 2
    store.close()


def test_all_persisted_json_buckets_redact_and_bound_metadata(tmp_path):
    store = JobRecordStore(tmp_path / "metadata-redact.sqlite3")
    store.record_observation({
        "job_id": "19",
        "metadata": {
            "raw_details": 'JobId=19 Environment={"AWS_SECRET_ACCESS_KEY":"hidden"}',
            "password": '"quoted value"',
            "large": "x" * 300_000,
        },
    })
    metadata = store.get("19")["metadata"]
    assert "hidden" not in metadata["raw_details"]
    assert "quoted value" not in metadata["password"]
    assert len(metadata["large"]) == 256_000
    store.close()


def test_v2_migration_preserves_submitted_provenance(tmp_path):
    path = tmp_path / "v2.sqlite3"
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE job_records (
        job_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL DEFAULT '', provider_id TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL DEFAULT '', exit_code TEXT NOT NULL DEFAULT '', submitted_at REAL NOT NULL,
        updated_at REAL NOT NULL, script_path TEXT NOT NULL DEFAULT '', script_hash TEXT NOT NULL DEFAULT '',
        script_text TEXT NOT NULL DEFAULT '', resources_json TEXT NOT NULL DEFAULT '{}',
        timing_json TEXT NOT NULL DEFAULT '{}', scope TEXT NOT NULL DEFAULT 'app-submitted')""")
    db.execute("INSERT INTO job_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        "12", "profile", "slurm", "COMPLETED", "0:0", 100, 200, "/work/run.sh", "hash",
        "#!/bin/sh", '{"cpus":2}', '{"elapsed":"00:01"}', "app-submitted"))
    db.execute("PRAGMA user_version=2")
    db.commit()
    db.close()
    store = JobRecordStore(path)
    row = store.get("12", profile_id="profile", provider_id="slurm")
    assert row["script_text"] == "#!/bin/sh"
    assert row["script_path"] == "/work/run.sh"
    assert row["resources"]["cpus"] == 2
    assert store._db.execute("PRAGMA user_version").fetchone()[0] == 4
    store.close()


def test_v2_migration_writes_owner_only_rollback_snapshot(tmp_path):
    path = tmp_path / "history.sqlite3"
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE job_records (
        job_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL DEFAULT '',
        provider_id TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '',
        exit_code TEXT NOT NULL DEFAULT '', submitted_at REAL NOT NULL,
        updated_at REAL NOT NULL, script_path TEXT NOT NULL DEFAULT '',
        script_hash TEXT NOT NULL DEFAULT '', script_text TEXT NOT NULL DEFAULT '',
        resources_json TEXT NOT NULL DEFAULT '{}',
        timing_json TEXT NOT NULL DEFAULT '{}',
        scope TEXT NOT NULL DEFAULT 'app-submitted')""")
    db.execute(
        "INSERT INTO job_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("888", "p", "truba", "COMPLETED", "0:0", 10, 20,
         "/work/old.slurm", "hash", "#!/bin/sh", "{}", "{}", "app-submitted"),
    )
    db.execute("PRAGMA user_version = 2")
    db.commit()
    db.close()

    upgraded = JobRecordStore(path)
    assert upgraded.get("888", profile_id="p", provider_id="truba")["state"] == "COMPLETED"
    upgraded.close()

    backups = list(tmp_path.glob("history.sqlite3.before-v4-*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as previous:
        assert previous.execute("PRAGMA user_version").fetchone()[0] == 2
        original = previous.execute(
            "SELECT job_id, profile_id, script_text FROM job_records"
        ).fetchone()
        assert original == ("888", "p", "#!/bin/sh")
    if __import__("os").name == "posix":
        assert backups[0].stat().st_mode & 0o077 == 0

    reopened = JobRecordStore(path)
    assert reopened.get("888", profile_id="p", provider_id="truba") is not None
    reopened.close()
    assert len(list(tmp_path.glob("history.sqlite3.before-v4-*.sqlite3"))) == 1


def test_future_schema_rejected_without_quarantine_or_data_loss(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE future_data (value TEXT)")
        db.execute("INSERT INTO future_data VALUES ('preserved')")
        db.execute("PRAGMA user_version = 5")
    with pytest.raises(ValueError, match="unsupported job record schema"):
        JobRecordStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
        assert db.execute("SELECT value FROM future_data").fetchone()[0] == "preserved"
    assert not list(tmp_path.glob("future.sqlite3.corrupt*"))


def test_legacy_explicit_submission_can_reuse_deleted_local_identity(tmp_path):
    store = JobRecordStore(tmp_path / "legacy-resubmit.sqlite3")
    identity = {"job_id": "55", "profile_id": "p", "cluster_id": "c", "provider_id": "truba"}
    store.upsert({**identity, "state": "SUBMITTED", "script_hash": "old"})
    assert store.delete_details([identity]) == 1
    assert not store.record_observation({**identity, "state": "COMPLETED"})
    # Legacy JobProvenanceCapture.upsert supplies no explicit "source" key.
    store.upsert({**identity, "state": "SUBMITTED", "script_hash": "new"})
    recovered = store.get("55", profile_id="p", cluster_id="c", provider_id="truba")
    assert recovered["script_hash"] == "new"
    assert recovered["state"] == "SUBMITTED"
    store.close()


def test_noncorrupt_migration_error_keeps_original_database(tmp_path):
    path = tmp_path / "legacy-unexpected-schema.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE job_records (
            job_id TEXT PRIMARY KEY, profile_id TEXT,
            provider_id TEXT, state TEXT, scope TEXT
        )""")
        db.execute(
            "INSERT INTO job_records VALUES (?, ?, ?, ?, ?)",
            ("777", "profile-a", "slurm", "COMPLETED", "app-submitted"),
        )
        # A malformed pre-existing workspace table produces a schema error,
        # not SQLITE_CORRUPT; the original database must remain untouched.
        db.execute("CREATE TABLE job_workspaces (job_id TEXT)")
        db.execute("PRAGMA user_version = 2")

    with pytest.raises(sqlite3.OperationalError):
        JobRecordStore(path)

    assert path.exists()
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute(
            "SELECT job_id, profile_id, state FROM job_records"
        ).fetchone() == ("777", "profile-a", "COMPLETED")
    assert list(tmp_path.glob("legacy-unexpected-schema.sqlite3.corrupt-*")) == []
