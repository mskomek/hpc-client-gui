from __future__ import annotations

import hashlib
import time
from typing import Any, Mapping

from hpc_gui import __version__
from hpc_gui.services.job_record_store import JobRecordStore


def script_hash(script_text: str) -> str:
    return hashlib.sha256(script_text.encode("utf-8")).hexdigest()


class JobProvenanceCapture:
    def __init__(self, store: JobRecordStore):
        self.store = store

    def submitted(self, job_id: str, script_text: str, *, profile_id: str = "", provider_id: str = "", resources: Mapping[str, Any] | None = None, paths: Mapping[str, str] | None = None) -> dict[str, Any]:
        record = {
            "job_id": str(job_id), "profile_id": profile_id, "provider_id": provider_id,
            "state": "SUBMITTED", "submitted_at": time.time(), "script_path": str((paths or {}).get("script") or ""),
            "script_hash": script_hash(script_text), "script_text": script_text,
            "resources": dict(resources or {}), "timing": {"app_version": __version__, **dict(paths or {})},
        }
        self.store.upsert(record)
        return record

    def observation(self, job_id: str, *, state: str = "", elapsed: str = "", exit_code: str = "", max_rss: str = "", nodes: str = "", completed_at: float | None = None) -> None:
        self.store.update_observation(str(job_id), state=state, timing={"elapsed": elapsed, "completed_at": completed_at}, resources={"max_rss": max_rss, "nodes": nodes}, exit_code=exit_code)

    @staticmethod
    def analytics_job_id(job_id: str) -> str:
        return str(job_id).split("_", 1)[0]
