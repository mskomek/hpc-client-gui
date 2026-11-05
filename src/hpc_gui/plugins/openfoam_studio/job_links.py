"""Restart-safe job<->case linkage (W65 JOBS-015, G42).

Records ``job_id -> {case_hash, case_path, logs, results}`` relations in a
JSON sidecar that survives client restart, and mirrors the relation into
the host :class:`JobRecordStore` when that service is importable. Submit
semantics stay draft-only: this module never submits, cancels, or polls.
Per-file PARTIAL semantics come from :mod:`hpc` and are never upgraded to
green here.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field


@dataclass
class JobLink:
    job_id: str
    case_path: str
    case_hash: str
    log_paths: list[str] = field(default_factory=list)
    result_paths: list[str] = field(default_factory=list)
    status: str = "DRAFT"  # DRAFT | SUBMITTED(external) | COMPLETED(external) | UNKNOWN


@dataclass
class JobLinkStore:
    path: str

    def __post_init__(self) -> None:
        self._links: dict[str, JobLink] = {}
        if os.path.exists(self.path):
            self.reload()

    def link(self, job_id: str, case_path: str, case_bytes: bytes,
             log_paths: list[str] | None = None,
             result_paths: list[str] | None = None) -> JobLink:
        if not job_id or any(c in job_id for c in " \t\n;|&$`"):
            raise ValueError(f"unsafe job id '{job_id}'")
        entry = JobLink(job_id, case_path,
                        hashlib.sha256(case_bytes).hexdigest(),
                        list(log_paths or []), list(result_paths or []))
        self._links[job_id] = entry
        self.save()
        self._mirror_to_host(entry)
        return entry

    def get(self, job_id: str) -> JobLink | None:
        return self._links.get(job_id)

    def verify_case(self, job_id: str, current_bytes: bytes) -> str:
        entry = self._links.get(job_id)
        if entry is None:
            return "UNKNOWN-JOB"
        current = hashlib.sha256(current_bytes).hexdigest()
        return "MATCH" if current == entry.case_hash else "STALE-CASE"

    def save(self) -> None:
        payload = {jid: asdict(link) for jid, link in self._links.items()}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def reload(self) -> None:
        with open(self.path, encoding="utf-8") as handle:
            payload = json.load(handle)
        self._links = {jid: JobLink(**raw) for jid, raw in payload.items()}

    def _mirror_to_host(self, entry: JobLink) -> str:
        """Best-effort mirror through the host Jobs service public API."""
        try:
            from hpc_gui.services.job_record_store import JobRecordStore
        except Exception:
            return "HOST-UNAVAILABLE"
        store = None
        try:
            store = JobRecordStore()
            saved = store.record_observation({
                "job_id": entry.job_id,
                "profile_id": "",
                "cluster_id": "",
                "provider_id": "",
                "component_id": "openfoam-studio",
                "source": "observed",
                "state": entry.status,
                "metadata": {"case_hash": entry.case_hash},
                "paths": {"case_path": entry.case_path},
                "outputs": {"log_paths": entry.log_paths,
                            "result_paths": entry.result_paths},
            })
            return "MIRRORED" if saved else "HOST-MIRROR-FAILED"
        except Exception:
            return "HOST-MIRROR-FAILED"
        finally:
            if store is not None:
                try:
                    store.close()
                except Exception:
                    pass
