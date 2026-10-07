"""wx shell jobs workflows."""
from __future__ import annotations

from pathlib import PurePosixPath
from hpc_gui.core.i18n import current_language, load_saved_language, set_language, subscribe_language_change, system_default_language, t, unsubscribe_language_change
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
        slurm = _resolve_slurm()
        profile = _resolve_profile()
        if not slurm:
            return ()
        raw = slurm.squeue(str(profile.get("username", "")))
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
            })
        return rows

    def read_output(job_id):
        slurm = _resolve_slurm()
        files = _resolve_files()
        if not slurm or not files:
            return {}
        metadata = str(slurm.scontrol_show_job(job_id) or "")
        paths = {}
        for key in ("StdOut", "StdErr"):
            for part in metadata.split():
                if part.startswith(f"{key}="):
                    paths[key] = part.split("=", 1)[1]
                    break
            else:
                paths[key] = ""
        return {
            "stdout": files.read_text(paths["StdOut"]) if paths["StdOut"] else "",
            "stderr": files.read_text(paths["StdErr"]) if paths["StdErr"] else "",
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
                meta = str(slurm.scontrol_show_job(job_id) or "")
                for part in meta.split():
                    if part.startswith("WorkDir="):
                        workdir = part.split("=", 1)[1]
                        break
                if not workdir:
                    for part in meta.split():
                        if part.startswith("StdOut="):
                            p = part.split("=", 1)[1]
                            workdir = str(PurePosixPath(p).parent) if p else ""
                            break
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
        "read_output": read_output,
        "read_remote_path": read_remote_path,
        "stat_remote_path": stat_remote_path,
        "list_job_files": list_job_files,
        "cancel": _cancel,
        "final_state": _final_state,
        "refresh_sacct": _refresh_sacct,
        "show_job_details": _show_job_details,
        "has_status_capability": _has_status_capability,
        "refresh_lssrv": _refresh_lssrv,
        "output_channel_defs": None,
        "output_channel_defs_provider": _resolve_output_defs,
        "open_main_files": open_main_files,
        "provider_filters": lambda: (_resolve_provider_config().get("file_filters", ()) if isinstance(_resolve_provider_config().get("file_filters", ()), (list, tuple)) else ()),
        "remote_files_callbacks": _remote_files_callbacks(session_state, parent, lifecycle),
        "generation": lambda: session_state.get("generation", 0),
        "lifecycle": lifecycle,
        "session_state": session_state,
    }
