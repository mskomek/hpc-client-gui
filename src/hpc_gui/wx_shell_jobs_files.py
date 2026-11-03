"""Remote file and output readers for the Jobs shell."""

from __future__ import annotations


def make_file_callbacks(context):
    def read_output(job_id):
        slurm = context.resolve_slurm()
        files = context.resolve_files()
        if not slurm or not files:
            return {}
        scontrol_error = None
        try:
            details = context.scontrol_details(slurm, job_id)
            stdout_path, stderr_path = details.stdout_path, details.stderr_path
        except Exception as exc:
            scontrol_error = exc
            stdout_path = stderr_path = ""
        if not stdout_path and not stderr_path:
            cached = context.cached_history_job(job_id) or context.query_sacct_job(job_id)
            stdout_path = str((cached or {}).get("stdout_path", ""))
            stderr_path = str((cached or {}).get("stderr_path", ""))
            if not stdout_path and not stderr_path and scontrol_error is not None:
                raise scontrol_error
        return {
            "stdout": files.read_text(stdout_path) if stdout_path else "",
            "stderr": files.read_text(stderr_path) if stderr_path else "",
        }

    def read_remote_path(path):
        files = context.resolve_files()
        if not files or not path:
            raise FileNotFoundError(path)
        return files.read_text(path)

    def stat_remote_path(path):
        files = context.resolve_files()
        if not files or not path:
            raise FileNotFoundError(path)
        return files.stat(path)

    def list_job_files(job_id, workdir=""):
        test_files = context.state.get("_test_job_files")
        if test_files is not None:
            if isinstance(test_files, dict):
                return tuple(test_files.get(str(job_id), ()))
            return tuple(test_files)
        slurm = context.resolve_slurm()
        files = context.resolve_files()
        if not slurm or not files or not hasattr(files, "iterdir_entries"):
            return ()
        try:
            if not workdir:
                try:
                    details = context.scontrol_details(slurm, job_id)
                except Exception:
                    details = None
                if details is not None:
                    from hpc_gui.services.job_paths import resolve_job_directory
                    workdir = resolve_job_directory({
                        "workdir": details.workdir, "stdout_path": details.stdout_path,
                        "stderr_path": details.stderr_path,
                    }).path
            if not workdir:
                from hpc_gui.services.job_paths import resolve_job_directory
                cached = context.cached_history_job(job_id) or context.query_sacct_job(job_id)
                workdir = resolve_job_directory(cached or {}).path
            if not workdir:
                return ()
            return tuple(files.iterdir_entries(workdir))
        except Exception:
            return ()

    return {
        "read_output": read_output,
        "read_remote_path": read_remote_path,
        "stat_remote_path": stat_remote_path,
        "list_job_files": list_job_files,
    }
