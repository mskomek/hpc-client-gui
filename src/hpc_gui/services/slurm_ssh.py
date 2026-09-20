from __future__ import annotations

import posixpath
import shlex
from dataclasses import dataclass
from typing import Any

from .slurm_base import SlurmBackend
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.ssh.client import SSHClientWrapper


@dataclass(frozen=True)
class SlurmCommandResult:
    """Outcome of one scheduler command, with the failure still attached.

    The legacy string API collapses ``(code, stdout, stderr)`` into one blob,
    so a caller could not tell "here are your jobs" from "the controller is
    unreachable" — a failed command was reported as a successful result. This
    keeps the exact legacy text in :attr:`text` while preserving the exit
    status next to it.
    """

    code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def text(self) -> str:
        """The legacy single-string rendering.

        Successful commands with empty output render as ``""`` (there is
        nothing to show for an empty queue), while failures keep the exact
        legacy fallback so an error is never mistaken for empty data.
        """
        if self.stdout.strip():
            return self.stdout
        if self.ok:
            return ""
        return self.stderr or f"[exit={self.code}]"

    @property
    def message(self) -> str:
        """Best human-readable explanation of a failure."""
        return self.stderr.strip() or self.stdout.strip() or f"command failed [exit={self.code}]"


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

    def _run(self, key: str, **values: str) -> SlurmCommandResult:
        """Run a templated scheduler command and keep its exit status."""
        cmd = self._command(key, **values)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return SlurmCommandResult(code=code, stdout=out, stderr=err)

    def squeue_result(self, user: str) -> SlurmCommandResult:
        return self._run("squeue_command", user=user)

    def sbatch_result(self, script_path: str) -> SlurmCommandResult:
        return self._run(
            "sbatch_command",
            script_dir=posixpath.dirname(script_path) or ".",
            script_name=posixpath.basename(script_path),
        )

    def scancel_result(self, job_id: str) -> SlurmCommandResult:
        return self._run("scancel_command", job_id=job_id)

    def sacct_result(self, user: str) -> SlurmCommandResult:
        return self._run("sacct_command", user=user)

    def scontrol_show_job_result(self, job_id: str) -> SlurmCommandResult:
        return self._run("scontrol_command", job_id=job_id)

    def squeue(self, user: str) -> str:
        return self.squeue_result(user).text

    def sbatch(self, script_path: str) -> str:
        return self.sbatch_result(script_path).text

    def scancel(self, job_id: str) -> str:
        result = self.scancel_result(job_id)
        return result.stdout.strip() or (
            "OK" if result.ok else (result.stderr or f"[exit={result.code}]")
        )

    def sacct(self, user: str) -> str:
        return self.sacct_result(user).text

    def sacct_job(self, job_id: str) -> str:
        """Query accounting for a specific job ID using stable pipe format."""
        cmd = self._command("sacct_job_command", job_id=job_id)
        code, out, err = self.ssh.run(cmd, log_output=False)
        return out if out.strip() else (err or f"[exit={code}]")

    def scontrol_show_job(self, job_id: str) -> str:
        return self.scontrol_show_job_result(job_id).text

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
