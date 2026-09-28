"""Framework-neutral job submit/cancel control paths for W30.

Owns HPC-W07-CTRL-001..010 (Workstream F Submission + Workstream G
Cancellation):

- CTRL-001: validate required fields before sending; success requires a
  confirmed scheduler acceptance/job ID (or equivalent provider result).
- CTRL-002: template partition/account/directive rules are capability/config
  driven, never hardcoded.
- CTRL-003..006: before cancel — selected job identity, cluster/profile
  scope, confirmation wording, capability availability.
- CTRL-007..010: after cancel — reflect command result, refresh, tolerate
  already-ended races, distinguish already-gone from unauthorized/error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


_SBATCH_JOB_ID_RE = re.compile(r"Submitted\s+batch\s+job\s+(\d+)", re.IGNORECASE)

# Slurm/scancel already-gone signals: the job left the queue between listing
# and cancel (completed/cancelled/unknown). These are benign races, not
# authorization failures.
_ALREADY_GONE_PATTERNS = (
    "invalid job id",
    "unknown job",
    "unknownjob",
    "job not found",
    "no such job",
    "already",
    "already completed",
    "already finished",
    "already ended",
    "already cancelled",
    "already canceled",
    "job has finished",
    "job has completed",
    "completed",
    "not found",
)

_UNAUTHORIZED_PATTERNS = (
    "permission denied",
    "not authorized",
    "unauthorized",
    "access denied",
    "permission",
    "assocmax",
    "association",
    "account",
    "qos",
)

_PLACEHOLDER_TOKENS = ("USERNAME", "<partition>", "<account>", "<qos>", "{{", "}}", "TODO", "FIXME")


def extract_sbatch_job_id(output: str) -> str:
    """Return the scheduler job ID from sbatch output, or "" when absent.

    Success is never inferred from free-form text: only the canonical
    ``Submitted batch job <id>`` acceptance token counts.
    """
    match = _SBATCH_JOB_ID_RE.search(str(output or ""))
    return match.group(1) if match else ""


def submit_result_status(output: str, *, ok: bool | None = None) -> tuple[str, str]:
    """Classify an sbatch result as (status, job_id_or_reason).

    ``SUCCESS`` requires a confirmed job ID. Any output without one —
    including a zero-exit blob with no acceptance token — is ``FAILURE`` so
    the caller never marks submission successful without scheduler
    acceptance (CTRL-001).
    """
    job_id = extract_sbatch_job_id(output)
    if job_id:
        return ("SUCCESS", job_id)
    # When the backend exposes an explicit exit flag, a non-OK result without
    # a job ID is always failure; an OK result without a job ID is still
    # failure (no confirmed acceptance).
    detail = str(output or "").strip()
    reason = detail if detail else "sbatch returned no job ID"
    if ok is False:
        reason = detail if detail else "sbatch command failed"
    return ("FAILURE", reason)


def validate_submit_request(
    script_path: str,
    script_text: str | None = None,
    *,
    provider_config: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate required submit fields before sending (CTRL-001/002).

    Returns a list of human-readable blocking errors (empty means valid).
    Checks are capability/config driven: template rules consult
    ``provider_config`` instead of hardcoded partition/account names.
    """
    errors: list[str] = []
    path = str(script_path or "").strip()
    if not path:
        errors.append("script path is required")
        return errors
    if script_text is None:
        return errors
    text = str(script_text or "")
    if not text.strip():
        errors.append("script content is empty")
        return errors
    for token in _PLACEHOLDER_TOKENS:
        if token in text:
            errors.append(f"template placeholder detected: {token}")
            break
    # CTRL-001/002: no hardcoded script-shape rule. Directive content is not a
    # required field here — the scheduler owns directive validity, provider
    # config owns partition/account rules, and success still requires a
    # confirmed job ID (submit_result_status).
    errors.extend(validate_template_against_provider(text, provider_config))
    return errors


def _provider_list(config: Mapping[str, Any] | None, *keys: str) -> list[str] | None:
    if not isinstance(config, Mapping):
        return None
    for key in keys:
        value = config.get(key)
        if isinstance(value, (list, tuple)):
            items = [str(v).strip() for v in value if str(v).strip()]
            if items:
                return items
            return []
    return None


def _provider_flag(config: Mapping[str, Any] | None, *keys: str) -> bool:
    if not isinstance(config, Mapping):
        return False
    requirements = config.get("requirements")
    if isinstance(requirements, Mapping):
        for key in keys:
            if key in requirements:
                return True
    for key in keys:
        value = config.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"required", "true", "yes"}:
            return True
    return False


def validate_template_against_provider(
    script_text: str,
    provider_config: Mapping[str, Any] | None,
) -> list[str]:
    """Validate partition/account/directive rules from provider config.

    When the provider declares allowed partitions/accounts (via
    ``allowed_partitions``/``partitions`` or ``allowed_accounts``/``accounts``)
    the script directive must belong to that set. When it declares an account
    or project requirement (``requirements`` containing ``account``/``project``
    or ``require_account``), the script must carry an ``-A/--account`` value.
    Undeclared dimensions impose no constraint — absence of config never
    blocks submission (CTRL-002).
    """
    from hpc_gui.services.slurm_directives import SlurmDirectives

    errors: list[str] = []
    if not isinstance(provider_config, Mapping):
        return errors
    directives = SlurmDirectives(str(script_text or ""))
    try:
        partition = (directives.get("partition") or "").strip()
    except Exception:
        partition = ""
    try:
        account = (directives.get("account") or "").strip()
    except Exception:
        account = ""
    allowed_partitions = _provider_list(provider_config, "allowed_partitions", "partitions")
    if allowed_partitions is not None and partition and partition not in allowed_partitions:
        errors.append(
            f"partition '{partition}' is not in provider allowed partitions: "
            + ", ".join(allowed_partitions)
        )
    allowed_accounts = _provider_list(provider_config, "allowed_accounts", "accounts")
    if allowed_accounts is not None and account and account not in allowed_accounts:
        errors.append(
            f"account '{account}' is not in provider allowed accounts: "
            + ", ".join(allowed_accounts)
        )
    if _provider_flag(provider_config, "account", "project", "require_account", "require_project"):
        if not account:
            errors.append("provider requires an account/project directive (#SBATCH -A/--account)")
    return errors


def cancel_capability_available(slurm_backend: Any) -> bool:
    """True when the backend can cancel (CTRL-006 capability availability)."""
    if slurm_backend is None:
        return False
    cancel = getattr(slurm_backend, "scancel", None)
    if callable(cancel):
        return True
    cancel_result = getattr(slurm_backend, "scancel_result", None)
    return callable(cancel_result)


def build_cancel_confirmation(job_id: str, job_name: str = "") -> str:
    """Confirmation wording that names the exact target (CTRL-005).

    The wording always carries the job ID; the job name is appended only when
    present so the operator can spot a drifted selection before confirming.
    """
    target = str(job_id or "").strip()
    name = str(job_name or "").strip()
    if name:
        return f"Cancel job {target} ({name})?"
    return f"Cancel job {target}?"


def _normalise(text: str) -> str:
    return str(text or "").strip().lower()


def is_already_gone_message(text: str) -> bool:
    """True when scheduler text means the job already left the queue."""
    needle = _normalise(text)
    if not needle:
        return False
    return any(token in needle for token in _ALREADY_GONE_PATTERNS)


def is_unauthorized_message(text: str) -> bool:
    """True when scheduler text means auth/policy refusal (not a race)."""
    needle = _normalise(text)
    if not needle:
        return False
    # Already-gone takes precedence: a completed-job notice that mentions an
    # account string must not be misread as unauthorized (CTRL-010).
    if is_already_gone_message(text):
        # Only yield to already-gone when the gone signal is explicit; a bare
        # "completed" plus an auth token is still ambiguous, so require the
        # gone token to win only for the canonical race phrases.
        race_tokens = (
            "invalid job id", "unknown job", "already", "job has finished",
            "job has completed", "not found", "no such job",
        )
        if any(token in needle for token in race_tokens):
            return False
    return any(token in needle for token in _UNAUTHORIZED_PATTERNS)


def classify_cancel_outcome(
    error: BaseException | None,
    output_text: str = "",
    *,
    final_state: str = "",
) -> str:
    """Classify a cancel attempt (CTRL-009/010).

    Returns one of ``CANCELLED`` (command accepted), ``ALREADY_GONE`` (benign
    race — the job ended before scancel arrived), or ``ERROR`` (including
    unauthorized/policy refusals, which are never conflated with a race).
    ``final_state`` is the optional post-cancel scheduler state used to
    confirm the race when the backend reports a terminal state.
    """
    from hpc_gui.services.slurm_models import TERMINAL_STATES

    if error is None:
        text = str(output_text or "")
        # Explicit failure text on a nominally-OK path still classifies.
        if text and is_already_gone_message(text):
            return "ALREADY_GONE"
        if text and is_unauthorized_message(text):
            return "ERROR"
        return "CANCELLED"
    message = f"{error} {output_text or ''}"
    if is_already_gone_message(message):
        return "ALREADY_GONE"
    if is_unauthorized_message(message):
        return "ERROR"
    state = str(final_state or "").strip().upper()
    if state and state in TERMINAL_STATES:
        return "ALREADY_GONE"
    return "ERROR"


@dataclass(frozen=True)
class CancelReflection:
    """How the UI should reflect a cancel attempt (CTRL-007/008)."""

    outcome: str
    message: str
    should_refresh: bool
    is_error: bool


def reflect_cancel_result(
    error: BaseException | None,
    output_text: str = "",
    *,
    job_id: str = "",
    final_state: str = "",
) -> CancelReflection:
    """Build the visible cancel reflection for the UI layer."""
    outcome = classify_cancel_outcome(error, output_text, final_state=final_state)
    target = str(job_id or "").strip() or "job"
    if outcome == "CANCELLED":
        return CancelReflection(
            outcome=outcome,
            message=f"Cancel accepted for {target}.",
            should_refresh=True,
            is_error=False,
        )
    if outcome == "ALREADY_GONE":
        return CancelReflection(
            outcome=outcome,
            message=f"{target} already ended; nothing to cancel.",
            should_refresh=True,
            is_error=False,
        )
    detail = str(output_text or (str(error) if error else "")).strip() or "cancel failed"
    return CancelReflection(
        outcome="ERROR",
        message=f"Cancel failed for {target}: {detail}",
        should_refresh=False,
        is_error=True,
    )
