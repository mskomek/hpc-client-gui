"""Host-owned Slurm job-draft validation and rendering for Case Studio.

Draft-only: builds a reviewable wrapper around an application-generated
Allrun. The wrapper references the Allrun by its SHA-256 and never carries
an interpolated shell body. Nothing here submits work.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from hpc_gui.openfoam_core.release_support import OPENFOAM_EDITION, release_profile


_JOB_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_PARTITION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_MODULE_RE = re.compile(r"[A-Za-z0-9_.+-]+(?:/[A-Za-z0-9_.+-]+)*\Z")
_TIME_RE = re.compile(
    r"(?:(?P<days>[0-9]{1,3})-)?(?P<hours>[0-9]{1,3}):"
    r"(?P<minutes>[0-5][0-9]):(?P<seconds>[0-5][0-9])\Z"
)

DEFAULT_MODULE = "apps/openfoam/v2312-2025"
MAX_WORKFLOW_STEPS = 128
DEFAULT_JOB_NAME = "openfoam-case"
DEFAULT_TIME = "01:00:00"


@dataclass(frozen=True)
class JobSpec:
    job_name: str = DEFAULT_JOB_NAME
    nodes: int = 1
    ntasks: int = 1
    time: str = DEFAULT_TIME
    partition: str = ""
    module: str = DEFAULT_MODULE


@dataclass(frozen=True)
class DraftBundle:
    solver: str
    allrun_text: str
    allrun_sha256: str
    slurm_text: str
    spec: JobSpec


def validate_job_spec(
    job_name: str = DEFAULT_JOB_NAME,
    nodes: int = 1,
    ntasks: int = 1,
    time: str = DEFAULT_TIME,
    partition: str = "",
    module: str = DEFAULT_MODULE,
) -> JobSpec:
    """Validate scheduler inputs; raises ValueError on any violation."""
    if not isinstance(job_name, str) or not _JOB_NAME_RE.fullmatch(job_name):
        raise ValueError("job name must be 1-128 safe ASCII letters, digits, dots, underscores, or hyphens")
    if type(nodes) is not int or type(ntasks) is not int or nodes < 1 or ntasks < 1:
        raise ValueError("scheduler nodes/ntasks must be integers >= 1")
    if not isinstance(time, str):
        raise ValueError("scheduler time must be text in HH:MM:SS or D-HH:MM:SS form")
    match = _TIME_RE.fullmatch(time)
    if not match or (match.group("days") and int(match.group("hours")) > 23):
        raise ValueError("scheduler time must be a valid HH:MM:SS or D-HH:MM:SS value")
    if not isinstance(partition, str):
        raise ValueError("scheduler partition must be text")
    if partition and not _PARTITION_RE.fullmatch(partition):
        raise ValueError("scheduler partition contains unsafe characters")
    if not isinstance(module, str) or not _MODULE_RE.fullmatch(module):
        raise ValueError("module must be a safe slash-separated module name")
    if any(part in (".", "..") for part in module.split("/")):
        raise ValueError("module path segments cannot be '.' or '..'")
    return JobSpec(job_name=job_name, nodes=nodes, ntasks=ntasks, time=time, partition=partition, module=module)


def require_release_catalog(catalog: dict) -> dict:
    """Require a catalog with a matching host-owned OpenFOAM release profile."""
    if not isinstance(catalog, dict):
        raise ValueError("case catalog is unavailable")
    if catalog.get("product") != OPENFOAM_EDITION:
        raise ValueError("case catalog is not an OpenFOAM.com / ESI catalog")
    profile = release_profile(catalog.get("version"))
    commands = catalog.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("case catalog has no command list")
    return profile


def require_catalog_v2312(catalog: dict) -> None:
    """Compatibility guard for callers that explicitly require the TRUBA target."""
    profile = require_release_catalog(catalog)
    if profile["source_tag"] != "OpenFOAM-v2312":
        raise ValueError("case catalog does not match OpenFOAM.com v2312")


def decompose_subdomains(documents: dict) -> int | None:
    """Return numberOfSubdomains when a decomposeParDict is loaded, else None."""
    document = (documents or {}).get("system/decomposeParDict")
    if document is None:
        return None
    try:
        raw = document.parsed.value("numberOfSubdomains", ())
    except Exception:
        raise ValueError("decomposeParDict numberOfSubdomains is not readable")
    if raw is None:
        raise ValueError("decomposeParDict is missing numberOfSubdomains")
    text = str(raw).strip().strip("\"'")
    if not re.fullmatch(r"[1-9][0-9]*", text):
        raise ValueError("decomposeParDict numberOfSubdomains must be a positive integer")
    return int(text)


def check_parallel_consistency(documents: dict, ntasks: int) -> None:
    """Require decompose ranks to match scheduler tasks; block unsafe drafts."""
    if type(ntasks) is not int or ntasks < 1:
        raise ValueError("scheduler ntasks must be an integer >= 1")
    count = decompose_subdomains(documents or {})
    if count is None:
        if ntasks > 1:
            raise ValueError("parallel draft needs system/decomposeParDict with matching numberOfSubdomains")
        return
    if count != ntasks:
        raise ValueError(f"rank mismatch: decompose {count} != scheduler ntasks {ntasks}")


def render_slurm_wrapper(spec: JobSpec, *, allrun_sha256: str) -> str:
    """Render the reviewable wrapper; references Allrun only by digest."""
    if not isinstance(spec, JobSpec):
        raise TypeError("spec must be a validated JobSpec")
    spec = validate_job_spec(
        job_name=spec.job_name, nodes=spec.nodes, ntasks=spec.ntasks,
        time=spec.time, partition=spec.partition, module=spec.module,
    )
    if not isinstance(allrun_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", allrun_sha256):
        raise ValueError("Allrun SHA-256 must be 64 lowercase hexadecimal characters")
    header = [
        "#!/bin/bash",
        f"#SBATCH --job-name={spec.job_name}",
        f"#SBATCH --nodes={spec.nodes}",
        f"#SBATCH --ntasks={spec.ntasks}",
        f"#SBATCH --time={spec.time}",
    ]
    if spec.partition:
        header.append(f"#SBATCH --partition={spec.partition}")
    guard = [
        "# DRAFT ONLY - review before submitting; nothing is submitted by the studio",
        "set -eo pipefail",
        "if ! command -v module >/dev/null 2>&1 && [[ -r /etc/profile.d/modules.sh ]]; then",
        "  source /etc/profile.d/modules.sh",
        "fi",
        "if ! command -v module >/dev/null 2>&1; then",
        '  echo \"Environment Modules is unavailable.\" >&2',
        "  exit 127",
        "fi",
        f"module load {spec.module}",
        "set -u",
        f"expected_allrun_sha256={allrun_sha256}",
        'if [ ! -f ./Allrun ] || [ -L ./Allrun ]; then',
        '  echo "Refusing missing or symlinked Allrun" >&2; exit 1',
        "fi",
        'printf \'%s  %s\\n\' "$expected_allrun_sha256" ./Allrun | sha256sum --check --status || {',
        '  echo "Allrun does not match the reviewed workflow draft" >&2; exit 1',
        "}",
        "exec bash -- ./Allrun",
    ]
    return "\n".join(header + guard) + "\n"


def _solver_for(documents: dict) -> str:
    control = (documents or {}).get("system/controlDict")
    solver = control.parsed.value("application") if control is not None else None
    return str(solver or "").strip().strip("\"'")


def build_draft_bundle(documents: dict, catalog: dict, steps, spec: JobSpec) -> DraftBundle:
    """Render Allrun plus its wrapper from validated inputs only."""
    from .run_script import render_allrun

    if not isinstance(documents, dict) or not documents:
        raise ValueError("no case is open")
    profile = require_release_catalog(catalog)
    if not profile["truba_module"]:
        raise ValueError(
            f"Slurm job draft is disabled for {catalog['version']}: no TRUBA module is verified"
        )
    if not isinstance(spec, JobSpec):
        raise TypeError("spec must be a validated JobSpec")
    if not isinstance(steps, (tuple, list)) or len(steps) > MAX_WORKFLOW_STEPS:
        raise ValueError(f"workflow must be a sequence of at most {MAX_WORKFLOW_STEPS} approved commands")
    spec = validate_job_spec(
        job_name=spec.job_name, nodes=spec.nodes, ntasks=spec.ntasks,
        time=spec.time, partition=spec.partition, module=spec.module,
    )
    if spec.module != profile["truba_module"]:
        raise ValueError(
            f"Slurm draft module is not verified for {catalog['version']}: {spec.module}"
        )
    check_parallel_consistency(documents, spec.ntasks)
    solver = _solver_for(documents)
    allrun_text = render_allrun(solver, tuple(steps), catalog["commands"])
    digest = hashlib.sha256(allrun_text.encode("utf-8")).hexdigest()
    slurm_text = render_slurm_wrapper(spec, allrun_sha256=digest)
    return DraftBundle(solver=solver, allrun_text=allrun_text, allrun_sha256=digest, slurm_text=slurm_text, spec=spec)
