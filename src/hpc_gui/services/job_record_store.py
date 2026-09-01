"""Versioned local SQLite store for jobs submitted by this application."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

from hpc_gui.core.paths import app_data_dir


SCHEMA_VERSION = 1


def default_job_record_path() -> Path:
    return app_data_dir() / "job_records.sqlite3"


class JobRecordStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or default_job_record_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._db = sqlite3.connect(self.path)
            self._migrate()
        except (sqlite3.DatabaseError, OSError):
            try:
                self._db.close()
            except Exception:
                pass
            corrupt = self.path.with_suffix(self.path.suffix + ".corrupt")
            try:
                self.path.replace(corrupt)
            except OSError:
                pass
            self._db = sqlite3.connect(self.path)
            self._migrate()
        if os.name == "posix":
            self.path.chmod(0o600)

    def _migrate(self) -> None:
        version = int(self._db.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise sqlite3.DatabaseError("unsupported job record schema")
        if version < 1:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS job_records (
                    job_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL DEFAULT '',
                    provider_id TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '',
                    submitted_at REAL NOT NULL, updated_at REAL NOT NULL,
                    script_path TEXT NOT NULL DEFAULT '', script_hash TEXT NOT NULL DEFAULT '',
                    script_text TEXT NOT NULL DEFAULT '', resources_json TEXT NOT NULL DEFAULT '{}',
                    timing_json TEXT NOT NULL DEFAULT '{}', scope TEXT NOT NULL DEFAULT 'app-submitted'
                )"""
            )
            self._db.execute("PRAGMA user_version = 1")
            self._db.commit()

    def upsert(self, record: Mapping[str, Any]) -> None:
        job_id = str(record.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("job_id is required")
        now = time.time()
        self._db.execute(
            """INSERT INTO job_records
            (job_id, profile_id, provider_id, state, submitted_at, updated_at,
             script_path, script_hash, script_text, resources_json, timing_json, scope)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'app-submitted')
            ON CONFLICT(job_id) DO UPDATE SET
             profile_id=excluded.profile_id, provider_id=excluded.provider_id,
             state=excluded.state, updated_at=excluded.updated_at,
             script_path=excluded.script_path, script_hash=excluded.script_hash,
             script_text=excluded.script_text, resources_json=excluded.resources_json,
             timing_json=excluded.timing_json""",
            (
                job_id, str(record.get("profile_id") or ""), str(record.get("provider_id") or ""),
                str(record.get("state") or ""), float(record.get("submitted_at") or now), now,
                str(record.get("script_path") or ""), str(record.get("script_hash") or ""),
                str(record.get("script_text") or ""),
                json.dumps(record.get("resources") or {}, ensure_ascii=False),
                json.dumps(record.get("timing") or {}, ensure_ascii=False),
            ),
        )
        self._db.commit()

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM job_records WHERE job_id = ?", (str(job_id),)).fetchone()
        return self._row(row) if row else None

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT * FROM job_records ORDER BY submitted_at DESC LIMIT ?", (max(1, int(limit)),)).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row) -> dict[str, Any]:
        keys = ("job_id", "profile_id", "provider_id", "state", "submitted_at", "updated_at", "script_path", "script_hash", "script_text", "resources_json", "timing_json", "scope")
        result = dict(zip(keys, row))
        result["resources"] = json.loads(result.pop("resources_json"))
        result["timing"] = json.loads(result.pop("timing_json"))
        return result

    def close(self) -> None:
        self._db.close()
