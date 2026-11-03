"""Shared profile and service access for Jobs shell callback groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class JobsCallbackContext:
    """Resolve the active session lazily for the Jobs workflow callbacks."""

    session_state: Any
    parent: Any
    lifecycle: Any

    @property
    def state(self) -> dict:
        return self.session_state if isinstance(self.session_state, dict) else {}

    def _session(self) -> dict:
        session = self.state.get("session") or {}
        return session if isinstance(session, dict) else {}

    def resolve_slurm(self):
        return self._session().get("slurm")

    def resolve_files(self):
        return self._session().get("files")

    def resolve_profile(self) -> dict:
        profile = self._session().get("profile") or {}
        return profile if isinstance(profile, dict) else {}

    def resolve_provider_config(self) -> dict:
        profile = self.resolve_profile()
        provider = profile.get("provider_template")
        return provider if isinstance(provider, dict) else profile

    def profile_identity(self) -> dict[str, str]:
        profile = self.resolve_profile()
        return {
            "profile_id": str(profile.get("id", profile.get("profile_id", ""))),
            "cluster_id": str(
                profile.get("cluster_id", profile.get("id", profile.get("profile_id", "")))
            ),
            "provider_id": str(profile.get("provider_id", profile.get("provider", ""))),
        }

    def scoped_record(self, job_id: Any) -> dict[str, str]:
        return {**self.profile_identity(), "job_id": str(job_id)}

    def job_store(self):
        from hpc_gui.services.job_record_store import JobRecordStore

        if not isinstance(self.session_state, dict):
            return JobRecordStore()
        store = self.session_state.get("_job_record_store")
        if store is None:
            store = JobRecordStore()
            self.session_state["_job_record_store"] = store
        return store

    def local_job_record(self, job_id: Any):
        return self.job_store().get(str(job_id), **self.profile_identity())

    def execute_contract_adapter(self, section: str, slurm: Any, job_id: Any = ""):
        from hpc_gui.services.adapter_registry import get_adapter
        from hpc_gui.services.provider_contract import execute_adapter, extract_contract

        contract = extract_contract(self.resolve_provider_config())
        adapter_id = getattr(contract, f"{section}_adapter", None)
        if not adapter_id:
            return None
        if get_adapter(adapter_id) is None:
            raise RuntimeError(f"Configured provider adapter is unavailable: {adapter_id}")
        profile = self.resolve_profile()
        return execute_adapter(
            adapter_id,
            slurm_backend=slurm,
            job_id=str(job_id),
            user=str(profile.get("username", "")),
            profile=profile,
        )

    def scontrol_details(self, slurm: Any, job_id: Any):
        from hpc_gui.services.slurm_models import parse_scontrol

        raw = slurm.scontrol_show_job(job_id)
        return parse_scontrol(str(raw or ""), str(job_id))

    def _history_identity(self) -> tuple[str, str, str, str]:
        profile = self.resolve_profile()
        return (
            str(profile.get("id", profile.get("profile_id", ""))),
            str(profile.get("cluster_id", "")),
            str(profile.get("provider_id", "")),
            str(profile.get("username", "")),
        )

    def cached_history_job(self, job_id: Any) -> dict | None:
        identity = self._history_identity()
        cache = self.state.get("_jobs_history_cache", {})
        for key, entry in cache.items():
            if tuple(key[:4]) != identity:
                continue
            row = next(
                (item for item in entry.get("rows", ())
                 if str(item.get("job_id", "")) == str(job_id)),
                None,
            )
            if row:
                return dict(row)
        return None

    def query_sacct_job(self, job_id: Any) -> dict | None:
        from hpc_gui.services.jobs_history import parse_sacct_history

        slurm = self.resolve_slurm()
        query = getattr(slurm, "sacct_job", None) if slurm else None
        if not callable(query):
            return None
        rows = parse_sacct_history(str(query(str(job_id)) or ""))
        return next(
            (row for row in rows if str(row.get("job_id", "")) == str(job_id)),
            None,
        )
