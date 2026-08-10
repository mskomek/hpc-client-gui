from __future__ import annotations

import json
from typing import Any

from truba_gui.services.slurm_ssh import SSHSlurmBackend


def jobs_backend(session, system_settings: dict[str, Any] | None = None) -> SSHSlurmBackend:
    return SSHSlurmBackend(session.ssh, system_settings=system_settings)


def emit_job_result(result: str, *, output_format: str, quiet: bool = False) -> int:
    if quiet:
        return 0
    if output_format == "json":
        print(json.dumps({"result": result}, ensure_ascii=False, indent=2))
        return 0
    print(result)
    return 0
