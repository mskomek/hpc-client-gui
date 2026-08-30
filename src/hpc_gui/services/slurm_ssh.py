from __future__ import annotations

import posixpath
import shlex
from typing import Any

from .slurm_base import SlurmBackend
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.ssh.client import SSHClientWrapper


class SSHSlurmBackend(SlurmBackend):
    def __init__(
        self,
        ssh: SSHClientWrapper,
        system_settings: dict[str, Any] | None = None,
    ):
        self.ssh = ssh
        self.system_settings = normalize_system_settings(system_settings)

    def _command(self, key: str, **values: str) -> str:
        template = self.system_settings[key]
        quoted = {name: shlex.quote(str(value)) for name, value in values.items()}
        quoted.update({f"{name}_q": value for name, value in quoted.items()})
        return template.format(**quoted)

    def squeue(self, user: str) -> str:
        cmd = self._command("squeue_command", user=user)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if out.strip() else (err or f"[exit={code}]")

    def sbatch(self, script_path: str) -> str:
        script_dir = posixpath.dirname(script_path) or "."
        script_name = posixpath.basename(script_path)
        cmd = self._command(
            "sbatch_command",
            script_dir=script_dir,
            script_name=script_name,
        )
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if out.strip() else (err or f"[exit={code}]")

    def scancel(self, job_id: str) -> str:
        cmd = self._command("scancel_command", job_id=job_id)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out.strip() or (
            "OK" if code == 0 else (err or f"[exit={code}]")
        )

    def sacct(self, user: str) -> str:
        cmd = self._command("sacct_command", user=user)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if out.strip() else (err or f"[exit={code}]")

    def scontrol_show_job(self, job_id: str) -> str:
        cmd = self._command("scontrol_command", job_id=job_id)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if out.strip() else (err or f"[exit={code}]")

    def lssrv(self) -> str:
        status_command = self.system_settings.get("status_command", "").strip()
        if not status_command:
            raise RuntimeError(
                "No site status command is configured for this system template."
            )
        if status_command != "lssrv":
            raise RuntimeError(
                "The configured legacy site status command is not an allowlisted adapter."
            )
        code, out, err = self.ssh.run(
            status_command,
            log_output=False,
        )
        if code != 0:
            raise RuntimeError(
                err.strip() or out.strip() or f"lssrv failed [exit={code}]"
            )
        return out

    def active_job_ids(self, user: str) -> str:
        cmd = self._command("active_job_ids_command", user=user)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if code == 0 else (err or out)

    def job_state(self, job_id: str) -> str:
        cmd = self._command("job_state_command", job_id=job_id)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if code == 0 else (err or out)
