"""Profile-scoped, versioned SQLite storage for Slurm job workspaces."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from hpc_gui.core.paths import app_data_dir
from hpc_gui.services.job_security import is_sensitive_key, redact_sensitive_text


SCHEMA_VERSION = 4
MAX_OUTPUT_CHARS = 256_000
_IDENTITY_FIELDS = ("profile_id", "cluster_id", "provider_id", "job_id", "component_id")
_JSON_FIELDS = ("metadata", "resources", "timing", "paths", "details", "outputs")
def default_job_record_path() -> Path:
    return app_data_dir() / "job_records.sqlite3"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _bound_output(value: Any) -> Any:
    if isinstance(value, str):
        redacted = redact_sensitive_text(value)
        return redacted[-MAX_OUTPUT_CHARS:]
    if isinstance(value, Mapping):
        return {
            str(key): ("[REDACTED]" if is_sensitive_key(str(key)) and item not in (None, "", [], {})
                       else _bound_output(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_bound_output(item) for item in value[-100:]]
    return value


class JobRecordStore:
    """Persist jobs by profile, cluster, provider, scheduler ID and component.

    The v2 ``job_records`` table is retained as a migration source.  v4 data is
    written to ``job_workspaces`` and never uses a bare scheduler ID as a key.
    Empty observations do not erase previously validated values.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or default_job_record_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        try:
            self._connect()
            self._migrate()
        except sqlite3.DatabaseError:
            try:
                self._db.close()
            except (AttributeError, sqlite3.DatabaseError):
                pass
            suffix = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
            backup = self.path.with_suffix(self.path.suffix + f".corrupt-{suffix}")
            counter = 1
            while backup.exists():
                backup = self.path.with_suffix(self.path.suffix + f".corrupt-{suffix}-{counter}")
                counter += 1
            if self.path.exists():
                self.path.replace(backup)
            for suffix_name in ("-wal", "-shm"):
                sidecar = Path(str(self.path) + suffix_name)
                if sidecar.exists():
                    sidecar.replace(Path(str(backup) + suffix_name))
            self._connect()
            self._migrate()
        if os.name == "posix":
            self.path.chmod(0o600)

    def _connect(self) -> None:
        self._db = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA busy_timeout=15000")

    def _migrate(self) -> None:
        version = int(self._db.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise sqlite3.DatabaseError("unsupported job record schema")
        with self._db:
            self._db.execute("""CREATE TABLE IF NOT EXISTS job_workspaces (
                profile_id TEXT NOT NULL DEFAULT '', cluster_id TEXT NOT NULL DEFAULT '',
                provider_id TEXT NOT NULL DEFAULT '', job_id TEXT NOT NULL,
                component_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'observed',
                state TEXT NOT NULL DEFAULT '', first_seen REAL NOT NULL,
                updated_at REAL NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}',
                resources_json TEXT NOT NULL DEFAULT '{}', timing_json TEXT NOT NULL DEFAULT '{}',
                paths_json TEXT NOT NULL DEFAULT '{}', details_json TEXT NOT NULL DEFAULT '{}',
                outputs_json TEXT NOT NULL DEFAULT '{}', deleted_details INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(profile_id, cluster_id, provider_id, job_id, component_id)
            )""")
            self._db.execute("""CREATE TABLE IF NOT EXISTS job_workspace_tombstones (
                profile_id TEXT NOT NULL, cluster_id TEXT NOT NULL, provider_id TEXT NOT NULL,
                job_id TEXT NOT NULL, component_id TEXT NOT NULL DEFAULT '', deleted_at REAL NOT NULL,
                PRIMARY KEY(profile_id, cluster_id, provider_id, job_id, component_id)
            )""")
            if version < 4:
                self._migrate_legacy_rows()
                self._db.execute("PRAGMA user_version = 4")

    def _migrate_legacy_rows(self) -> None:
        exists = self._db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_records'"
        ).fetchone()
        if not exists:
            return
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(job_records)")}
        if not {"job_id", "profile_id", "provider_id"}.issubset(columns):
            return
        rows = self._db.execute("SELECT * FROM job_records").fetchall()
        for row in rows:
            value = dict(row)
            payload = {
                "job_id": value.get("job_id"), "profile_id": value.get("profile_id", ""),
                "provider_id": value.get("provider_id", ""), "state": value.get("state", ""),
                "source": value.get("scope", "app-submitted"),
                "metadata": {"exit_code": value.get("exit_code", ""),
                             "script_hash": value.get("script_hash", ""),
                             "script_text": value.get("script_text", "")},
                "resources": self._decode(value.get("resources_json")),
                "timing": self._decode(value.get("timing_json")),
                "paths": {"script_path": value.get("script_path", "")},
                "first_seen": value.get("submitted_at") or time.time(),
                "updated_at": value.get("updated_at") or time.time(),
            }
            self._write(payload, allow_resurrect=True)

    @staticmethod
    def _decode(value: Any) -> dict[str, Any]:
        try:
            decoded = json.loads(value or "{}")
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError):
            return {}

    @staticmethod
    def _identity(record: Mapping[str, Any]) -> tuple[str, ...]:
        job_id = _text(record.get("job_id"))
        if not job_id:
            raise ValueError("job_id is required")
        return tuple(_text(record.get(key)) for key in _IDENTITY_FIELDS[:-2]) + (
            job_id, _text(record.get("component_id")),
        )

    def _find(self, identity: tuple[str, ...]):
        return self._db.execute(
            "SELECT * FROM job_workspaces WHERE profile_id=? AND cluster_id=? "
            "AND provider_id=? AND job_id=? AND component_id=?", identity,
        ).fetchone()

    def _write(self, record: Mapping[str, Any], *, allow_resurrect: bool = False) -> bool:
        with self._lock:
            return self._write_locked(record, allow_resurrect=allow_resurrect)

    def _write_locked(self, record: Mapping[str, Any], *, allow_resurrect: bool = False) -> bool:
        identity = self._identity(record)
        if not any(identity[:3]):
            candidates = self._db.execute(
                "SELECT profile_id,cluster_id,provider_id,job_id,component_id "
                "FROM job_workspaces WHERE job_id=? AND component_id=?",
                (identity[3], identity[4]),
            ).fetchall()
            if len(candidates) == 1:
                identity = tuple(candidates[0])
        if not allow_resurrect and self._db.execute(
            "SELECT 1 FROM job_workspace_tombstones WHERE profile_id=? AND cluster_id=? "
            "AND provider_id=? AND job_id=? AND component_id=?", identity,
        ).fetchone():
            return False
        if allow_resurrect:
            self._db.execute(
                "DELETE FROM job_workspace_tombstones WHERE profile_id=? AND cluster_id=? "
                "AND provider_id=? AND job_id=? AND component_id=?", identity,
            )
        old = self._find(identity)
        now = time.time()
        old_value = self._row(old) if old else {}
        json_values = {}
        for key in _JSON_FIELDS:
            incoming = record.get(key)
            merged = dict(old_value.get(key) or {})
            if isinstance(incoming, Mapping):
                for field, value in incoming.items():
                    if value not in (None, "", [], {}):
                        value = "[REDACTED]" if is_sensitive_key(str(field)) else _bound_output(value)
                        merged[str(field)] = value
            json_values[key] = _json(merged)
        first_seen = float(record.get("first_seen") or record.get("submitted_at") or
                           old_value.get("first_seen") or now)
        data = (*identity, _text(record.get("source") or old_value.get("source") or "app-submitted"),
                _text(record.get("state") or old_value.get("state")), first_seen, now,
                *(json_values[key] for key in _JSON_FIELDS), 0)
        with self._db:
            self._db.execute("""INSERT INTO job_workspaces (
                profile_id,cluster_id,provider_id,job_id,component_id,source,state,first_seen,
                updated_at,metadata_json,resources_json,timing_json,paths_json,details_json,
                outputs_json,deleted_details) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(profile_id,cluster_id,provider_id,job_id,component_id) DO UPDATE SET
                source=excluded.source,state=excluded.state,updated_at=excluded.updated_at,
                metadata_json=excluded.metadata_json,resources_json=excluded.resources_json,
                timing_json=excluded.timing_json,paths_json=excluded.paths_json,
                details_json=excluded.details_json,outputs_json=excluded.outputs_json""", data)
        return True

    def upsert(self, record: Mapping[str, Any]) -> None:
        self._write(record, allow_resurrect=_text(record.get("source")) == "submitted")

    def record_observation(self, record: Mapping[str, Any]) -> bool:
        """Save a queue/accounting observation unless the user deleted details."""
        return self._write(record)

    def get(self, job_id: str, *, profile_id: str = "", cluster_id: str = "",
            provider_id: str = "", component_id: str = "") -> dict[str, Any] | None:
        with self._lock:
            if profile_id or cluster_id or provider_id:
                row = self._find((_text(profile_id), _text(cluster_id), _text(provider_id),
                                  _text(job_id), _text(component_id)))
            else:
                rows = self._db.execute("SELECT * FROM job_workspaces WHERE job_id=?", (_text(job_id),)).fetchall()
                row = rows[0] if len(rows) == 1 else None
            return self._row(row) if row else None

    def update_observation(self, job_id: str, *, profile_id: str = "", cluster_id: str = "",
                           provider_id: str = "", component_id: str = "", state: str = "",
                           timing: Mapping[str, Any] | None = None,
                           resources: Mapping[str, Any] | None = None, exit_code: str = "") -> None:
        current = self.get(job_id, profile_id=profile_id, cluster_id=cluster_id,
                           provider_id=provider_id, component_id=component_id)
        if current is None:
            return
        metadata = dict(current["metadata"])
        if exit_code:
            metadata["exit_code"] = exit_code
        self._write({**current, "state": state, "metadata": metadata,
                     "timing": timing or {}, "resources": resources or {}})

    def delete_details(self, identities: list[Mapping[str, Any]]) -> int:
        """Delete local details/path/output payloads and tombstone each scope."""
        deleted = 0
        with self._lock, self._db:
            for item in identities:
                identity = self._identity(item)
                row = self._find(identity)
                if row:
                    self._db.execute("DELETE FROM job_workspaces WHERE profile_id=? AND cluster_id=? "
                                     "AND provider_id=? AND job_id=? AND component_id=?", identity)
                    deleted += 1
                self._db.execute("INSERT OR IGNORE INTO job_workspace_tombstones VALUES (?,?,?,?,?,?)",
                                 (*identity, time.time()))
        return deleted

    def list(self, limit: int = 100, *, profile_id: str | None = None,
             cluster_id: str | None = None, provider_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            clauses, values = [], []
            for key, value in (("profile_id", profile_id), ("cluster_id", cluster_id), ("provider_id", provider_id)):
                if value is not None:
                    clauses.append(f"{key}=?")
                    values.append(_text(value))
            where = "WHERE " + " AND ".join(clauses) if clauses else ""
            rows = self._db.execute(f"SELECT * FROM job_workspaces {where} ORDER BY first_seen DESC LIMIT ?",
                                    (*values, max(1, int(limit)))).fetchall()
            return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
        value = dict(row)
        for key in _JSON_FIELDS:
            value[key] = JobRecordStore._decode(value.pop(f"{key}_json", "{}"))
        value["script_path"] = value["paths"].get("script_path", "")
        value["script_text"] = value["metadata"].get("script_text", "")
        value["script_hash"] = value["metadata"].get("script_hash", "")
        value["exit_code"] = value["metadata"].get("exit_code", "")
        value["submitted_at"] = value["first_seen"]
        value["scope"] = value["source"]
        return value

    def close(self) -> None:
        self._db.close()
