"""wx shell jobs workflows."""
from __future__ import annotations

from pathlib import PurePosixPath
import time
from hpc_gui.core.i18n import t
from hpc_gui.wx_shell_files import _remote_files_callbacks


def _jobs_callbacks(session_state, parent, lifecycle):
    from hpc_gui.services.adapter_registry import get_adapter
    from hpc_gui.services.provider_contract import execute_adapter, extract_contract

    def _resolve_slurm():
        session = (session_state or {}).get("session") or {}
        return session.get("slurm")

    def _resolve_files():
        session = (session_state or {}).get("session") or {}
        return session.get("files")

    def _resolve_profile():
        session = (session_state or {}).get("session") or {}
        return session.get("profile") or {}

    def _resolve_provider_config():
        profile = _resolve_profile()
        provider = profile.get("provider_template")
        return provider if isinstance(provider, dict) else profile

    def _profile_identity():
        profile = _resolve_profile()
        return {
            "profile_id": str(profile.get("id", profile.get("profile_id", ""))),
            "cluster_id": str(profile.get("cluster_id", profile.get("id", profile.get("profile_id", "")))),
            "provider_id": str(profile.get("provider_id", profile.get("provider", ""))),
        }

    def _execute_contract_adapter(section, slurm, job_id=""):
        contract = extract_contract(_resolve_provider_config())
        adapter_id = getattr(contract, f"{section}_adapter", None)
        if not adapter_id:
            return None
        if get_adapter(adapter_id) is None:
            raise RuntimeError(f"Configured provider adapter is unavailable: {adapter_id}")
        profile = _resolve_profile()
        return execute_adapter(
            adapter_id,
            slurm_backend=slurm,
            job_id=str(job_id),
            user=str(profile.get("username", "")),
            profile=profile,
        )

    def list_jobs():
        from hpc_gui.services.jobs_history import merge_job_sources, parse_sacct_history
        slurm = _resolve_slurm()
        profile = _resolve_profile()
        if not slurm:
            return ()
        username = str(profile.get("username", ""))
        history_days = int(owner_state.get("_jobs_history_days", 7)) if isinstance(
            owner_state := (session_state if isinstance(session_state, dict) else {}), dict
        ) else 7
        if history_days not in {7, 30, 90, 365}:
            history_days = 7
        squeue_result = getattr(slurm, "squeue_result", None)
        queue_response = squeue_result(username) if callable(squeue_result) else slurm.squeue(username)
        if getattr(queue_response, "ok", True) is False:
            raise RuntimeError(getattr(queue_response, "message", "squeue is unavailable"))
        raw = getattr(queue_response, "stdout", queue_response)
        rows = []
        for line in str(raw or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("jobid"):
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) < 6:
                continue
            job_id = parts[0]
            partition = parts[1] if len(parts) > 1 else ""
            name = parts[2] if len(parts) > 2 else ""
            user = parts[3] if len(parts) > 3 else ""
            state = parts[4] if len(parts) > 4 else ""
            elapsed = parts[5] if len(parts) > 5 else ""
            nodes = parts[6] if len(parts) > 6 else ""
            cpus = parts[7] if len(parts) > 7 else ""
            reason = parts[8] if len(parts) > 8 else ""
            submit_time = parts[9] if len(parts) > 9 else ""
            rows.append({
                "id": job_id,
                "job_id": job_id,
                "name": name,
                "state": state,
                "partition": partition,
                "elapsed": elapsed,
                "nodes": nodes,
                "cpus": cpus,
                "reason": reason,
                "user": user,
                "submit_time": submit_time,
                "source": "squeue",
            })
        if not rows and str(raw or "").strip():
            # Retain support for existing profiles whose squeue template emits
            # Slurm's human-readable columns instead of the pipe format.
            from hpc_gui.services.slurm_models import parse_squeue_result
            rows = [
                {
                    "id": job.job_id, "job_id": job.job_id, "name": job.name,
                    "state": job.state, "partition": job.partition,
                    "elapsed": job.elapsed, "nodes": job.nodes, "cpus": job.cpus,
                    "reason": job.reason, "user": job.user, "source": "squeue",
                }
                for job in parse_squeue_result(raw)
            ]
        cache = owner_state.setdefault("_jobs_history_cache", {})
        identity = (
            str(profile.get("id", profile.get("profile_id", ""))),
            str(profile.get("cluster_id", "")),
            str(profile.get("provider_id", "")), username, history_days,
        )
        entry = cache.setdefault(identity, {
            "rows": [], "read_at": -60.0, "error": "", "active_ids": None,
        })
        active_ids = frozenset(row["job_id"] for row in rows)
        queue_changed = entry["active_ids"] is not None and active_ids != entry["active_ids"]
        first_queue_read = entry["active_ids"] is None
        entry["active_ids"] = active_ids
        stale = False
        if first_queue_read or queue_changed or time.monotonic() - entry["read_at"] >= 60:
            try:
                sacct_history = getattr(slurm, "sacct_history_result", None)
                sacct_result = getattr(slurm, "sacct_result", None)
                if callable(sacct_history):
                    response = sacct_history(username, history_days)
                    if getattr(response, "ok", True) is False:
                        raise RuntimeError(getattr(response, "message", "sacct is unavailable"))
                    accounting = getattr(response, "stdout", response)
                elif callable(sacct_result):
                    response = sacct_result(username)
                    if getattr(response, "ok", True) is False:
                        raise RuntimeError(getattr(response, "message", "sacct is unavailable"))
                    accounting = getattr(response, "stdout", response)
                else:
                    accounting = slurm.sacct(username)
                entry["rows"] = parse_sacct_history(str(accounting or ""))
                entry["read_at"] = time.monotonic()
                entry["error"] = ""
            except Exception as error:
                entry["error"] = str(error) or "sacct is unavailable"
                stale = True
        else:
            stale = bool(entry["error"])
        merged = merge_job_sources(rows, entry["rows"])
        return {
            "jobs": merged,
            "active_job_ids": tuple(row["job_id"] for row in rows),
            "history_stale": stale,
            "history_error": entry["error"],
        }

    def set_history_days(days):
        value = int(days)
        if value not in {7, 30, 90, 365}:
            raise ValueError("unsupported history window")
        if isinstance(session_state, dict):
            session_state["_jobs_history_days"] = value
        return value

    def can_load_older_history():
        slurm = _resolve_slurm()
        return callable(getattr(slurm, "sacct_history_result", None))

    def _scontrol_details(slurm, job_id):
        from hpc_gui.services.slurm_models import parse_scontrol
        return parse_scontrol(str(slurm.scontrol_show_job(job_id) or ""), str(job_id))

    def read_output(job_id):
        slurm = _resolve_slurm()
        files = _resolve_files()
        if not slurm or not files:
            return {}
        details = _scontrol_details(slurm, job_id)
        stdout_path, stderr_path = details.stdout_path, details.stderr_path
        if not stdout_path and not stderr_path:
            from hpc_gui.services.jobs_history import parse_sacct_history
            history_cache = (session_state or {}).get("_jobs_history_cache", {})
            profile = _resolve_profile()
            identity = (
                str(profile.get("id", profile.get("profile_id", ""))),
                str(profile.get("cluster_id", "")),
                str(profile.get("provider_id", "")),
                str(profile.get("username", "")),
            )
            cached = next((
                row for key, entry in history_cache.items() if tuple(key[:4]) == identity
                for row in entry.get("rows", ())
                if str(row.get("job_id", "")) == str(job_id)
            ), None)
            if cached is None and callable(getattr(slurm, "sacct_job", None)):
                cached = next((row for row in parse_sacct_history(slurm.sacct_job(str(job_id)))
                               if str(row.get("job_id", "")) == str(job_id)), None)
            stdout_path = str((cached or {}).get("stdout_path", ""))
            stderr_path = str((cached or {}).get("stderr_path", ""))
        return {
            "stdout": files.read_text(stdout_path) if stdout_path else "",
            "stderr": files.read_text(stderr_path) if stderr_path else "",
        }

    def read_remote_path(path):
        files = _resolve_files()
        if not files or not path:
            raise FileNotFoundError(path)
        return files.read_text(path)

    def stat_remote_path(path):
        files = _resolve_files()
        if not files or not path:
            raise FileNotFoundError(path)
        return files.stat(path)

    def list_job_files(job_id, workdir=""):
        test_files = session_state.get("_test_job_files")
        if test_files is not None:
            if isinstance(test_files, dict):
                return tuple(test_files.get(str(job_id), ()))
            return tuple(test_files)
        slurm = _resolve_slurm()
        files = _resolve_files()
        if not slurm or not files or not hasattr(files, "iterdir_entries"):
            return ()
        try:
            if not workdir:
                details = _scontrol_details(slurm, job_id)
                workdir = details.workdir
                if not workdir:
                    workdir = str(PurePosixPath(details.stdout_path).parent) if details.stdout_path else ""
            if not workdir:
                from hpc_gui.services.jobs_history import parse_sacct_history
                history_cache = (session_state or {}).get("_jobs_history_cache", {})
                profile = _resolve_profile()
                identity = (
                    str(profile.get("id", profile.get("profile_id", ""))),
                    str(profile.get("cluster_id", "")),
                    str(profile.get("provider_id", "")),
                    str(profile.get("username", "")),
                )
                cached = next((
                    row for key, entry in history_cache.items() if tuple(key[:4]) == identity
                    for row in entry.get("rows", ())
                    if str(row.get("job_id", "")) == str(job_id)
                ), None)
                if cached is None and callable(getattr(slurm, "sacct_job", None)):
                    cached = next((row for row in parse_sacct_history(slurm.sacct_job(str(job_id)))
                                   if str(row.get("job_id", "")) == str(job_id)), None)
                workdir = str((cached or {}).get("workdir", ""))
            if not workdir:
                return ()
            return tuple(files.iterdir_entries(workdir))
        except Exception:
            return ()

    def _cancel(job_id):
        slurm = _resolve_slurm()
        if slurm and hasattr(slurm, "scancel"):
            return slurm.scancel(job_id)
        return None

    def _final_state(job_id):
        slurm = _resolve_slurm()
        if slurm and hasattr(slurm, "job_state"):
            return slurm.job_state(job_id)
        return ""

    def _refresh_sacct(job_id):
        slurm = _resolve_slurm()
        profile = _resolve_profile()
        if not slurm:
            return ""
        contract_result = _execute_contract_adapter("accounting", slurm, job_id)
        if contract_result is not None:
            return contract_result
        sacct_job = getattr(slurm, "sacct_job", None)
        if callable(sacct_job):
            return sacct_job(str(job_id))
        if not hasattr(slurm, "sacct"):
            return ""
        try:
            return str(slurm.sacct(str(profile.get("username", "")), job_id=job_id) or "")
        except TypeError:
            return str(slurm.sacct(str(profile.get("username", ""))) or "")

    def _refresh_job_metadata(job_id):
        """Return the full sacct row for a selected job, including file paths."""
        from hpc_gui.services.jobs_history import parse_sacct_history

        slurm = _resolve_slurm()
        profile = _resolve_profile()
        if not slurm:
            return {}
        job_id = str(job_id or "").strip()
        username = str(profile.get("username", ""))
        identity = (
            str(profile.get("id", profile.get("profile_id", ""))),
            str(profile.get("cluster_id", "")),
            str(profile.get("provider_id", "")), username,
        )
        history_cache = (session_state or {}).get("_jobs_history_cache", {})
        for key, entry in history_cache.items():
            if tuple(key[:4]) != identity:
                continue
            cached = next((row for row in entry.get("rows", ())
                           if str(row.get("job_id", "")) == job_id), None)
            if cached:
                return dict(cached)

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
        return next((row for row in parse_sacct_history(str(raw or ""))
                     if str(row.get("job_id", "")) == job_id), {})

    def _show_job_details(job_id):
        slurm = _resolve_slurm()
        if not slurm:
            return ""
        contract_result = _execute_contract_adapter("job_details", slurm, job_id)
        if contract_result is not None:
            return contract_result
        return str(slurm.scontrol_show_job(job_id) or "")

    def _has_status_capability():
        slurm = _resolve_slurm()
        if not slurm:
            return False
        contract = extract_contract(_resolve_provider_config())
        if contract.cluster_status_adapter:
            return get_adapter(contract.cluster_status_adapter) is not None
        return callable(getattr(slurm, "lssrv", None))

    def _refresh_lssrv(_job_id=""):
        slurm = _resolve_slurm()
        if not slurm or not callable(getattr(slurm, "lssrv", None)):
            raise RuntimeError(t("jobs_outputs.provider_status_unavailable"))
        contract_result = _execute_contract_adapter("cluster_status", slurm, _job_id)
        if contract_result is not None:
            return contract_result
        return str(slurm.lssrv() or "")

    def _resolve_output_defs():
        from hpc_gui.services.output_channel_resolver import definitions_from_provider
        session = (session_state or {}).get("session") or {}
        profile = session.get("profile") or {}
        provider = profile.get("provider_template") if isinstance(profile, dict) else None
        config = provider if isinstance(provider, dict) else profile
        job_outputs = config.get("job_outputs") if isinstance(config, dict) else None
        return definitions_from_provider(job_outputs)

    def open_main_files(path="", highlight_path=""):
        main_notebook = session_state.get("_embedded_main_notebook")
        files_page = session_state.get("_embedded_files_page")
        remote_panel = session_state.get("_embedded_remote_files_panel")
        if main_notebook is None or files_page is None or remote_panel is None:
            return
        page_index = next(
            (index for index in range(main_notebook.GetPageCount())
             if main_notebook.GetPage(index) is files_page),
            -1,
        )
        if page_index >= 0:
            main_notebook.SetSelection(page_index)
        remote_notebook = getattr(remote_panel, "_wx_remote_notebook", None)
        tabs = getattr(remote_panel, "_wx_remote_tabs", ())
        if remote_notebook is not None and tabs:
            active_index = remote_notebook.GetSelection()
            if 0 <= active_index < len(tabs):
                tabs[active_index]["highlight_path"] = str(highlight_path or "")
        controls = getattr(remote_panel, "_wx_remote_controls", {})
        navigate = controls.get("navigate")
        load = controls.get("load")
        if callable(navigate):
            navigate(str(path or "/"))
        if callable(load):
            load()

    return {
        "list_jobs": list_jobs,
        "set_history_days": set_history_days,
        "can_load_older_history": can_load_older_history,
        "read_output": read_output,
        "read_remote_path": read_remote_path,
        "stat_remote_path": stat_remote_path,
        "list_job_files": list_job_files,
        "cancel": _cancel,
        "final_state": _final_state,
        "refresh_sacct": _refresh_sacct,
        "refresh_job_metadata": _refresh_job_metadata,
        "show_job_details": _show_job_details,
        "has_status_capability": _has_status_capability,
        "refresh_lssrv": _refresh_lssrv,
        "output_channel_defs": None,
        "output_channel_defs_provider": _resolve_output_defs,
        "open_main_files": open_main_files,
        "provider_filters": lambda: (_resolve_provider_config().get("file_filters", ()) if isinstance(_resolve_provider_config().get("file_filters", ()), (list, tuple)) else ()),
        "remote_files_callbacks": _remote_files_callbacks(session_state, parent, lifecycle),
        "generation": lambda: session_state.get("generation", 0),
        **_profile_identity(),
        "lifecycle": lifecycle,
        "session_state": session_state,
    }
