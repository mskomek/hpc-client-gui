from __future__ import annotations

from hpc_gui.services.slurm_script_parser import parse_output_error, resolve_path
from hpc_gui.services.command_history_store import is_sensitive_command
from hpc_gui.core.diagnostics import create_diagnostic_bundle
from pathlib import Path


def main() -> int:
    script = """#!/bin/bash
#SBATCH --output=logs/out_%j.txt
#SBATCH --error=logs/err_%j.txt
echo hello
"""
    out, err = parse_output_error(script)
    assert out == "logs/out_%j.txt"
    assert err == "logs/err_%j.txt"
    assert resolve_path("/arf/home/u/job.sbatch", out, job_id="1234").endswith("/logs/out_1234.txt")
    assert is_sensitive_command("curl -H 'Authorization: Bearer abc'")
    smoke_dir = Path(__file__).resolve().parents[1] / "build" / "ci-smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    bundle = create_diagnostic_bundle(str(smoke_dir))
    bundle.unlink(missing_ok=True)
    print("smoke test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
