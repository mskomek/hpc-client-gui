"""Accounting and metadata refresh callbacks for the Jobs shell."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def make_details_callbacks(context):
    def cancel(job_id):
        slurm = context.resolve_slurm()
        if slurm and hasattr(slurm, "scancel"):
            return slurm.scancel(job_id)
        return None

    def final_state(job_id):
        slurm = context.resolve_slurm()
        if slurm and hasattr(slurm, "job_state"):
            return slurm.job_state(job_id)
        return ""

    def refresh_sacct(job_id):
        slurm = context.resolve_slurm()
        profile = context.resolve_profile()
        result = ""
        try:
            if slurm:
                contract_result = context.execute_contract_adapter("accounting", slurm, job_id)
                if contract_result is not None:
                    result = str(contract_result or "")
                else:
                    result = _query_job_accounting(slurm, str(profile.get("username", "")), job_id)
        except Exception:
            result = ""
        if result:
            return result
        record = context.local_job_record(job_id)
        return str(((record or {}).get("details", {})).get("raw_accounting", ""))

    def refresh_job_metadata(job_id):
        """Return the full accounting row for a job, including file paths."""
        from hpc_gui.services.jobs_history import parse_sacct_history

        slurm = context.resolve_slurm()
        profile = context.resolve_profile()
        if not slurm:
            return {}
        job_id = str(job_id or "").strip()
        cached = context.cached_history_job(job_id)
        if cached:
            return cached
        username = str(profile.get("username", ""))
        history = getattr(slurm, "sacct_history_result", None)
        if callable(history):
            response = history(username, 365)
            if getattr(response, "ok", True) is False:
                raise RuntimeError(getattr(response, "message", "sacct history is unavailable"))
            raw = getattr(response, "stdout", response)
        else:
            result = getattr(slurm, "sacct_result", None)
            if callable(result):
                response = result(username)
                if getattr(response, "ok", True) is False:
                    raise RuntimeError(getattr(response, "message", "sacct is unavailable"))
                raw = getattr(response, "stdout", response)
            elif callable(getattr(slurm, "sacct", None)):
                raw = slurm.sacct(username)
            else:
                return {}
        row = next(
            (item for item in parse_sacct_history(str(raw or ""))
             if str(item.get("job_id", "")) == job_id),
            None,
        )
        if row:
            row["workdir_source"] = "sacct" if row.get("workdir") else ""
            return row
        record = context.local_job_record(job_id)
        if not record:
            return {}
        restored = {
            **record.get("metadata", {}),
            **record.get("paths", {}),
            "state": record.get("state", ""),
            "source": "local_archive",
        }
        restored.update(record.get("details", {}))
        return restored

    def show_job_details(job_id):
        slurm = context.resolve_slurm()
        if not slurm:
            return ""
        contract_result = context.execute_contract_adapter("job_details", slurm, job_id)
        if contract_result is not None:
            return contract_result
        raw = str(slurm.scontrol_show_job(job_id) or "")
        if raw.strip():
            return raw
        record = context.local_job_record(job_id)
        return str(((record or {}).get("details", {})).get("raw_details", ""))

    def has_status_capability():
        slurm = context.resolve_slurm()
        if not slurm:
            return False
        from hpc_gui.services.adapter_registry import get_adapter
        from hpc_gui.services.provider_contract import extract_contract

        contract = extract_contract(context.resolve_provider_config())
        if contract.cluster_status_adapter:
            return get_adapter(contract.cluster_status_adapter) is not None
        return callable(getattr(slurm, "lssrv", None))

    def refresh_lssrv(job_id=""):
        slurm = context.resolve_slurm()
        if not slurm or not callable(getattr(slurm, "lssrv", None)):
            raise RuntimeError(t("jobs_outputs.provider_status_unavailable"))
        result = context.execute_contract_adapter("cluster_status", slurm, job_id)
        return result if result is not None else str(slurm.lssrv() or "")

    return {
        "cancel": cancel,
        "final_state": final_state,
        "refresh_sacct": refresh_sacct,
        "refresh_job_metadata": refresh_job_metadata,
        "show_job_details": show_job_details,
        "has_status_capability": has_status_capability,
        "refresh_lssrv": refresh_lssrv,
    }


def _query_job_accounting(slurm, username, job_id):
    query = getattr(slurm, "sacct_job", None)
    if callable(query):
        return str(query(str(job_id)) or "")
    query = getattr(slurm, "sacct", None)
    if not callable(query):
        return ""
    try:
        return str(query(username, job_id=job_id) or "")
    except TypeError:
        return str(query(username) or "")
