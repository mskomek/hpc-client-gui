import sqlite3

from hpc_gui.services.job_record_store import JobRecordStore


def test_create_insert_update_query_and_empty_db(tmp_path):
    store = JobRecordStore(tmp_path / "jobs.sqlite3")
    assert store.list() == []
    store.upsert({"job_id": "123", "profile_id": "p", "state": "PENDING", "resources": {"cpus": 4}})
    store.upsert({"job_id": "123", "state": "COMPLETED"})
    row = store.get("123")
    assert row["state"] == "COMPLETED"
    assert row["profile_id"] == ""
    assert row["scope"] == "app-submitted"
    store.close()


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
