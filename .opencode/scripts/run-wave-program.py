from __future__ import annotations


import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
AC_MAX_TRANSPORT_ATTEMPTS = 5
AC_MAX_IDENTICAL_RECOVERY = 3
# Provider quota waits are external, not recovery attempts. Bounded total wait;
# override with AC_MAX_PROVIDER_WAIT_SECONDS to match the provider's reset window.
AC_MAX_PROVIDER_WAIT_SECONDS = int(os.environ.get("AC_MAX_PROVIDER_WAIT_SECONDS", str(6 * 3600)))
PROVIDER_QUOTA_MARKER = "AC_WAVE_PROVIDER_QUOTA:"


def provider_wait_delay(attempt: int) -> int:
    """60s, 120s, 240s ... capped at 15 minutes."""
    return min(900, 60 * 2 ** max(0, attempt))


from wave_state_engine import (
    ControllerLock, aggregate_validation_required, configure_temp_environment,
    current_target as engine_current_target, discover_unfinished_run,
    ensure_lifecycle_integrity, ensure_temp_layout, load_profile, no_progress_key, pending_targets as engine_pending_targets,
    reconcile_active_wave_tracker as engine_reconcile_active_wave_tracker,
    reconcile_waves_index as engine_reconcile_waves_index,
    program_run_root, repo_identity, repository_content_identity, resume_classification,
    load_progress_ledger, record_progress_attempt, clear_progress_entry,
    semantic_finding_key, wave_location as engine_wave_location, wave_metadata,
    wave_targets_in_folder as engine_wave_targets_in_folder, legacy_program_roots,
    parse_wave_id as engine_parse_wave_id, wave_sort_key as engine_wave_sort_key,
    wave_channel_of as engine_wave_channel_of, wave_number_of as engine_wave_number_of,
    group_members as engine_group_members, wave_title_of as engine_wave_title_of,
    progress_contract_version as engine_progress_contract_version,
    normalize_progress_profile as engine_normalize_progress_profile,
    managed_job_lease as engine_managed_job_lease, live_controller_locks as engine_live_controller_locks,
    controller_owned_surfaces as engine_controller_owned_surfaces, reserved_surface_hits as engine_reserved_surface_hits,
    git_capability as engine_git_capability, subprocess_no_window_kwargs,
)
from phase_job import (
    job_matches, mark_result as mark_phase_job_result, process_start_marker, read_job as read_phase_job,
    start_job as start_phase_job, wait_job as wait_phase_job, poll_job as poll_phase_job,
    poll_jobs as poll_phase_jobs, join_jobs as join_phase_jobs, read_job_delta as read_phase_job_delta,
    job_is_alive as phase_job_is_alive, channel_job_matches as phase_channel_job_matches,
    job_liveness as phase_job_liveness, job_identity_mismatches as phase_job_identity_mismatches,
    write_job as write_phase_job, terminate_job_tree as terminate_phase_job_tree,
    kill_process_tree, terminate_process_tree, survivors_alive,
)
import wave_progress as progress_engine
import parallel_workspace as workspace_engine


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


# Machine-result authority is strictly block-scoped. Whole-output
# WAVE_PHASE_STATUS counting is NOT authority: quoted reports, evidence,
# prior phase output, grep/Select-String output, WAVE_PHASE_STATUS_EVIDENCE,
# and historical markers outside the single complete block are ignored.
# Legacy whole-output regexes were removed; only MACHINE_* below is authority.
REPAIR_HYPOTHESIS_RE = re.compile(r"(?im)^\s*WAVE_REPAIR_HYPOTHESIS:\s*([A-Za-z0-9][A-Za-z0-9._:-]{0,127})\s*$")

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

MACHINE_BLOCK_RE = re.compile(r"(?ms)^\s*AC_WAVE_MACHINE_RESULT_BEGIN\s*$\r?\n(?P<body>.*?)^\s*AC_WAVE_MACHINE_RESULT_END\s*$")
MACHINE_STATUS_RE = re.compile(r"(?im)^\s*WAVE_PHASE_STATUS:\s*([A-Z_]+)\s*$")
MACHINE_HYPOTHESIS_RE = re.compile(r"(?im)^\s*WAVE_REPAIR_HYPOTHESIS:\s*([A-Za-z0-9][A-Za-z0-9._:-]{0,127})\s*$")


def _strip_ansi_for_machine(text: str) -> str:
    return ANSI_RE.sub("", text or "")


# Bounded legacy planner aliases; opencode_phase() maps them to READY.
LEGACY_STATUS_ALIASES = {"PLANNED": "READY", "PLAN_COMPLETE": "READY", "READY_FOR_RUN": "READY"}


BRIDGE_STDOUT_SENTINEL = "AC_WAVE_BRIDGE_STDOUT_BEGIN"


def bridge_authoritative_output(output: str) -> str:
    """The job log merges the worker transcript (stderr, may quote old machine
    blocks) with the bridge-validated stdout. Only text after the bridge's last
    sentinel is machine authority; logs from older bridges are used whole."""
    text = output or ""
    positions = [m.end() for m in re.finditer(rf"(?m)^\s*{BRIDGE_STDOUT_SENTINEL}\s*$", text)]
    return text[positions[-1]:] if positions else text


def parse_machine_result(output: str, phase: str) -> dict[str, str]:
    # Strip ANSI so colorized stdout still parses; only the single complete
    # machine-result block is authority. Everything outside is prose/evidence.
    clean = _strip_ansi_for_machine(output or "")
    blocks = list(MACHINE_BLOCK_RE.finditer(clean))
    if len(blocks) != 1:
        raise ValueError(f"expected exactly one complete machine-result block, found {len(blocks)}")
    body = blocks[0].group("body")
    statuses = list(MACHINE_STATUS_RE.finditer(body))
    if len(statuses) != 1:
        raise ValueError(f"expected exactly one machine-result status, found {len(statuses)}")
    hypotheses = list(MACHINE_HYPOTHESIS_RE.finditer(body))
    if phase == "repair" and len(hypotheses) != 1 and statuses[0].group(1).upper() != "ORCHESTRATION_RECOVERY_REQUIRED":
        raise ValueError(f"expected exactly one repair hypothesis, found {len(hypotheses)}")
    if phase != "repair" and hypotheses:
        raise ValueError("non-repair machine-result contains a repair hypothesis")
    result = {"status": statuses[0].group(1).upper()}
    # Report/requirement dispositions (NOT_APPLICABLE_ACCEPTED, DEFERRED_CLEAN,
    # AWAITING_INPUT, IMPLEMENT, ...) are never machine status. Fail closed.
    if result["status"] not in RESULT_SCHEMA["properties"]["status"]["enum"] and result["status"] not in LEGACY_STATUS_ALIASES:
        raise ValueError(f"machine-result status outside canonical schema: {result['status']}")
    if hypotheses:
        result["repair_hypothesis"] = hypotheses[0].group(1)
    return result
LIFECYCLE_RE = re.compile(
    r"(?im)^\s*(WAVE_PHASE_STATUS|WAVE_REPAIR_STATUS):\s*([A-Z_]+)\s*$"
)
# Only concrete authority failures may become HUMAN_DEFERRED. Product prose
# mentioning authentication/credentials is repository work, not human authority.
HUMAN_RE = re.compile(
    r"(?ix)\b(?:mfa|two[- ]factor|device\s+authorization|"
    r"401|403|unauthori[sz]ed|forbidden|not\s+logged\s+in|login\s+required|"
    r"interactive\s+(?:login|authorization)|api[_ -]?key\s+(?:missing|required|invalid)|"
    r"manual\s+acceptance|customer\s+acceptance|required\s+hardware|"
    r"authoritative\s+external\s+service)\b"
)
TRANSIENT_RE = re.compile(
    r"(?i)(timeout|timed out|connection|econn|network|transport|temporar|unavailable|overload|capacity|"
    r"queue|rate.?limit|429|5\d\d|broken pipe|epipe|gateway|dns|failed to fetch)"
)
CONFIG_RE = re.compile(r"(?i)(unknown option|unknown flag|unexpected argument|invalid option|model .*not found|parse error)")
FINDING_ID_RE = re.compile(
    r"\b(?:REOPEN-)?[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){1,}\b",
    re.I,
)
# Machine error classes that arrive as free prose. Each is reduced to a stable
# token so an unchanged outage keeps one identity across rewordings and across
# program restarts, instead of churning the no-progress fingerprint. Volatile
# detail (model/provider names, exit codes, paths, quoted text) is dropped: the
# class is what determines whether the *same* blocker is being retried.
FINDING_ERROR_CLASS_RES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\bphase[_ -]?bridge[_ -]?error\b"), "ERR:PHASE_BRIDGE"),
    (re.compile(r"(?i)\bmodel[_ -]?transport\b|\btransport[_ -]?(?:retry|exhaust)"), "ERR:MODEL_TRANSPORT"),
    (re.compile(r"(?i)\b(?:codex|opencode|claude)[_ -]?transport\b"), "ERR:MODEL_TRANSPORT"),
    (re.compile(r"(?i)\bprovider[_ -]?quota\b|\bquota[_ -]?(?:exhaust|wait)"), "ERR:PROVIDER_QUOTA"),
    (re.compile(r"(?i)\bmanaged[_ -]?worker[_ -]?timeout\b"), "ERR:MANAGED_WORKER_TIMEOUT"),
    (re.compile(r"(?i)\bunresolved[_ -]?managed[_ -]?child\b"), "ERR:UNRESOLVED_MANAGED_CHILD"),
    (re.compile(r"(?i)\bmissing[_ -]?status\b|\bno[_ -]?machine[_ -]?result\b"), "ERR:MISSING_STATUS"),
    (re.compile(r"(?i)\borchestration[_ -]?recovery[_ -]?required\b"), "ERR:ORCHESTRATION_RECOVERY_REQUIRED"),
    (re.compile(r"(?i)\b(?:model|provider)\b.*\b(?:not\s+found|unknown|unavailable|not\s+available|"
                r"unsupported|disabled)\b|\bunknown\s+(?:model|provider)\b"), "ERR:MODEL_UNAVAILABLE"),
    (re.compile(r"(?i)\b(?:timeout|timed\s+out|connection|econn|network|temporar|unavailable|overload|"
                r"capacity|queue|rate.?limit|429|5\d\d|broken\s+pipe|epipe|gateway|dns|failed\s+to\s+fetch)\b"),
     "ERR:TRANSIENT"),
)
# Detail that varies run to run and must not take part in the identity.
FINDING_VOLATILE_RE = re.compile(
    r"(?i)(?:\b[a-z0-9][\w.-]*/[\w.-]+\b"          # provider/model paths
    r"|\b\d{2,}\b)"                                  # bare numbers: exit codes, ports, counts
)


def classify_finding_identity(text: str) -> str:
    """Stable identity for a finding that carries no machine ID.

    A recognised error class collapses to its token regardless of surrounding
    prose, so `AC_WAVE_PHASE_BRIDGE_ERROR: required model X unavailable` and
    `... required model Y is not available` are the same blocker. Unrecognised
    prose is returned with volatile detail stripped, never discarded: an
    unfamiliar finding still has a stable, content-derived identity.
    """
    value = str(text or "").strip()
    if not value:
        return ""
    for pattern, token in FINDING_ERROR_CLASS_RES:
        if pattern.search(value):
            return token
    return FINDING_VOLATILE_RE.sub(" ", value).strip()


RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "READY", "PASS", "READY_FOR_AUDIT", "REOPEN", "BLOCKED", "FAIL",
                "HUMAN_DEFERRED", "COMPLETE", "NO_PROGRESS", "MISSING_STATUS",
                "ORCHESTRATION_RECOVERY_REQUIRED"
            ],
        },
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "string"}},
        "changed_files": {"type": "array", "items": {"type": "string"}},
        # Nullable, not optional: OpenAI strict structured output (codex exec
        # --output-schema) requires every property to be listed in `required`.
        "repair_hypothesis": {"type": ["string", "null"]},
        "next_action": {
            "type": "string",
            "enum": ["plan", "run", "repair", "audit", "close", "reconcile", "next_wave", "none"],
        },
    },
    "required": ["status", "summary", "findings", "changed_files", "repair_hypothesis", "next_action"],
    "additionalProperties": False,
}


# Structured PLAN TODO contract. PLAN workers emit one block:
#   AC_WAVE_TODO_PLAN_BEGIN
#   [{"id":"T01","title":"...","kind":"task","owner_phase":"run",...}, ...]
#   AC_WAVE_TODO_PLAN_END
# in validated stdout. The controller validates it before storing; worker
# output never replaces canonical state directly. The contract version is
# decided before dispatch from the project profile (progress.contract_version):
# v1 legacy workers may omit the block (controller default plan); under v2 a
# missing/malformed/invalid block is a contract violation -> recovery, never a
# silent fallback to v1.
TODO_PLAN_BEGIN_RE = re.compile(r"(?m)^\s*AC_WAVE_TODO_PLAN_BEGIN\s*$")
TODO_PLAN_END_RE = re.compile(r"(?m)^\s*AC_WAVE_TODO_PLAN_END\s*$")


def default_todo_plan_for_wave(wave_id: str) -> list[dict[str, Any]]:
    return [
        {"id": "T01", "title": "Inspect existing implementation", "kind": "task", "owner_phase": "run", "status": "pending"},
        {"id": "T02", "title": "Define trust boundary", "kind": "task", "owner_phase": "run", "status": "pending"},
        {"id": "T03", "title": "Implement change", "kind": "task", "owner_phase": "run", "status": "pending"},
        {"id": "T04", "title": "Run focused tests", "kind": "test", "owner_phase": "run", "status": "pending"},
        {"id": "T05", "title": "Run regression", "kind": "test", "owner_phase": "run", "status": "pending"},
        {"id": "T06", "title": "Update evidence", "kind": "evidence", "owner_phase": "run", "status": "pending"},
        {"id": "T07", "title": "Audit #1", "kind": "audit", "owner_phase": "audit", "status": "pending"},
        {"id": "T08", "title": "Close", "kind": "close", "owner_phase": "close", "status": "pending"},
    ]


def parse_plan_todo_block(output: str) -> list[dict[str, Any]] | None:
    """Extract a structured TODO plan from validated worker stdout, if present."""
    text = output or ""
    begins = list(TODO_PLAN_BEGIN_RE.finditer(text))
    ends = list(TODO_PLAN_END_RE.finditer(text))
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or ends[0].start() < begins[0].end():
        raise ValueError("expected exactly one AC_WAVE_TODO_PLAN block")
    payload = text[begins[0].end():ends[0].start()].strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"TODO plan block is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("TODO plan block must be a JSON list")
    return data


def evaluate_plan_todo(text: str, contract: int) -> dict[str, Any]:
    """PLAN TODO verdict under a pre-dispatch contract version.

    Returns {plan, error, violation}: `plan` is a validated list to store (or
    None), `error` explains a missing/malformed/invalid block, `violation` is
    True only under contract v2 (v1 keeps the legacy default plan).
    """
    plan, error = None, None
    try:
        parsed = parse_plan_todo_block(text)
    except ValueError as exc:
        error = f"todo-plan-malformed:{exc}"
    else:
        if parsed is None:
            error = "todo-plan-missing"
        else:
            verrs = progress_engine.validate_initial_todo_plan(parsed)
            if verrs:
                error = "todo-plan-invalid:" + ";".join(verrs[:6])
            else:
                plan = parsed
    return {"plan": plan, "error": error, "violation": error is not None and int(contract) >= 2}


# Effective contract v2 accepts a Wave's structured plan only when the controller
# has recorded the verdict. `progress_engine.validate_initial_todo_plan()` stays
# the single acceptance authority; these are its durable controller-owned values.
TODO_PLAN_PENDING = "pending"
TODO_PLAN_ACCEPTED = "accepted"
TODO_PLAN_REJECTED = "rejected"
TODO_PLAN_STATES = {TODO_PLAN_PENDING, TODO_PLAN_ACCEPTED, TODO_PLAN_REJECTED}


def store_plan_todo(run_dir: Path, entry: dict[str, Any], wave_id: str, verdict: dict[str, Any]) -> None:
    """Store a validated PLAN TODO list; a v1 bad block is recorded, never applied."""
    if verdict.get("plan"):
        # Keep the worker boundary declaration-only even if a caller supplies a
        # prebuilt verdict: all status and provenance start controller-owned.
        entry["todos"] = [progress_engine.normalize_todo_item({
            **{key: item[key] for key in ("id", "title", "kind", "owner_phase")}, "status": "pending"
        }) for item in verdict["plan"]]
        entry["todo_plan_state"] = TODO_PLAN_ACCEPTED
        # The reason described a non-accepted state; an accepted plan owns its own.
        entry.pop("todo_plan_state_reason", None)
        append_event(run_dir, {"event": "wave_todo_planned", "wave": wave_id, "count": len(verdict["plan"])})
    elif verdict.get("error") and verdict.get("error") != "todo-plan-missing":
        append_event(run_dir, {"event": "wave_todo_plan_rejected", "wave": wave_id, "error": verdict["error"],
                               "contract": entry.get("progress_contract_version"),
                               "contract_source": entry.get("progress_contract_source")})


def effective_contract_version(state: dict[str, Any] | None) -> int:
    """The pre-dispatch progress contract version the controller fixed."""
    try:
        return int((state or {}).get("progress_contract_version") or 1)
    except (TypeError, ValueError):
        return 1


def normalize_todo_plan_state(entry: dict[str, Any] | None, contract: int) -> str | None:
    """Give a pre-v2/migrated Wave entry a deterministic v2 plan state.

    A legacy entry carries the controller default plan, which was never a
    worker-declared v2 plan, so it is recorded `pending` and its items are kept
    non-destructively: only a validated PLAN block installs TODOs and it
    replaces them. Nothing is erased and nothing is marked accepted. Under v1
    legacy the field is never invented, so the default plan behaves exactly as
    before. Returns the recorded state, or None when the entry already had one.
    """
    if not isinstance(entry, dict) or int(contract) < 2:
        return None
    current = str(entry.get("todo_plan_state") or "").strip().lower()
    if current in TODO_PLAN_STATES:
        return None
    entry["todo_plan_state"] = TODO_PLAN_PENDING
    entry.setdefault("progress_contract_version", int(contract))
    return TODO_PLAN_PENDING


def v2_plan_gate_violation(state: dict[str, Any] | None, entry: dict[str, Any] | None, phase: str) -> str | None:
    """The recorded non-accepted plan state when RUN/REPAIR may not start, else None.

    Effective contract v2 fails closed: only an accepted structured PLAN may
    precede RUN/REPAIR, so `pending` and `rejected` both force PLAN first. v1
    legacy keeps the controller default plan and never fires the gate.
    """
    if str(phase or "").lower() not in {"run", "repair"}:
        return None
    if effective_contract_version(state) < 2:
        return None
    recorded = str((entry or {}).get("todo_plan_state") or "").strip().lower()
    return None if recorded == TODO_PLAN_ACCEPTED else (recorded or TODO_PLAN_PENDING)


def plan_output_text(repo: Path, result: dict[str, Any]) -> str:
    log_rel = str(result.get("phase_log_path") or "")
    if not log_rel:
        return ""
    try:
        return bridge_authoritative_output((repo / log_rel).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def ensure_wave_entry(state: dict[str, Any], wave_id: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Controller-owned per-Wave progress entry. Creates a legacy-compatible entry when missing."""
    waves = state.setdefault("waves", {})
    key = str(wave_id)
    entry = waves.get(key)
    title = None
    if isinstance(meta, dict) and str(meta.get("wave_title") or "").strip():
        title = str(meta.get("wave_title")).strip()
    contract = effective_contract_version(state)
    if isinstance(entry, dict) and entry.get("todos") is not None:
        if title and not str(entry.get("wave_title") or "").strip():
            entry["wave_title"] = title
        entry.setdefault("execution_state", "active")
        # A pre-v2/migrated entry records no plan verdict. Normalize it to
        # `pending` so the PLAN gate reads it as unaccepted instead of letting
        # the legacy default plan pass as a usable structured plan.
        if normalize_todo_plan_state(entry, contract):
            entry["current_action"] = f"Planning {key}: awaiting structured TODO plan"
        return entry
    number, channel = engine_parse_wave_id(key)
    if contract >= 2:
        # v2: no speculative TODOs; only a validated PLAN block installs them.
        entry = progress_engine.initialize_wave_progress(key, number, channel, [], allow_empty=True)
        entry["todo_plan_state"] = TODO_PLAN_PENDING
        entry["current_action"] = f"Planning {key}: awaiting structured TODO plan"
    else:
        # v1 legacy: controller default plan (workers may omit a TODO block).
        entry = progress_engine.initialize_wave_progress(key, number, channel, default_todo_plan_for_wave(key))
    entry["progress_contract_version"] = contract
    if state.get("progress_contract_source"):
        entry["progress_contract_source"] = str(state["progress_contract_source"])
    entry["execution_state"] = "active"
    if title:
        entry["wave_title"] = title
    waves[key] = entry
    return entry


def new_phase_instance_id(run_id: str, dispatch_seq: int, wave_id: str, phase: str) -> str:
    """Every semantic worker dispatch gets a fresh identity; reattach keeps it."""
    return f"{run_id}:{int(dispatch_seq)}:{wave_id}:{phase}"


def drain_progress_deltas(
    entry: dict[str, Any],
    delta_text: str,
    *,
    run_dir: Path | None = None,
    expected_phase: str | None = None,
    expected_phase_instance_id: str | None = None,
) -> dict[str, Any]:
    """Validate and apply AC_WAVE_PROGRESS_EVENT lines found in new log output.

    Expected wave/phase/instance always come from controller-authoritative
    state/dispatch context — never from the event payload itself.
    Returns {applied, rejected}. Rejected events never mutate state.
    """
    applied: list[str] = []
    rejected: list[dict[str, Any]] = []
    details: list[str] = []
    authoritative_phase = str(expected_phase or entry.get("phase") or "")
    for line in (delta_text or "").splitlines():
        event = progress_engine.parse_progress_event_line(line)
        if event is None:
            continue
        before_ts = entry.get("last_meaningful_progress_ts")
        ok, error = progress_engine.apply_valid_progress_event(
            entry,
            event,
            expected_wave_id=str(entry.get("wave_id")),
            expected_phase=authoritative_phase,
            expected_phase_instance_id=expected_phase_instance_id,
        )
        if ok:
            applied.append(str(event.get("event_id")))
            if entry.get("last_meaningful_progress_ts") != before_ts:
                # Human-useful operator line from validated state, not raw prose.
                todo = next((t for t in entry.get("todos") or [] if str(t.get("id")) == str(event.get("todo_id"))), None)
                label = f"{todo.get('id')} {todo.get('status')}: {todo.get('title')}" if todo else ""
                details.append(" · ".join(x for x in (label, str(entry.get("current_action") or "")) if x)[:200])
        else:
            rejected.append({"event_id": str(event.get("event_id") or "?"), "error": error})
    return {"applied": applied, "rejected": rejected, "details": details}


def consume_progress_log(
    entry: dict[str, Any],
    log_path: Path,
    *,
    run_id: str,
    phase_instance_id: str,
    expected_phase: str | None = None,
    final: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Durable, line-safe progress ingestion from a managed job log.

    The consumed byte offset lives in canonical state (entry["progress_cursor"])
    and is bound to run_id + Wave + phase + phase_instance_id + log path: a new
    instance or log starts at 0, never at EOF, so an event written right after
    launch or while the controller was down is still applied. Only complete
    lines are consumed while the child runs; `final=True` (child gone, log
    complete) also takes a trailing partial line. The caller saves state, so
    applied events and the advanced cursor persist in one atomic write.
    Replaying bytes is still safe (seen_event_ids), but is not the normal path.
    Returns (consumed_text, {applied, rejected}).
    """
    log_key = os.path.normcase(os.path.abspath(str(log_path)))
    phase = str(expected_phase or entry.get("phase") or "")
    cur = entry.get("progress_cursor")
    offset = 0
    if (isinstance(cur, dict) and cur.get("phase_instance_id") == phase_instance_id
            and cur.get("log_path") == log_key and cur.get("run_id") == run_id):
        try:
            offset = max(0, int(cur.get("offset") or 0))
        except (TypeError, ValueError):
            offset = 0
    data = b""
    try:
        with Path(log_path).open("rb") as fh:
            size = fh.seek(0, 2)
            if size < offset:
                offset = 0  # log truncated/replaced: replay, the reducer dedupes
            fh.seek(offset)
            data = fh.read()
    except OSError:
        pass
    if not final:
        data = data[: data.rfind(b"\n") + 1]
    text = data.decode("utf-8", "replace")
    outcome = (drain_progress_deltas(entry, text, expected_phase=phase, expected_phase_instance_id=phase_instance_id)
               if text else {"applied": [], "rejected": [], "details": []})
    entry["progress_cursor"] = {
        "run_id": run_id, "wave_id": entry.get("wave_id"), "phase": phase,
        "phase_instance_id": phase_instance_id, "log_path": log_key,
        "offset": offset + len(data), "updated_at": utcnow(),
    }
    return text, outcome


def _iso_ts(value: Any) -> float | None:
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return None


def lease_violation(job: dict[str, Any], entry: dict[str, Any] | None, lease: dict[str, Any] | None,
                    *, now: float | None = None) -> str | None:
    """Controller-owned managed-worker lease. None while the worker is within it.

    `phase_runtime_exceeded`: alive longer than max_phase_runtime_seconds since
    the job started. `no_meaningful_progress`: no meaningful progress (the
    reducer's last_meaningful_progress_ts, never heartbeats or log bytes) for
    max_no_meaningful_progress_seconds, measured from max(job start, last
    meaningful progress). 0 disables a limit.
    """
    if not lease:
        return None
    now = time.time() if now is None else now
    started = _iso_ts(job.get("started_at"))
    if started is None:
        return None
    max_rt = int(lease.get("max_phase_runtime_seconds") or 0)
    if max_rt and now - started > max_rt:
        return "phase_runtime_exceeded"
    max_np = int(lease.get("max_no_meaningful_progress_seconds") or 0)
    try:
        last = max(started, float((entry or {}).get("last_meaningful_progress_ts") or 0.0))
    except (TypeError, ValueError):
        last = started
    if max_np and now - last > max_np:
        return "no_meaningful_progress"
    return None


def enforce_lease(run_dir: Path, job_path: Path, entry: dict[str, Any] | None,
                  lease: dict[str, Any] | None, wave: str, phase: str) -> str | None:
    """Terminate an alive managed worker whose lease expired (identity-verified).

    Returns the timeout reason (also recorded durably in the job record and
    events), or None when the worker is within its lease. Counters are never
    touched here: a hung worker is not a semantic audit/repair iteration.
    """
    job = read_phase_job(job_path)
    if job.get("timeout_reason"):
        return str(job["timeout_reason"])
    reason = lease_violation(job, entry, lease)
    if reason is None:
        return None
    outcome = terminate_phase_job_tree(job)
    job = read_phase_job(job_path) or job
    job["timeout_reason"] = reason
    job["timeout_termination"] = outcome
    write_phase_job(job_path, job)
    append_event(run_dir, {"event": "managed_worker_timeout", "wave": wave, "phase": phase, "reason": reason,
                           "pid": job.get("pid"), "termination": outcome, "job": str(job_path)})
    return reason


def controller_fallback_action(phase: str, wave_id: str) -> str:
    table = {
        "plan": f"Planning {wave_id}",
        "run": f"Executing {wave_id}",
        "repair": f"Repairing {wave_id}",
        "audit": f"Auditing {wave_id}",
        "close": f"Closing {wave_id}",
        "reconcile": f"Reconciling {wave_id}",
    }
    return table.get(str(phase).lower(), f"Working {wave_id}")


def max_parallel_concurrency(profile: dict[str, Any]) -> int:
    try:
        from wave_state_engine import parallel_config as _parallel_config
        return int(_parallel_config(profile).get("max_concurrency", 2))
    except Exception:
        for scope in (profile.get("scheduler") or {}, profile.get("parallel") or {}):
            raw = scope.get("max_concurrency")
            try:
                value = int(raw) if raw is not None else None
            except (TypeError, ValueError):
                value = None
            if value is not None and value >= 1:
                return min(value, 8)
        return 2


def pending_parallel_groups(repo: Path, profile: dict[str, Any]) -> list[tuple[int, list[tuple[str, Path]]]]:
    """Pending Waves grouped by numeric scheduling group, ordered by group."""
    pending = engine_pending_targets(repo, profile)
    groups: dict[int, list[tuple[str, Path]]] = {}
    for wid, path in pending:
        try:
            number = engine_wave_number_of(str(wid))
        except ValueError:
            continue
        groups.setdefault(int(number), []).append((wid, path))
    ordered: list[tuple[int, list[tuple[str, Path]]]] = []
    for number in sorted(groups):
        members = sorted(groups[number], key=lambda item: engine_wave_sort_key(str(item[0])))
        ordered.append((int(number), members))
    return ordered


def group_lifecycle_done(repo: Path, profile: dict[str, Any], members: list[tuple[str, Path]]) -> bool:
    """Group barrier: every member must be lifecycle-DONE before the next group starts."""
    for wid, _ in members:
        _, state = engine_wave_location(repo, profile, str(wid))
        if state != "done":
            return False
    return True


def scheduled_group_numbers(repo: Path, profile: dict[str, Any]) -> list[int]:
    """All numeric groups that have any scheduled Wave in any lifecycle state.

    Scope is the engine's single in_scheduler_scope() predicate (the same one
    pending discovery uses), so a base scheduled ID like W101 covers W101a/b.
    """
    numbers: set[int] = set()
    for state_name in ("pending", "done", "blocked", "postponed"):
        try:
            targets = engine_wave_targets_in_folder(repo, profile, state_name, scheduled_only=True)
        except Exception:
            continue
        for wid, _ in targets:
            try:
                numbers.add(int(engine_wave_number_of(str(wid))))
            except ValueError:
                continue
    return sorted(numbers)


def group_members_all_states(repo: Path, profile: dict[str, Any], number: int) -> list[tuple[str, str]]:
    """Every scheduled Wave of a numeric group as (wave_id, lifecycle_state)."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for state_name in ("pending", "done", "blocked", "postponed"):
        try:
            targets = engine_wave_targets_in_folder(repo, profile, state_name, scheduled_only=True)
        except Exception:
            continue
        for wid, _ in targets:
            try:
                if int(engine_wave_number_of(str(wid))) != int(number):
                    continue
            except ValueError:
                continue
            key = str(wid).lower()
            if key in seen:
                continue
            seen.add(key)
            _, loc = engine_wave_location(repo, profile, str(wid))
            out.append((str(wid), str(loc or state_name)))
    out.sort(key=lambda item: engine_wave_sort_key(item[0]))
    return out


def is_group_lifecycle_done(repo: Path, profile: dict[str, Any], number: int) -> bool:
    """True only when every authored/scheduled channel of the group is DONE.

    Candidate PASS, worker PASS, BLOCKED, POSTPONED, and PENDING are never
    completion. An empty (unauthored) group is vacuously done.
    """
    members = group_members_all_states(repo, profile, int(number))
    if not members:
        return True
    return all(state == "done" for _, state in members)


def active_scheduled_group(repo: Path, profile: dict[str, Any]) -> tuple[int, list[tuple[str, str]]] | None:
    """Minimum numeric group with any non-DONE scheduled Wave, or None when all DONE."""
    for number in scheduled_group_numbers(repo, profile):
        members = group_members_all_states(repo, profile, int(number))
        if any(state != "done" for _, state in members):
            return int(number), members
    return None


def apply_phase_result_to_progress(
    state: dict[str, Any],
    run_dir: Path,
    repo: Path,
    target: str,
    phase: str,
    result: dict[str, Any],
) -> None:
    """Controller-owned TODO/counter/health update after a semantic phase result."""
    try:
        entry = ensure_wave_entry(state, target, None)
    except Exception:
        return
    status = str(result.get("status", "")).upper()
    entry["phase"] = str(phase).lower()
    # PLAN structured TODO: validated before storing. The contract was fixed
    # before dispatch; a v2 violation never reaches here as READY (the main
    # loop turned it into orchestration recovery), and nothing is upgraded
    # or downgraded from worker output.
    if str(phase).lower() == "plan" and status in {"READY", "PASS"}:
        store_plan_todo(run_dir, entry, target,
                        evaluate_plan_todo(plan_output_text(repo, result), int(state.get("progress_contract_version") or 1)))
        progress_engine.complete_owned_todos(entry, "plan", str(entry.get("phase_instance_id") or ""))
        progress_engine.mark_meaningful_progress(entry, reason=f"plan:{status}")
        entry["current_action"] = f"Planned {target}; ready for execution"
    elif phase_result_bypasses_no_progress(phase, status):
        progress_engine.mark_meaningful_progress(entry, reason=f"{phase}:{status}")
        if str(phase).lower() in {"run", "repair"}:
            # Accepted forward result: the controller closes this phase's TODOs.
            progress_engine.complete_owned_todos(entry, str(phase).lower(), str(entry.get("phase_instance_id") or ""))
            entry["current_action"] = f"{target} ready for fresh audit"
        elif str(phase).lower() == "audit":
            entry["current_action"] = f"{target} audit PASS; ready to close"
        elif str(phase).lower() == "close":
            entry["current_action"] = f"{target} closed"
            entry["execution_state"] = "done" if status == "PASS" else entry.get("execution_state", "active")
    else:
        # Non-forward result consumes per-Wave no-progress budget in parallel
        # with the global fingerprint guard (which stays authoritative).
        entry["no_progress_count"] = int(entry.get("no_progress_count", 0) or 0) + 1
        entry["health"] = progress_engine.derive_wave_health(entry)
        if not str(entry.get("current_action") or "").strip():
            entry["current_action"] = controller_fallback_action(phase, target)
    # The semantic AUDIT -> REOPEN -> REPAIR iteration is NOT recorded here:
    # this runs before the result is classified/routed, and transport,
    # provider, parser and orchestration recovery results also pass through.
    # See record_audit_reopen_transition(), called after routing is final.
    entry["health"] = progress_engine.derive_wave_health(entry)
    entry["updated_at"] = utcnow()
    save_state(run_dir, state)


# AUDIT results that are accepted findings (REOPEN semantics). Orchestration
# recovery, missing status and provider/transport outcomes never qualify.
SEMANTIC_AUDIT_FINDING_STATUSES = {"REOPEN", "BLOCKED", "FAIL", "NO_PROGRESS"}


def record_audit_reopen_transition(state: dict[str, Any], run_dir: Path, target: str, status: str) -> int | None:
    """Commit one semantic AUDIT #n -> REOPEN -> REPAIR iteration.

    Called by the controller only after the audit result was classified as an
    accepted finding and owner routing is final, immediately before the
    lifecycle moves into REPAIR. Increments `repair_audit_iteration` and
    appends Repair #n / Focused retest #n / Audit #n+1 (+ the single Close)
    TODO history without erasing or re-selecting completed tasks. Returns the new iteration, or None when the
    status is not a semantic finding (no counter change).
    """
    if str(status).upper() not in SEMANTIC_AUDIT_FINDING_STATUSES:
        return None
    entry = ensure_wave_entry(state, target, None)
    iteration = progress_engine.record_repair_audit_iteration(entry)
    # Close only the audit TODO bound to THIS audit dispatch (phase instance);
    # earlier audit items are immutable history.
    progress_engine.complete_phase_todo(entry, "audit", str(entry.get("phase_instance_id") or ""), "REOPEN")
    # The one pending Close moves behind the new iteration (never duplicated).
    todos = entry.setdefault("todos", [])
    pending_close = [t for t in todos if isinstance(t, dict) and str(t.get("kind")) == "close"
                     and str(t.get("status")) == "pending" and not t.get("phase_instance_id")]
    for todo in pending_close:
        todos.remove(todo)
    progress_engine.append_repair_todo_items(
        entry,
        [
            {"title": f"Repair #{iteration}", "kind": "repair", "owner_phase": "repair"},
            {"title": f"Focused retest #{iteration}", "kind": "retest", "owner_phase": "repair"},
            {"title": f"Audit #{progress_engine.audit_item_count(entry) + 1}", "kind": "audit", "owner_phase": "audit"},
        ],
    )
    if pending_close:
        todos.append(pending_close[0])
    else:
        progress_engine.append_repair_todo_items(entry, [{"title": "Close", "kind": "close", "owner_phase": "close"}])
    entry["current_action"] = f"Repair #{iteration} for {target}"
    append_event(run_dir, {"event": "wave_repair_iteration", "wave": target, "repair_audit_iteration": iteration,
                           "status": str(status).upper()})
    save_state(run_dir, state)
    return iteration


def ensure_parallel_repair_todos(entry: dict[str, Any]) -> None:
    """A repair candidate needs a fresh, controller-owned focused retest TODO."""
    open_kinds = {str(todo.get("kind") or "") for todo in entry.get("todos") or []
                  if isinstance(todo, dict) and str(todo.get("owner_phase") or "") == "repair"
                  and str(todo.get("status") or "") in {"pending", "in_progress"}}
    additions = []
    if "repair" not in open_kinds:
        additions.append({"title": "Repair implementation", "kind": "repair", "owner_phase": "repair"})
    if "retest" not in open_kinds:
        additions.append({"title": "Focused retest after repair", "kind": "retest", "owner_phase": "repair"})
    if additions:
        progress_engine.append_repair_todo_items(entry, additions)


def validate_parallel_group_authoring(
    repo: Path, profile: dict[str, Any], members: list[tuple[str, Path]]
) -> list[str]:
    """Fail-closed authoring gate for one parallel group. Never silent fallback.

    Normalizes member metadata then delegates to the shared
    `wave_state_engine.check_parallel_group_invariants` helper so the runtime
    gate and the standalone authoring validator cannot drift.
    """
    from wave_state_engine import check_parallel_group_invariants as _shared_check
    errors: list[str] = []
    if len(members) < 2:
        return errors
    entries: dict[str, dict[str, Any]] = {}
    for wid, path in members:
        try:
            meta = wave_metadata(path, profile)
        except Exception as exc:
            errors.append(f"group-metadata-unreadable:{wid}:{exc}")
            continue
        owned = meta.get("owned_requirements") or []
        if isinstance(owned, str):
            owned = [owned]
        deps = meta.get("completion_dependencies") or []
        if isinstance(deps, str):
            deps = [deps]
        resources = meta.get("exclusive_resources") or []
        if isinstance(resources, str):
            resources = [resources]
        try:
            number = engine_wave_number_of(str(wid))
            channel = engine_wave_channel_of(str(wid))
        except ValueError:
            errors.append(f"group-identity-invalid:{wid}")
            continue
        # Controller-owned surfaces (lifecycle dirs, trackers, Agent Core) are never a write surface.
        for hit in engine_reserved_surface_hits([str(x) for x in (meta.get("write_surface") or [])], profile):
            errors.append(f"reserved-write-surface:{wid}:{hit}")
        entries[str(wid)] = {
            "number": int(number),
            "channel": str(channel or "").lower(),
            "channel_group": meta.get("channel_group"),
            "write_surface": [str(x) for x in (meta.get("write_surface") or [])],
            "completion_dependencies": [str(x) for x in deps],
            "exclusive_resources": [str(x) for x in resources],
            "owned_requirements": [str(x) for x in owned],
        }
    if errors:
        return errors
    try:
        return list(_shared_check(entries))
    except Exception as exc:
        return [f"authoring-check-failed:{exc}"]


def allocate_parallel_slots(
    members: list[str], running: set[str], max_concurrency: int
) -> tuple[list[str], list[str]]:
    """Deterministic slot allocation in channel order. Returns (to_start, waiting_slot)."""
    ordered = sorted(members, key=engine_wave_sort_key)
    idle = [wid for wid in ordered if wid not in running]
    free = max(0, int(max_concurrency) - len(running))
    return idle[:free], idle[free:]


def _parallel_group_state(state: dict[str, Any], group: int) -> dict[str, Any]:
    groups = state.setdefault("parallel_groups", {})
    if not isinstance(groups, dict):
        state["parallel_groups"] = groups = {}
    gstate = groups.setdefault(str(int(group)), {})
    if not isinstance(gstate, dict):
        groups[str(int(group))] = gstate = {}
    channels = gstate.setdefault("channels", {})
    if not isinstance(channels, dict):
        gstate["channels"] = channels = {}
    return gstate


def _persist_channel_job(
    state: dict[str, Any],
    run_dir: Path,
    repo: Path,
    *,
    group: int,
    wave_id: str,
    phase: str,
    phase_instance_id: str,
    job_path: Path,
    log_path: Path,
    proc_pid: int | None,
    start_marker: str | None,
    workspace: Path,
    base_head: str | None,
    base_content_identity: str | None,
    seq: int,
    status: str = "RUNNING",
    offset: int = 0,
    progress_contract_version: int = 1,
    todo_plan_state: str | None = None,
) -> dict[str, Any]:
    """Durable per-channel job identity. One Wave + one phase instance = one record.

    The controller-resolved contract version and plan state travel with the
    record so a reattach after a restart can tell a RUN/REPAIR that was
    dispatched from an unaccepted plan and must not be adopted.
    """
    gstate = _parallel_group_state(state, group)
    try:
        job_rel = str(job_path.relative_to(repo))
    except ValueError:
        job_rel = str(job_path)
    record = {
        "wave_id": str(wave_id),
        "channel": engine_wave_channel_of(str(wave_id)) if str(wave_id) else "",
        "group": int(group),
        "phase": str(phase),
        "phase_instance_id": str(phase_instance_id),
        "job_rel": job_rel,
        "log_path": str(log_path),
        "pid": int(proc_pid) if proc_pid else None,
        "process_start_time": start_marker,
        "workspace": str(workspace),
        "base_head": base_head,
        "base_content_identity": base_content_identity,
        "progress_contract_version": int(progress_contract_version),
        "todo_plan_state": str(todo_plan_state) if todo_plan_state else None,
        "status": status,
        "seq": int(seq),
        "offset": int(offset),
        "updated_at": utcnow(),
    }
    try:
        record["channel"] = str(engine_wave_channel_of(str(wave_id)))
    except ValueError:
        record["channel"] = ""
    gstate["channels"][str(wave_id)] = record
    save_state(run_dir, state)
    return record


def _reattach_channel_job(
    repo: Path,
    run_dir: Path,
    program: str,
    *,
    group: int,
    wave_id: str,
    record: dict[str, Any],
    progress_contract_version: int = 1,
    todo_plan_state: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Resume-time reattach with fail-closed identity: never duplicate, never orphan.

    Outcomes:
      reattached - the same semantic worker, alive and start-marker verified:
                   reuse it and resume its progress cursor.
      exited     - the same instance already exited (or its PID was recycled)
                   while the controller was down and its result was never
                   consumed: no live process, consume its durable log once.
      mismatch   - a live Agent Core child whose identity differs from the
                   record or cannot be proven. Returned as info so the caller
                   keeps it accounted (JOIN) and dispatches no replacement for
                   this Wave/worktree until it has exited. Never adopted as
                   authority, never killed here.
      stale      - nothing alive to account for (dead, consumed, or its PID
                   now belongs to another process per the start marker).
    """
    if not isinstance(record, dict) or not str(record.get("job_rel") or ""):
        return None, "stale"
    job_rel = str(record.get("job_rel"))
    job_path = repo / job_rel if not Path(job_rel).is_absolute() else Path(job_rel)
    job = read_phase_job(job_path)
    mismatches: list[str] = []
    if not job:
        # Job file lost but state still names the child: rebuild a receipt so
        # JOIN can track the PID; its identity is unprovable, so fail closed.
        job = {"pid": record.get("pid"), "process_start_time": record.get("process_start_time"),
               "wave_id": str(wave_id), "status": "RUNNING", "recovered_from_state": True,
               "log_path": str(record.get("log_path") or job_path.with_suffix(".log"))}
        if phase_job_liveness(job) == "dead":
            return None, "stale"
        write_phase_job(job_path, job)
        mismatches.append("job-record-missing")
    liveness = phase_job_liveness(job)
    consumed = str(job.get("status") or "").upper() == "CONSUMED"
    if liveness == "dead" and consumed:
        return None, "stale"
    try:
        channel = engine_wave_channel_of(str(wave_id))
    except ValueError:
        channel = ""
    expected_identity = {
        "run_id": run_dir.name, "program": program, "parallel_group": int(group),
        "wave_id": str(wave_id), "channel": channel, "phase": str(record.get("phase") or ""),
        "phase_instance_id": str(record.get("phase_instance_id") or ""),
        "workspace": record.get("workspace"), "base_head": record.get("base_head"),
        "base_content_identity": record.get("base_content_identity"),
    }
    if not phase_channel_job_matches(job, **expected_identity):
        mismatches += phase_job_identity_mismatches(job, expected_identity)
        if not mismatches:
            mismatches.append("channel-job-identity-mismatch")
    rec_marker = str(record.get("process_start_time") or "")
    if rec_marker and str(job.get("process_start_time") or "") != rec_marker:
        mismatches.append("process_start_time:job!=record")
    if liveness == "unverified":
        mismatches.append("process_start_time:unrecorded")
    # Progress contract v2: a RUN/REPAIR dispatched from a plan that is not
    # accepted is never adopted after a restart. The child stays accounted
    # (JOIN) and the channel gets no replacement until it exits; the PLAN gate
    # then forces a fresh PLAN for this Wave.
    if v2_plan_gate_violation({"progress_contract_version": progress_contract_version},
                              {"todo_plan_state": todo_plan_state},
                              str(record.get("phase") or "")) is not None:
        mismatches.append("v2-plan-unaccepted")
    info = {
        "job_path": job_path,
        "log_path": Path(str(job.get("log_path") or record.get("log_path") or job_path.with_suffix(".log"))),
        "proc": None,
        "phase": str(record.get("phase")),
        "instance": str(record.get("phase_instance_id")),
        "seq": int(record.get("seq") or 0),
        "offset": int(record.get("offset") or 0),
        "reattached": True,
    }
    if liveness == "dead":
        # Exited while the controller was down: consume its durable log once,
        # but only when it is provably this instance.
        return (info, "exited") if not mismatches else (None, "stale")
    if mismatches:
        info["mismatch"] = mismatches
        return info, "mismatch"
    return info, "reattached"


def _discover_live_wave_jobs(run_dir: Path, wave_id: str, known: set[str]) -> list[dict[str, Any]]:
    """Managed children for `wave_id` that are alive but absent from state.

    Covers the crash window between start_job() writing the job file and the
    controller persisting its channel record. Not-provably-dead counts as alive.
    """
    out: list[dict[str, Any]] = []
    for job_path in sorted(run_dir.glob("*-job.json")):
        if os.path.normcase(str(job_path.resolve())) in known:
            continue
        job = read_phase_job(job_path)
        if str(job.get("wave_id") or job.get("target") or "") != str(wave_id):
            continue
        if str(job.get("status") or "").upper() == "CONSUMED" or phase_job_liveness(job) == "dead":
            continue
        out.append({"job_path": job_path, "log_path": Path(str(job.get("log_path") or job_path.with_suffix(".log"))),
                    "proc": None, "mismatch": ["unrecorded-live-job"]})
    return out


def start_channel_job(
    *,
    run_dir: Path,
    program: str,
    group: int,
    wave_id: str,
    worktree: Path,
    phase: str,
    instance_id: str,
    seq: int,
    frozen: dict[str, Any],
    args: list[str],
    backend: str = "opencode",
    result_path: Path | None = None,
    stdin_path: Path | None = None,
    progress_contract_version: int = 1,
    todo_plan_state: str | None = None,
):
    """Start one parallel channel worker with the full semantic identity that reattach verifies.

    `backend` is recorded in the durable job so result consumption (also after a
    controller restart) reads the backend's own result channel: the OpenCode
    bridge's machine block, or the Codex `--output-last-message` JSON.
    `progress_contract_version`/`todo_plan_state` are the controller's own
    resolution, recorded so a reattach can refuse to adopt a RUN/REPAIR that was
    dispatched from an unaccepted plan.
    """
    log_path = run_dir / f"{seq:04d}-{wave_id}-{phase}-parallel.log"
    job_path = run_dir / f"{seq:04d}-{wave_id}-{phase}-parallel-job.json"
    proc = start_phase_job(
        args=args, cwd=worktree, log_path=log_path, job_path=job_path, stdin_path=stdin_path,
        metadata={"seq": seq, "target": wave_id, "wave_id": wave_id, "phase": phase,
                  "program": program, "backend": str(backend), "controller_pid": os.getpid(),
                  "run_id": run_dir.name, "phase_instance_id": instance_id,
                  "parallel_group": int(group), "channel": engine_wave_channel_of(wave_id) if wave_id else "",
                  "workspace": str(worktree), "base_head": frozen.get("base_head"),
                  "base_content_identity": frozen.get("base_content_identity"),
                  "progress_contract_version": int(progress_contract_version),
                  "todo_plan_state": str(todo_plan_state) if todo_plan_state else None,
                  # Not "result_path": start_job owns that key (normalized receipt).
                  "codex_result_path": str(result_path) if result_path is not None else None},
    )
    return job_path, log_path, proc


def channel_owner_route(repo: Path, run_dir: Path, profile: dict[str, Any], wave_id: str, wave_path: Path,
                        phase: str, seq: int, status: str, machine: dict[str, Any], authoritative: str) -> dict[str, Any] | None:
    """Route a parallel channel's semantic finding through the controller's
    finding ledger (route-wave-findings.py, the same router serial AUDIT uses).

    Returns {from, owner, owner_state, findings_path} when the finding's true
    owner is another Wave; None when it belongs to this channel (self repair).
    The worker never chooses the owner: requirement ownership does.
    """
    findings = [str(x) for x in (machine.get("findings") or []) if str(x).strip()] or [authoritative[-1600:]]
    normalized = run_dir / f"{int(seq):04d}-{wave_id}-{phase}-parallel-normalized.json"
    # Same persistence boundary as the serial normalized receipt: worker prose can quote
    # this machine's scratch-output paths, and the routed findings ledger is derived from
    # this receipt, so redaction here keeps the whole parallel path clean.
    write_json(normalized, {"status": status,
                            "summary": _redact_environment_paths(authoritative[-3000:]),
                            "findings": [_redact_environment_paths(f) for f in findings],
                            "changed_files": [], "next_action": "repair"})
    try:
        canonical = str(wave_metadata(wave_path, profile).get("canonical_source") or "") or None
    except Exception:
        canonical = None
    try:
        findings_path = route_findings(repo, run_dir, wave_id, canonical, None, None, int(seq), normalized)
    except (RuntimeError, OSError) as exc:
        # No ledger, no ownership claim: keep the channel's own repair (recorded).
        append_event(run_dir, {"event": "parallel_owner_route_unavailable", "wave": wave_id, "detail": str(exc)[:300]})
        return None
    owner = routed_owner(findings_path, wave_id)
    if not owner:
        return None
    owner_path, owner_state = engine_wave_location(repo, profile, owner)
    if owner_path is None:
        append_event(run_dir, {"event": "owner_route_unresolved", "target": wave_id, "owner": owner, "parallel": True})
        return None
    return {"from": wave_id, "owner": owner, "owner_state": owner_state, "status": status,
            "findings_path": str(findings_path.relative_to(repo))}


def channel_machine_result(job: dict[str, Any], output: str, phase: str) -> tuple[dict[str, str], str]:
    """Machine result of a finished channel job -> (machine, authoritative text).

    Front ends whose CLI returns schema JSON (see SCHEMA_JSON_BACKENDS) are read
    through the same validated result path, so their decisions are identical.
    Bridge-based front ends use the single machine block after the bridge
    sentinel. Raises ValueError (recovery).
    """
    if str(job.get("backend") or "") in SCHEMA_JSON_BACKENDS:
        data = read_json_file(Path(str(job["codex_result_path"]))) if job.get("codex_result_path") else None
        if not isinstance(data, dict):
            raise ValueError(f"{job.get('backend')} result JSON missing or invalid")
        status = str(data.get("status") or "").upper()
        if status not in RESULT_SCHEMA["properties"]["status"]["enum"]:
            raise ValueError(
                f"{job.get('backend')} result status outside canonical schema: {status or '<missing>'}")
        machine = {"status": status, "findings": [str(x) for x in (data.get("findings") or [])]}
        if str(data.get("repair_hypothesis") or "").strip():
            machine["repair_hypothesis"] = str(data["repair_hypothesis"]).strip()
        return machine, output
    authoritative = bridge_authoritative_output(output) if BRIDGE_STDOUT_SENTINEL in output else output
    return parse_machine_result(authoritative, phase), authoritative


def run_parallel_group_implement(
    *,
    repo: Path,
    profile: dict[str, Any],
    program: str,
    run_dir: Path,
    state: dict[str, Any],
    group: int,
    members: list[tuple[str, Path]],
    frozen: dict[str, Any],
    seq_start: int,
    dispatch_fn=None,
    poll_seconds: float = 0.2,
    backend: str = "opencode",
    codex_model: str | None = None,
) -> dict[str, Any]:
    """Managed parallel implement stage for one numeric group.

    Each eligible channel runs concurrently in its own worktree at the frozen
    base. `dispatch_fn(wave_id, worktree, phase, instance_id, seq)` may be
    injected by tests; by default the controller's `backend` decides the
    worker: `opencode` -> the family's OpenCode phase bridge, `codex` -> a
    managed `codex exec` job. A Codex run never falls back to an OpenCode
    bridge. Returns {candidates, errors, next_seq, joined}. The caller must
    JOIN before integration or terminal exit; this function always joins
    every dispatch.
    """
    if backend not in BACKENDS:
        raise ValueError(f"unsupported parallel backend: {backend}")
    contract = int(state.get("progress_contract_version") or 1)
    max_c = max_parallel_concurrency(profile)
    lease = engine_managed_job_lease(profile)
    timeouts: dict[str, str] = {}
    unresolved: dict[str, str] = {}  # wave -> job path of a live child that could not be resolved
    exhausted: list[dict[str, Any]] = []  # channels that used up their no-progress budget
    owner_pivot: dict[str, Any] | None = None  # a channel finding owned by another Wave
    gstate = _parallel_group_state(state, group)
    running: dict[str, dict[str, Any]] = {}
    completed: dict[str, dict[str, Any]] = {}
    candidates: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    seq = int(seq_start)
    dispatched: list[dict[str, Any]] = []
    # Ensure entries + workspaces.
    worktrees: dict[str, Path] = {}
    member_titles: dict[str, str] = {}
    for wid, wpath in members:
        try:
            _m = wave_metadata(wpath, profile)
            member_titles[str(wid)] = str(_m.get("wave_title") or "").strip()
        except Exception:
            member_titles[str(wid)] = ""
        entry = ensure_wave_entry(state, str(wid), {"wave_title": member_titles[str(wid)]} if member_titles[str(wid)] else None)
        entry["phase"] = "run"
        if member_titles[str(wid)]:
            entry["wave_title"] = member_titles[str(wid)]
        try:
            number = engine_wave_number_of(str(wid))
            channel = engine_wave_channel_of(str(wid))
        except ValueError:
            number, channel = group, ""
        worktree = workspace_engine.channel_workspace(repo, run_dir.name, group, str(wid))
        worktrees[str(wid)] = worktree
    save_state(run_dir, state)
    pending_ids = [str(wid) for wid, _ in members]

    def _plan_gate_meta(wave_id: str) -> tuple[int, str | None]:
        """The controller's own contract/plan resolution for a channel job record.

        Read at dispatch time from the entry the controller owns, so the durable
        job, the channel record and the reattach gate all see one value.
        """
        try:
            _entry = ensure_wave_entry(state, str(wave_id), None)
            return contract, (str(_entry.get("todo_plan_state")) if _entry.get("todo_plan_state") else None)
        except Exception:
            return contract, None

    def _default_dispatch(wave_id: str, worktree: Path, phase: str, instance_id: str, cur_seq: int):
        script_map = {
            "ac-wave-luna-openai-parallel": "run-ac-wave-luna-openai-phase.ps1",
            "ac-wave-opencode-parallel": "run-ac-wave-opencode-phase.ps1",
            "ac-wave-hybrid-parallel": "run-ac-wave-hybrid-phase.ps1",
        }
        script_name = "run-ac-wave-opencode-phase.ps1"
        for key, name in script_map.items():
            if program.startswith(key.rsplit("-parallel", 1)[0] + "-"):
                script_name = name
                break
        script = SCRIPT_ROOT / script_name
        # The worker learns its phase_instance_id from the controller context;
        # without it every progress event would be rejected as stale.
        context_path = phase_controller_context(repo, run_dir, cur_seq, wave_id, phase,
                                                str(frozen.get("base_content_identity") or "unknown"), state, None)
        exe = shutil.which("powershell") or "powershell"
        args = [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), phase, wave_id,
                "-RepoRoot", str(worktree), "-ControllerContextPath", str(context_path)]
        return start_channel_job(run_dir=run_dir, program=program, group=group, wave_id=wave_id, worktree=worktree,
                                 phase=phase, instance_id=instance_id, seq=cur_seq, frozen=frozen, args=args,
                                 progress_contract_version=_plan_gate_meta(wave_id)[0],
                                 todo_plan_state=_plan_gate_meta(wave_id)[1])

    def _codex_dispatch(wave_id: str, worktree: Path, phase: str, instance_id: str, cur_seq: int):
        # Same prompt/contract as the serial Codex path, rooted in the channel
        # worktree; the worker is a managed job, so restart/reattach/JOIN hold.
        wave_file = Path(dict(members)[wave_id])
        try:
            rel = wave_file.resolve().relative_to(repo.resolve())
        except ValueError:
            rel = Path(wave_file.name)
        try:
            canonical = str(wave_metadata(wave_file, profile).get("canonical_source") or "") or None
        except Exception:
            canonical = None
        prompt = build_phase_prompt(worktree, str(profile.get("project_id") or ""), wave_id, worktree / rel, phase,
                                    canonical, None, False, None, str(frozen.get("base_content_identity") or "unknown"),
                                    phase_instance_id=instance_id, progress_contract_version=contract)
        prompt_path = run_dir / f"{cur_seq:04d}-{wave_id}-{phase}-parallel.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        result_path = run_dir / f"{cur_seq:04d}-{wave_id}-{phase}-parallel-result.json"
        sandbox = "read-only" if phase in {"reconcile", "plan", "audit"} else "workspace-write"
        placeholder = str(run_dir / "__RESULT_PATH_PLACEHOLDER__")
        args = [str(result_path) if a == placeholder else a for a in codex_exec_args(run_dir, sandbox, codex_model)] + ["-"]
        return start_channel_job(run_dir=run_dir, program=program, group=group, wave_id=wave_id, worktree=worktree,
                                 phase=phase, instance_id=instance_id, seq=cur_seq, frozen=frozen, args=args,
                                 backend="codex", result_path=result_path, stdin_path=prompt_path,
                                 progress_contract_version=_plan_gate_meta(wave_id)[0],
                                 todo_plan_state=_plan_gate_meta(wave_id)[1])

    def _cli_dispatch(wave_id: str, worktree: Path, phase: str, instance_id: str, cur_seq: int,
                     backend: str):
        """Managed channel worker for any front end that runs its own CLI.

        One prompt, one contract, one durable job record. Only the executable and
        its flags differ per front end, so scheduling, progress, join, evidence
        and integration stay identical across backends by construction.
        """
        wave_file = Path(dict(members)[wave_id])
        try:
            rel = wave_file.resolve().relative_to(repo.resolve())
        except ValueError:
            rel = Path(wave_file.name)
        try:
            canonical = str(wave_metadata(wave_file, profile).get("canonical_source") or "") or None
        except Exception:
            canonical = None
        prompt = build_phase_prompt(worktree, str(profile.get("project_id") or ""), wave_id, worktree / rel, phase,
                                    canonical, None, False, None, str(frozen.get("base_content_identity") or "unknown"),
                                    phase_instance_id=instance_id, progress_contract_version=contract)
        prompt_path = run_dir / f"{cur_seq:04d}-{wave_id}-{phase}-parallel.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        result_path = run_dir / f"{cur_seq:04d}-{wave_id}-{phase}-parallel-result.json"
        sandbox = "read-only" if phase in {"reconcile", "plan", "audit"} else "workspace-write"
        placeholder = str(run_dir / "__RESULT_PATH_PLACEHOLDER__")
        transport = BACKEND_TRANSPORTS[backend]
        args = [str(result_path) if a == placeholder else a
                for a in transport(run_dir, sandbox, codex_model)] + ["-"]
        return start_channel_job(run_dir=run_dir, program=program, group=group, wave_id=wave_id,
                                 worktree=worktree, phase=phase, instance_id=instance_id, seq=cur_seq,
                                 frozen=frozen, args=args, backend=backend, result_path=result_path,
                                 stdin_path=prompt_path,
                                 progress_contract_version=_plan_gate_meta(wave_id)[0],
                                 todo_plan_state=_plan_gate_meta(wave_id)[1])

    def _claude_dispatch(wave_id: str, worktree: Path, phase: str, instance_id: str, cur_seq: int):
        return _cli_dispatch(wave_id, worktree, phase, instance_id, cur_seq, "claude")

    _CHANNEL_DISPATCH = {"codex": _codex_dispatch, "claude": _claude_dispatch}

    # Repair loops stay bounded; audit/close happen serially after integration.
    # Restore persisted phases/attempts so a restart never resets progress.
    channel_phase: dict[str, str] = {}
    attempts: dict[str, int] = {}
    for wid, _ in members:
        key = str(wid)
        rec = (gstate.get("channels") or {}).get(key) if isinstance(gstate.get("channels"), dict) else None
        if isinstance(rec, dict) and str(rec.get("phase") or "") in {"plan", "run", "repair"}:
            channel_phase[key] = str(rec.get("phase"))
        else:
            channel_phase[key] = "plan"
        try:
            attempts[key] = int(rec.get("attempts") or 0) if isinstance(rec, dict) else 0
        except (TypeError, ValueError):
            attempts[key] = 0
    joined: list[dict[str, Any]] = []
    # Live children that are not provably the current instance: accounted,
    # never adopted, and their Wave gets no new worker until they exit.
    quarantined: dict[str, list[dict[str, Any]]] = {}
    # Restart reattach: an authoritative live job is reused, never duplicated.
    for wid, _ in members:
        key = str(wid)
        rec = (gstate.get("channels") or {}).get(key) if isinstance(gstate.get("channels"), dict) else None
        if not isinstance(rec, dict):
            continue
        info, outcome = _reattach_channel_job(repo, run_dir, program, group=group, wave_id=key, record=rec,
                                              progress_contract_version=_plan_gate_meta(key)[0],
                                              todo_plan_state=_plan_gate_meta(key)[1])
        if outcome in {"reattached", "exited"} and info is not None:
            running[key] = info
            dispatched.append({"job_path": info["job_path"], "log_path": info["log_path"], "proc": info.get("proc"), "offset": int(info.get("offset") or 0)})
            channel_phase[key] = str(rec.get("phase") or channel_phase.get(key, "plan"))
            append_event(run_dir, {"event": "parallel_reattach", "wave": key, "group": group, "outcome": outcome,
                                   "phase": channel_phase[key], "phase_instance_id": info.get("instance")})
        elif outcome == "stale":
            append_event(run_dir, {"event": "parallel_stale_job", "wave": key, "group": group,
                                   "phase": str(rec.get("phase") or "")})
        elif outcome == "mismatch" and info is not None:
            # Fail closed: the live child stays accounted (JOIN) and blocks any
            # replacement in this Wave/worktree until it is gone.
            quarantined.setdefault(key, []).append(info)
            dispatched.append({"job_path": info["job_path"], "log_path": info["log_path"], "proc": None})
            append_event(run_dir, {"event": "parallel_job_mismatch", "wave": key, "group": group,
                                   "job": str(info["job_path"]), "mismatch": info.get("mismatch")})
    # Live children the state never recorded (crash between start and persist).
    known = {os.path.normcase(str(Path(i["job_path"]).resolve())) for i in dispatched}
    for wid, _ in members:
        for info in _discover_live_wave_jobs(run_dir, str(wid), known):
            quarantined.setdefault(str(wid), []).append(info)
            dispatched.append({"job_path": info["job_path"], "log_path": info["log_path"], "proc": None})
            known.add(os.path.normcase(str(Path(info["job_path"]).resolve())))
            append_event(run_dir, {"event": "parallel_job_mismatch", "wave": str(wid), "group": group,
                                   "job": str(info["job_path"]), "mismatch": info.get("mismatch")})
    save_state(run_dir, state)

    def _release_quarantine() -> None:
        # A quarantined child is released only once it is provably gone; its
        # output is never lifecycle authority.
        for qwid in list(quarantined):
            keep = []
            for q in quarantined[qwid]:
                if phase_job_is_alive(read_phase_job(q["job_path"]), None):
                    expired = enforce_lease(run_dir, q["job_path"], None,
                                            {"max_phase_runtime_seconds": lease.get("max_phase_runtime_seconds")}, qwid, "quarantined")
                    if expired and phase_job_is_alive(read_phase_job(q["job_path"]), None):
                        # Past the hard cap and not killable (identity unverified):
                        # stop waiting; never kill a possibly-foreign PID. The Wave
                        # gets no replacement and its workspace stays protected.
                        unresolved[qwid] = str(q["job_path"])
                        completed[qwid] = {"status": "UNRESOLVED_CHILD"}
                        errors.append(f"unresolved-child:{qwid}:{q['job_path']}")
                        append_event(run_dir, {"event": "parallel_unresolved_child", "wave": qwid, "group": group,
                                               "job": str(q["job_path"])})
                        continue
                    keep.append(q)
                    continue
                mark_phase_job_result(q["job_path"], status="IDENTITY_MISMATCH_DISCARDED", consumed=True)
                append_event(run_dir, {"event": "parallel_mismatch_released", "wave": qwid, "group": group,
                                       "job": str(q["job_path"])})
            if keep:
                quarantined[qwid] = keep
            else:
                del quarantined[qwid]

    try:
        while len(completed) < len(pending_ids):
            _release_quarantine()
            busy = set(running) | set(quarantined)
            to_start, waiting = allocate_parallel_slots(
                [wid for wid in pending_ids if wid not in completed and wid not in busy], busy, max_c
            )
            if owner_pivot:
                to_start, waiting = [], []  # ownership pivot: never dispatch more of this group
            for wid in waiting:
                append_event(run_dir, {"event": "parallel_waiting_slot", "wave": wid, "group": group})
                try:
                    _wentry = ensure_wave_entry(state, wid, None)
                    if _wentry.get("execution_state") != "done":
                        _wentry["execution_state"] = "waiting_slot"
                        _wentry["current_action"] = "Waiting for concurrency slot"
                except Exception:
                    pass
            save_state(run_dir, state)
            for wid in to_start:
                phase = channel_phase.get(wid, "run")
                entry = ensure_wave_entry(state, wid, None)
                # Progress contract v2, parallel path: a channel restored at
                # RUN/REPAIR from a persisted record (restart, migration, or a
                # plan that was never accepted) runs PLAN first. Same gate and
                # same semantics as the serial path; bounded by the existing
                # attempts>=3 channel-stalled bound, and no audit/repair
                # counter is touched.
                requested_phase = phase
                _unaccepted = v2_plan_gate_violation(state, entry, requested_phase)
                if _unaccepted is not None:
                    phase = "plan"
                    channel_phase[wid] = phase
                    entry["todo_plan_state"] = _unaccepted
                    entry["current_action"] = f"Planning {wid}: awaiting structured TODO plan"
                    append_event(run_dir, {"event": "v2_plan_required_before_phase", "target": wid,
                                           "requested_phase": requested_phase, "todo_plan_state": _unaccepted,
                                           "contract": contract, "parallel_group": group})
                    save_state(run_dir, state)
                seq += 1
                instance = new_phase_instance_id(run_dir.name, seq, wid, phase)
                entry["phase"] = phase
                entry["phase_instance_id"] = instance
                entry["execution_state"] = "active"
                # Semantic counters: one increment per fresh dispatch.
                # Transport/poll retries never touch these counters.
                if str(phase).lower() == "audit":
                    progress_engine.record_audit_attempt(entry)
                if str(phase).lower() == "repair":
                    progress_engine.record_repair_attempt(entry)
                entry["current_action"] = controller_fallback_action(phase, wid)
                save_state(run_dir, state)
                worktree = worktrees[wid]
                fn = dispatch_fn or _CHANNEL_DISPATCH.get(backend, _default_dispatch)
                try:
                    job_path, log_path, proc = fn(wid, worktree, phase, instance, seq)
                except Exception as exc:
                    errors.append(f"dispatch-failed:{wid}:{exc}")
                    completed[wid] = {"status": "DISPATCH_FAILED", "detail": str(exc)}
                    continue
                # Accounted for JOIN before anything else can raise.
                dispatched.append({"job_path": job_path, "log_path": log_path, "proc": proc})
                # Durable identity BEFORE polling so a crash cannot lose it.
                try:
                    start_marker = phase_job_is_alive(read_phase_job(job_path), proc) and str(read_phase_job(job_path).get("process_start_time") or "") or None
                except Exception:
                    start_marker = None
                if start_marker is None:
                    try:
                        start_marker = str(read_phase_job(job_path).get("process_start_time") or "") or None
                    except Exception:
                        start_marker = None
                _persist_channel_job(state, run_dir, repo, group=group, wave_id=wid, phase=phase,
                                     phase_instance_id=instance, job_path=job_path, log_path=log_path,
                                     proc_pid=int(proc.pid) if proc is not None and hasattr(proc, "pid") else None,
                                     start_marker=start_marker, workspace=worktree,
                                     base_head=frozen.get("base_head"),
                                     base_content_identity=frozen.get("base_content_identity"),
                                     seq=seq, status="RUNNING", offset=0,
                                     progress_contract_version=contract,
                                     todo_plan_state=str(entry.get("todo_plan_state") or "") or None)
                try:
                    gstate["channels"][wid]["attempts"] = int(attempts.get(wid, 0))
                    save_state(run_dir, state)
                except Exception:
                    pass
                running[wid] = {"job_path": job_path, "log_path": log_path, "proc": proc,
                                "phase": phase, "instance": instance, "seq": seq, "offset": 0}
                append_event(run_dir, {"event": "parallel_dispatch", "wave": wid, "group": group, "phase": phase,
                                       "phase_instance_id": instance, "job": str(job_path)})
                save_state(run_dir, state)
            if not running and not quarantined:
                break
            # Poll all running workers together; consume live progress per
            # channel from its durable cursor. Liveness is sampled before the
            # read, so a read after exit is final and sees the complete log.
            time.sleep(max(0.05, poll_seconds))
            finished: list[str] = []
            for wid, info in list(running.items()):
                alive = phase_job_is_alive(read_phase_job(info["job_path"]), info["proc"])
                entry = ensure_wave_entry(state, wid, None)
                if alive:
                    _reason = enforce_lease(run_dir, info["job_path"], entry, lease, wid, info["phase"])
                    if _reason:
                        timeouts[wid] = _reason
                        alive = phase_job_is_alive(read_phase_job(info["job_path"]), info["proc"])
                        job = read_phase_job(info["job_path"])
                        if alive and not (job.get("timeout_termination") or {}).get("terminated"):
                            unresolved[wid] = str(info["job_path"])
                            completed[wid] = {"status": "UNRESOLVED_CHILD"}
                            errors.append(f"unresolved-child:{wid}:{info['job_path']}")
                            entry["health"] = "stalled"
                            entry["current_action"] = "Worker tree unresolved; workspace retained"
                            running.pop(wid, None)
                            append_event(run_dir, {"event": "parallel_unresolved_child", "wave": wid, "group": group,
                                                   "job": str(info["job_path"]), "termination": job.get("timeout_termination")})
                            save_state(run_dir, state)
                            continue
                before = (entry.get("progress_cursor") or {}).get("offset")
                _, outcome = consume_progress_log(entry, info["log_path"], run_id=run_dir.name,
                                                  phase_instance_id=info["instance"], expected_phase=info["phase"],
                                                  final=not alive)
                info["offset"] = int(entry["progress_cursor"]["offset"])
                if outcome["applied"] or outcome["rejected"]:
                    append_event(run_dir, {"event": "wave_progress" if alive else "wave_progress_final", "wave": wid,
                                           "applied": outcome["applied"], "rejected": outcome["rejected"], "details": outcome.get("details") or []})
                if outcome["applied"] or outcome["rejected"] or before != info["offset"]:
                    rec = gstate["channels"].get(wid)
                    if isinstance(rec, dict):
                        rec["offset"] = info["offset"]
                    save_state(run_dir, state)
                if not alive:
                    finished.append(wid)
            for wid in finished:
                info = running.pop(wid)
                job = read_phase_job(info["job_path"])
                try:
                    output = info["log_path"].read_text(encoding="utf-8", errors="replace")
                except OSError:
                    output = ""
                entry = ensure_wave_entry(state, wid, None)
                job_status = str(job.get("status") or "EXITED")
                exit_code = job.get("exit_code")
                # Backend-aware result: Codex result JSON or the bridge machine
                # block (fake dispatch_fn outputs are plain machine blocks).
                authoritative = output
                if owner_pivot and not job.get("timeout_reason"):
                    # Sibling JOINed after an ownership pivot: its work was built on a
                    # base the owner repair will change, so it is discarded, never a candidate.
                    mark_phase_job_result(info["job_path"], status="DISCARDED_FOR_OWNER_ROUTE", consumed=True)
                    completed[wid] = {"status": "DISCARDED_FOR_OWNER_ROUTE"}
                    joined.append({"wave": wid, "phase": info["phase"], "status": "DISCARDED_FOR_OWNER_ROUTE",
                                   "exit_code": job.get("exit_code"), "job_status": str(job.get("status") or "")})
                    append_event(run_dir, {"event": "parallel_join", "wave": wid, "group": group, "phase": info["phase"],
                                           "status": "DISCARDED_FOR_OWNER_ROUTE"})
                    save_state(run_dir, state)
                    continue
                if job.get("timeout_reason") and not (job.get("timeout_termination") or {}).get("terminated"):
                    # Leader gone but descendants not proven drained: unresolved, never a clean terminal.
                    unresolved[wid] = str(info["job_path"])
                    completed[wid] = {"status": "UNRESOLVED_CHILD"}
                    errors.append(f"unresolved-child:{wid}:{info['job_path']}")
                    joined.append({"wave": wid, "phase": info["phase"], "status": "UNRESOLVED_CHILD",
                                   "exit_code": job.get("exit_code"), "job_status": str(job.get("status") or "")})
                    append_event(run_dir, {"event": "parallel_unresolved_child", "wave": wid, "group": group,
                                           "job": str(info["job_path"]), "termination": job.get("timeout_termination")})
                    save_state(run_dir, state)
                    continue
                if wid in timeouts or job.get("timeout_reason"):
                    # Hung worker terminated under the lease: no result, no
                    # candidate, the channel (and so the group) is not complete.
                    timeouts[wid] = str(timeouts.get(wid) or job.get("timeout_reason"))
                    mark_phase_job_result(info["job_path"], status="WORKER_TIMEOUT", consumed=True)
                    rec = gstate.get("channels", {}).get(wid)
                    if isinstance(rec, dict):
                        rec.update({"status": "CONSUMED", "timeout_reason": timeouts[wid]})
                    entry["health"] = "stalled"
                    entry["current_action"] = f"Worker terminated: {timeouts[wid]}"
                    errors.append(f"worker-timeout:{wid}:{info['phase']}:{timeouts[wid]}")
                    completed[wid] = {"status": "WORKER_TIMEOUT", "reason": timeouts[wid]}
                    joined.append({"wave": wid, "phase": info["phase"], "status": "WORKER_TIMEOUT",
                                   "exit_code": job.get("exit_code"), "job_status": str(job.get("status") or "")})
                    append_event(run_dir, {"event": "parallel_join", "wave": wid, "group": group, "phase": info["phase"],
                                           "status": "WORKER_TIMEOUT"})
                    save_state(run_dir, state)
                    continue
                try:
                    machine, authoritative = channel_machine_result(job, output, info["phase"])
                    status = str(machine.get("status") or "FAIL").upper()
                except ValueError as exc:
                    machine = {}
                    status = "ORCHESTRATION_RECOVERY_REQUIRED"
                    errors.append(f"machine-result-recovery:{wid}:{exc}")
                plan_verdict = None
                if info["phase"] == "plan" and status in {"READY", "PASS"}:
                    # Contract version comes from config, never from this output.
                    plan_verdict = evaluate_plan_todo(authoritative, contract)
                    if plan_verdict["violation"]:
                        entry["todo_plan_state"] = TODO_PLAN_REJECTED
                        status = "ORCHESTRATION_RECOVERY_REQUIRED"
                        errors.append(f"todo-plan-contract-v{contract}:{wid}:{plan_verdict['error']}")
                        append_event(run_dir, {"event": "wave_todo_plan_rejected", "wave": wid,
                                               "contract": contract, "error": plan_verdict["error"]})
                mark_phase_job_result(info["job_path"], status=status, consumed=True)
                try:
                    rec = gstate.get("channels", {}).get(wid)
                    if isinstance(rec, dict):
                        rec["status"] = "CONSUMED"
                        rec["offset"] = int(info.get("offset") or 0)
                        rec["attempts"] = int(attempts.get(wid, 0)) + 1
                        save_state(run_dir, state)
                except Exception:
                    pass
                joined.append({"wave": wid, "phase": info["phase"], "status": status, "exit_code": exit_code, "job_status": job_status})
                append_event(run_dir, {"event": "parallel_join", "wave": wid, "group": group, "phase": info["phase"], "status": status})
                attempts[wid] = int(attempts.get(wid, 0)) + 1
                # Advance the channel's implement-stage phase machine.
                if info["phase"] == "plan" and status in {"READY", "PASS"}:
                    channel_phase[wid] = "run"
                    store_plan_todo(run_dir, entry, wid, plan_verdict or {})
                    progress_engine.complete_owned_todos(entry, "plan", info["instance"])
                    save_state(run_dir, state)
                elif info["phase"] in {"run", "repair"} and status in {"READY_FOR_AUDIT", "PASS", "READY"}:
                    # Candidate collection from the channel worktree.
                    try:
                        meta = wave_metadata(dict(members)[wid], profile)
                        surface = meta.get("write_surface") or []
                    except Exception:
                        surface = []
                    cand = workspace_engine.collect_candidate(
                        repo, worktrees[wid], wave_id=wid,
                        channel=engine_wave_channel_of(wid) if True else "",
                        group=group, base_head=frozen.get("base_head"),
                        base_content_identity=frozen.get("base_content_identity"),
                        write_surface=surface, test_result=status,
                        reserved_surfaces=engine_controller_owned_surfaces(profile),
                    )
                    # Controller-bound proof: which dispatch/tests vouch for this exact tree.
                    try:
                        _log_sha = hashlib.sha256(Path(info["log_path"]).read_bytes()).hexdigest()
                    except OSError:
                        _log_sha = None
                    workspace_engine.bind_candidate_evidence(cand, {
                        "phase": info["phase"], "phase_instance_id": info["instance"],
                        "job": str(info["job_path"]), "log_sha256": _log_sha, "result_status": status,
                        "test_todos": [{k: t.get(k) for k in (
                            "id", "title", "kind", "owner_phase", "status", "evidence", "completed_by",
                            "completion_source", "completion_phase", "completion_phase_instance_id",
                            "completion_event_id", "evidence_source", "evidence_phase",
                            "evidence_phase_instance_id", "evidence_event_id",
                        )}
                                       for t in entry.get("todos") or [] if str(t.get("kind")) in {"test", "retest"}],
                        "bound_at": utcnow()}, evidence_required=contract >= 2)
                    append_event(run_dir, {"event": "parallel_candidate", "wave": wid, "status": cand.get("status"),
                                           "candidate_identity": cand.get("candidate_identity"),
                                           "files": len(cand.get("changed_files") or [])})
                    if cand.get("status") != "READY_FOR_INTEGRATION":
                        errors.append(f"candidate-rejected:{wid}:{cand.get('write_surface_violations')}")
                        completed[wid] = {"status": "CANDIDATE_REJECTED", "candidate": cand}
                    else:
                        candidates[wid] = cand
                        workspace_engine.build_candidate_manifest(cand, run_dir, program)
                        progress_engine.complete_owned_todos(entry, info["phase"], info["instance"])
                        completed[wid] = {"status": status, "candidate": cand}
                    progress_engine.mark_meaningful_progress(entry, reason=f"parallel:{wid}:{status}")
                    save_state(run_dir, state)
                elif status in SEMANTIC_AUDIT_FINDING_STATUSES and (_route := channel_owner_route(
                        repo, run_dir, profile, wid, Path(dict(members)[wid]), info["phase"], int(info["seq"]),
                        status, machine, authoritative)):
                    # True owner is another Wave: stop dispatching, JOIN the open
                    # siblings (discarding their work), hand the route to the controller.
                    owner_pivot = _route
                    completed[wid] = {"status": "OWNER_ROUTED", "owner": _route["owner"]}
                    for other in pending_ids:
                        if other not in completed and other not in running:
                            completed[other] = {"status": "DEFERRED_FOR_OWNER_ROUTE"}
                    append_event(run_dir, {"event": "parallel_owner_route", "group": group, **_route,
                                           "open_siblings": sorted(running)})
                    save_state(run_dir, state)
                elif attempts[wid] >= 3:
                    errors.append(f"channel-stalled:{wid}:{info['phase']}:{status}")
                    completed[wid] = {"status": status}
                else:
                    # Semantic BLOCKED/REOPEN/FAIL -> repair; orchestration
                    # recovery re-runs the same phase (as the serial choose_after).
                    next_channel_phase = (info["phase"] if status in {"ORCHESTRATION_RECOVERY_REQUIRED", "MISSING_STATUS"}
                                          else "repair")
                    if next_channel_phase == "repair" and info["phase"] != "repair":
                        ensure_parallel_repair_todos(entry)
                    channel_phase[wid] = next_channel_phase
                    entry["no_progress_count"] = int(entry.get("no_progress_count", 0) or 0) + 1
                    entry["health"] = progress_engine.derive_wave_health(entry)
                    save_state(run_dir, state)
                    # Same bounded-recovery rule as the serial path: a channel
                    # that exhausts its no-progress budget stops the program.
                    _npcount = int(entry.get("no_progress_count", 0) or 0)
                    _nplimit = int(entry.get("no_progress_limit", 3) or 3)
                    if _npcount >= _nplimit:
                        # Signal only. The terminal decision belongs to the
                        # caller, exactly like unresolved_child / worker_timeout.
                        exhausted.append({"wave": str(wid), "count": _npcount, "limit": _nplimit})
                try:
                    rec = gstate.get("channels", {}).get(wid)
                    if isinstance(rec, dict):
                        rec["phase"] = str(channel_phase.get(wid, info["phase"]))
                        save_state(run_dir, state)
                except Exception:
                    pass
                save_state(run_dir, state)
    finally:
        # Guaranteed JOIN: every dispatched child is accounted for even on
        # exception/stall/terminal. Never leave orphans.
        try:
            still_open = []
            known_unresolved = {os.path.normcase(str(v)) for v in unresolved.values()}
            for item in dispatched:
                if os.path.normcase(str(item["job_path"])) in known_unresolved:
                    continue
                job = read_phase_job(item["job_path"])
                try:
                    alive = phase_job_is_alive(job, item.get("proc"))
                except Exception:
                    alive = True  # cannot prove it is gone: JOIN it
                # A live child is joined whatever its recorded status says.
                if alive or str(job.get("status") or "").upper() not in {"CONSUMED", "EXITED", "RESULT_READY"}:
                    still_open.append(item)
            if still_open:
                append_event(run_dir, {"event": "parallel_guaranteed_join", "group": group, "count": len(still_open)})
                try:
                    for done in join_phase_jobs(still_open, poll_seconds=min(1.0, poll_seconds), echo=False,
                                                max_wait_seconds=float(lease.get("max_phase_runtime_seconds") or 0) or None):
                        if done.get("unresolved"):
                            unresolved[str(done.get("wave_id") or "?")] = str(done["job_path"])
                            errors.append(f"unresolved-child:{done.get('wave_id')}:{done['job_path']}")
                except Exception as exc:
                    errors.append(f"guaranteed-join-failed:{exc}")
                    append_event(run_dir, {"event": "parallel_guaranteed_join_failed", "group": group, "detail": str(exc)[:500]})
                for item in still_open:
                    if os.path.normcase(str(item["job_path"])) in {os.path.normcase(v) for v in unresolved.values()}:
                        continue  # still possibly running: never marked consumed
                    try:
                        mark_phase_job_result(item["job_path"], status=str((read_phase_job(item["job_path"]).get("result_status")) or "FAIL"), consumed=True)
                    except Exception:
                        pass
        except Exception as exc:
            errors.append(f"guaranteed-join-accounting-failed:{exc}")
        save_state(run_dir, state)
    if owner_pivot:
        candidates = {}  # nothing from this frozen group attempt may be integrated
    return {"candidates": candidates, "errors": errors, "next_seq": seq, "joined": joined,
            "worktrees": {k: str(v) for k, v in worktrees.items()}, "timeouts": timeouts, "unresolved": unresolved,
            "owner_route": owner_pivot, "no_progress_exhausted": exhausted}


def observe_controller_provenance(repo: Path, profile: dict[str, Any], run_dir: Path, state: dict[str, Any],
                                  *, record: bool = False) -> bool:
    """Controller-owned provenance of main's uncommitted content (state.json).

    `record=True` right after this controller (or a worker it dispatched)
    changed content: the current identity + HEAD become the last known
    controller state. Otherwise it verifies nothing else changed main since.
    A clean tree always re-establishes the chain; any unexplained change
    breaks it until main is clean again. Returns provenance_chain_ok.
    """
    ident = implementation_identity(repo, profile)
    head = project_git_head(repo)
    if not workspace_engine.repository_dirty_files(repo):
        state.update({"provenance_chain_ok": True, "last_controller_identity": ident, "last_controller_head": head})
    elif record:
        state.update({"last_controller_identity": ident, "last_controller_head": head})
    elif (ident, head) != (state.get("last_controller_identity"), state.get("last_controller_head")):
        if state.get("provenance_chain_ok"):
            append_event(run_dir, {"event": "controller_provenance_broken", "reason": "main changed outside the controller"})
        state["provenance_chain_ok"] = False
    return bool(state.get("provenance_chain_ok"))


def dirt_is_controller_owned(repo: Path, profile: dict[str, Any], state: dict[str, Any]) -> bool:
    """Every uncommitted change in main came from this run's controller:
    chain established from a clean tree and unbroken, identity + HEAD equal
    to the last controller-recorded state."""
    if not state.get("provenance_chain_ok"):
        return False
    head = project_git_head(repo)
    return (implementation_identity(repo, profile), head) == (state.get("last_controller_identity"),
                                                               state.get("last_controller_head"))


def live_managed_workspaces(repo: Path) -> set[str]:
    """Workspaces of every managed job (any run/program) that may still be alive."""
    live: set[str] = set()
    for job_path in (repo / ".tmp" / "agent-runs").glob("*/*/*-job.json"):
        job = read_phase_job(job_path)
        if not job:
            continue
        if phase_job_liveness(job) == "dead" and not any(
                survivors_alive(job.get(k)) for k in ("timeout_termination", "join_timeout")):
            continue  # 'unverified' / undrained descendants count as alive: never delete under them
        where = job.get("workspace") or job.get("cwd")
        if where:
            live.add(os.path.normcase(os.path.abspath(str(where))))
    return live


def _workspace_in_use(path: Path, live: set[str]) -> bool:
    key = os.path.normcase(os.path.abspath(str(path)))
    return any(item == key or item.startswith(key + os.sep) for item in live)


def _remove_empty_dirs(*paths: Path) -> None:
    for path in paths:
        try:
            path.rmdir()
        except OSError:
            pass


def record_parallel_strategy(run_dir: Path, state: dict[str, Any], strategy: str, group: int | None,
                             reason: str | None = None) -> None:
    """The one place the parallel strategy is decided/recorded (state.json + event).

    `undetermined` until a multi-channel group is evaluated; `managed` when
    isolated workers run; `serial_fallback` only with a deterministic
    `fallback_reason`. An event is written only when the decision changes.
    """
    changed = state.get("parallel_strategy") != strategy or state.get("fallback_reason") != reason
    state["parallel_strategy"] = strategy
    if strategy == "serial_fallback":
        state["fallback_reason"] = str(reason or "unspecified")
    else:
        state.pop("fallback_reason", None)
    if changed:
        append_event(run_dir, {"event": "parallel_serial_fallback" if strategy == "serial_fallback" else "parallel_strategy_selected",
                               "group": group, "strategy": strategy, "reason": state.get("fallback_reason")})
    save_state(run_dir, state)


def cleanup_group_worktrees(repo: Path, run_dir: Path, state: dict[str, Any], group: int, reason: str) -> dict[str, Any]:
    """Remove a finished group's channel + integration worktrees (controller authority).

    Called only after run_parallel_group_implement returned (every dispatched
    child JOINed) and the integration/promotion or terminal outcome is
    recorded durably. A worktree a live managed job still uses is preserved.
    The outcome is recorded in state.json (parallel_groups.<g>.worktree_cleanup).
    """
    gstate = _parallel_group_state(state, group)
    root = workspace_engine.group_workspace_root(repo, run_dir.name, group)
    results: dict[str, Any] = {}
    if root.is_dir():
        live = live_managed_workspaces(repo)
        for child in sorted(p for p in root.iterdir() if p.is_dir()):
            if _workspace_in_use(child, live):
                results[child.name] = {"removed": False, "reason": "live-worker-preserved"}
                continue
            results[child.name] = workspace_engine.cleanup_completed_worktree(repo, child)
        _remove_empty_dirs(root, root.parent)
    frozen = gstate.get("frozen") if isinstance(gstate.get("frozen"), dict) else {}
    if frozen.get("base_ref") and not any(r.get("reason") == "live-worker-preserved" for r in results.values()):
        results["synthetic_base_ref_deleted"] = workspace_engine.delete_synthetic_base(repo, frozen.get("base_ref"))
    gstate["worktree_cleanup"] = {"reason": reason, "results": results, "at": utcnow()}
    append_event(run_dir, {"event": "parallel_worktree_cleanup", "group": group, "reason": reason, "results": results})
    save_state(run_dir, state)
    return results


def sweep_stale_managed_worktrees(repo: Path, profile: dict[str, Any], run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Resume-time cleanup of managed worktrees left by finished groups/runs.

    Preserved: this run's still-active group (reattach owns it), any run held
    by a live controller lock, and every worktree a possibly-alive managed job
    uses. Everything else under the managed root is removed and pruned.
    """
    root = workspace_engine.managed_worktree_root(repo)
    live = live_managed_workspaces(repo)
    live_runs = {m.group(1) for line in engine_live_controller_locks(repo, profile)
                 for m in [re.search(r"run_id=(\S+)", line)] if m}
    removed: dict[str, Any] = {}
    for run_root in sorted(p for p in (root.iterdir() if root.is_dir() else []) if p.is_dir()):
        for group_root in sorted(p for p in run_root.iterdir() if p.is_dir()):
            if run_root.name == run_dir.name:
                gstate = (state.get("parallel_groups") or {}).get(group_root.name.lstrip("W")) or {}
                if not (gstate.get("integrated") or gstate.get("failed")):
                    continue
            elif run_root.name in live_runs:
                continue
            for child in sorted(p for p in group_root.iterdir() if p.is_dir()):
                if _workspace_in_use(child, live):
                    continue
                removed[str(child.relative_to(root))] = workspace_engine.cleanup_completed_worktree(repo, child)
            _remove_empty_dirs(group_root)
        _remove_empty_dirs(run_root)
    # Synthetic base refs of finished groups/runs (the active group's is kept).
    for ref in workspace_engine.list_synthetic_bases(repo):
        parts = ref.split("/")
        run_name, gname = (parts[-2], parts[-1]) if len(parts) >= 2 else ("", "")
        if run_name == run_dir.name:
            gstate = (state.get("parallel_groups") or {}).get(gname.lstrip("W")) or {}
            if not (gstate.get("integrated") or gstate.get("failed")):
                continue
        elif run_name in live_runs:
            continue
        if (root / run_name / gname).exists():
            continue  # a preserved (live) worktree may still sit on it
        removed[ref] = {"removed": workspace_engine.delete_synthetic_base(repo, ref)}
    if removed:
        append_event(run_dir, {"event": "managed_worktree_sweep", "removed": removed})
    return removed


def integrate_parallel_candidates(
    *,
    repo: Path,
    profile: dict[str, Any],
    run_dir: Path,
    program: str,
    group: int,
    members: list[tuple[str, Path]],
    candidates: dict[str, dict[str, Any]],
    worktrees: dict[str, Path],
    frozen: dict[str, Any],
) -> dict[str, Any]:
    """Transactional safe integration (controller authority).

    Flow: candidates → integration worktree (deterministic channel order) →
    validate complete integrated filesystem (union surface + op validity +
    project hooks) → re-verify main base immediately before promote →
    transactional promote with backup + rollback → receipt.

    Main is never mutated before validation completes, and a failed
    promotion leaves main unchanged (fail closed).
    """
    ordered_ids = sorted([str(wid) for wid, _ in members], key=engine_wave_sort_key)
    ordered_cands = [candidates[wid] for wid in ordered_ids if wid in candidates]
    if len(ordered_cands) != len(ordered_ids):
        missing = [wid for wid in ordered_ids if wid not in candidates]
        return {"ok": False, "reason": f"missing-candidates:{','.join(missing)}"}
    # Only candidates collected READY from this group's frozen base may enter
    # integration: a pre-repair, rejected or other-base candidate is stale.
    for cand in ordered_cands:
        if cand.get("status") != "READY_FOR_INTEGRATION":
            return {"ok": False, "reason": f"candidate-not-ready:{cand.get('wave')}:{cand.get('status')}"}
        _evidence = workspace_engine.verify_candidate_evidence(cand, frozen)
        if _evidence:
            append_event(run_dir, {"event": "parallel_candidate_evidence_invalid", "group": group, "problems": _evidence})
            return {"ok": False, "reason": "candidate-evidence-invalid:" + ";".join(_evidence[:3])}
        for key in ("base_head", "base_content_identity"):
            if frozen.get(key) and cand.get(key) != frozen.get(key):
                append_event(run_dir, {"event": "parallel_candidate_stale", "group": group, "wave": cand.get("wave"), "field": key})
                return {"ok": False, "reason": f"candidate-stale-base:{cand.get('wave')}:{key}"}
    ok, reason = workspace_engine.verify_base_identity(
        repo, frozen, lambda r: implementation_identity(r, profile)
    )
    if not ok:
        append_event(run_dir, {"event": "parallel_stale_base", "group": group, "reason": reason})
        return {"ok": False, "reason": reason}
    integration, _integ_outcome = workspace_engine.ensure_integration_worktree(repo, run_dir.name, group, frozen.get("base_head"))
    if _integ_outcome == "recreated-stale":
        append_event(run_dir, {"event": "parallel_integration_recreated_stale", "group": group})
    actual_integ_head = workspace_engine.worktree_head(integration)
    if frozen.get("base_head") and actual_integ_head and actual_integ_head != frozen.get("base_head"):
        append_event(run_dir, {"event": "parallel_integration_stale_base", "group": group,
                               "expected": frozen.get("base_head"), "actual": actual_integ_head})
        return {"ok": False, "reason": f"integration-stale-base:{actual_integ_head}!={frozen.get('base_head')}"}
    receipt = workspace_engine.apply_candidates_to_integration(integration, ordered_cands, worktrees)
    if not receipt.get("ok"):
        append_event(run_dir, {"event": "parallel_integration_conflict", "group": group, "conflicts": receipt.get("conflicts")})
        return {"ok": False, "reason": "integration-conflict", "receipt": receipt}
    # Combined validation of the complete integrated filesystem.
    union_surface: list[str] = []
    for cand in ordered_cands:
        union_surface.extend(cand.get("write_surface") or [])
    tree_changes = workspace_engine.integration_tree_changes(integration, frozen.get("base_head"))
    reserved = engine_controller_owned_surfaces(profile)
    valid, problems = workspace_engine.validate_integrated_tree(tree_changes, union_surface, ordered_cands,
                                                                reserved_surfaces=reserved)
    if not valid:
        append_event(run_dir, {"event": "parallel_integration_invalid", "group": group, "problems": problems})
        return {"ok": False, "reason": "integration-invalid:" + ";".join(problems[:5]), "receipt": receipt,
                "tree_changes": tree_changes}
    parallel_cfg = profile.get("parallel") or {}
    hooks: list[str] = []
    for raw in [*(parallel_cfg.get("integration_validators") or []), *(parallel_cfg.get("focused_tests") or [])]:
        value = str(raw).strip()
        if value and value not in hooks:
            hooks.append(value)
    if hooks:
        hooks_ok, hook_problems = workspace_engine.run_integration_hooks(integration, hooks)
        append_event(run_dir, {"event": "parallel_integration_hooks", "group": group,
                               "hooks": [str(h) for h in hooks], "ok": hooks_ok, "problems": hook_problems})
        if not hooks_ok:
            return {"ok": False, "reason": "integration-hooks-failed:" + ";".join(hook_problems[:3]),
                    "receipt": receipt, "tree_changes": tree_changes}
    # Stale-base race: re-verify main immediately before promotion.
    ok, reason = workspace_engine.verify_base_identity(
        repo, frozen, lambda r: implementation_identity(r, profile)
    )
    if not ok:
        append_event(run_dir, {"event": "parallel_promote_stale_base", "group": group, "reason": reason})
        return {"ok": False, "reason": reason, "receipt": receipt, "tree_changes": tree_changes}
    backup_root = repo / ".tmp" / "integration-backup" / str(run_dir.name) / f"W{int(group)}"
    promoted = workspace_engine.transactional_promote(repo, integration, tree_changes, backup_root=backup_root, verify=True,
                                                      reserved_surfaces=reserved)
    append_event(run_dir, {"event": "parallel_promoted" if promoted.get("ok") else "parallel_promote_failed",
                           "group": group, "receipt": promoted})
    if not promoted.get("ok"):
        return {"ok": False, "reason": str(promoted.get("reason") or "promotion-failed"),
                "receipt": receipt, "tree_changes": tree_changes, "promotion": promoted}
    append_event(run_dir, {"event": "parallel_integrated", "group": group, "waves": ordered_ids})
    return {"ok": True, "receipt": receipt, "tree_changes": tree_changes,
            "promotion": promoted, "integration": str(integration)}




def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()




def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return ""




def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        # Windows refuses the replace while a reader (the follower) has the
        # target open; that is transient, so retry briefly instead of crashing.
        for attempt in range(40):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 39:
                    raise
                time.sleep(0.05)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


STATE_SCHEMA_VERSION = 3


def migrate_state(state: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible migration for state.json. Old runs stay resumable.

    v3 adds the durable per-Wave progress cursor (waves.<id>.progress_cursor)
    and the channel record log_path. Pre-v3 runs have no cursor: they resume
    from offset 0 and the seen_event_ids reducer drops already-applied events.
    """
    if not isinstance(state, dict):
        return state
    version = state.get("state_schema_version")
    try:
        version = int(version) if version is not None else 1
    except (TypeError, ValueError):
        version = 1
    if version < 2:
        state.setdefault("waves", {})
        state.setdefault("parallel_groups", {})
        state.setdefault("progress_contract_version", 1)
        state.setdefault("progress_epoch", int(state.get("progress_epoch", 0)))
        state.setdefault("fingerprints", {})
        state.setdefault("owner_stack", [])
        state.setdefault("recovery_counts", {})
    if not isinstance(state.get("waves"), dict):
        state["waves"] = {}
    if not isinstance(state.get("parallel_groups"), dict):
        state["parallel_groups"] = {}
    if version < 3:
        for entry in state["waves"].values():
            if isinstance(entry, dict):
                entry.setdefault("progress_cursor", None)
                if not isinstance(entry.get("seen_event_ids"), list):
                    entry["seen_event_ids"] = []
        for gstate in state["parallel_groups"].values():
            channels = gstate.get("channels") if isinstance(gstate, dict) else None
            for rec in (channels.values() if isinstance(channels, dict) else []):
                if isinstance(rec, dict):
                    rec.setdefault("log_path", None)
    # owner_phase is mandatory for every TODO (the reducer rejects events on
    # an ownerless TODO). Older states may hold ownerless controller items:
    # derive the owner deterministically from the kind (idempotent).
    for entry in state["waves"].values():
        for todo in (entry.get("todos") or []) if isinstance(entry, dict) else []:
            if isinstance(todo, dict) and not str(todo.get("owner_phase") or "").strip():
                todo["owner_phase"] = progress_engine.infer_owner_phase(str(todo.get("kind") or ""))
    # Effective contract v2: an entry written before v2 (or before this Wave's
    # contract was fixed at 2) carries no plan verdict. Record it as `pending`
    # deterministically so the PLAN gate fires before the next RUN/REPAIR
    # dispatch instead of reading the legacy default plan as accepted. The items
    # are kept; a validated PLAN block replaces them via store_plan_todo.
    _contract = effective_contract_version(state)
    for entry in state["waves"].values():
        if isinstance(entry, dict) and normalize_todo_plan_state(entry, _contract):
            entry["todo_plan_state_reason"] = "migrated-entry-without-validated-v2-plan"
    state["state_schema_version"] = STATE_SCHEMA_VERSION
    return state




def record_controller_error(run_dir: Path | None, category: str, detail: str) -> None:
    if run_dir is None:
        return
    path = run_dir / "controller-error-frequency.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    item = data.setdefault(category, {"count": 0, "first_seen": utcnow(), "last_seen": None, "examples": []})
    item["count"] += 1
    item["last_seen"] = utcnow()
    if detail and detail not in item["examples"]:
        item["examples"] = [*item["examples"], detail][-3:]
    write_json(path, data)




def parse_kv_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in read_text(path).splitlines():
        if ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        out[k.strip()] = v.strip()
    return out




def run_stream(args: list[str], cwd: Path, stdin_text: str | None = None, log_path: Path | None = None, on_line=None,
               abort_check=None) -> tuple[int, str]:
    """Stream a child's output. `abort_check()` (polled by a watchdog thread)
    returns a reason to terminate the child tree; the reason is then exposed as
    `run_stream.last_abort` for the caller (the controller lease)."""
    exe = shutil.which(args[0]) or args[0]
    actual = [exe, *args[1:]]
    if os.name == "nt" and Path(exe).suffix.lower() in {".cmd", ".bat"}:
        cmdline = subprocess.list2cmdline(actual)
        actual = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmdline]
    process_kwargs = subprocess_no_window_kwargs()
    if os.name != "nt":
        process_kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        actual,
        cwd=str(cwd),
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        # Keep background children hidden on Windows and give POSIX children
        # their own process group for reliable timeout cleanup.
        **process_kwargs,
    )
    if stdin_text is not None and proc.stdin:
        proc.stdin.write(stdin_text)
        proc.stdin.close()
    run_stream.last_abort = None
    run_stream.last_abort_outcome = None
    if abort_check is not None:
        import threading

        def _watch() -> None:
            while proc.poll() is None:
                reason = abort_check()
                if reason:
                    run_stream.last_abort = reason
                    # Identity is the live Popen handle itself (our direct child);
                    # the whole tree must be proven gone (terminal barrier).
                    run_stream.last_abort_outcome = terminate_process_tree(proc.pid, process_start_marker(proc.pid))
                    return
                time.sleep(0.5)
        threading.Thread(target=_watch, daemon=True).start()
    lines: list[str] = []
    log_fh = log_path.open("a", encoding="utf-8") if log_path else None
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            try:
                print(line, end="", flush=True)
            except UnicodeEncodeError as exc:
                record_controller_error(log_path.parent if log_path else None, "stdout_encoding", str(exc))
                print(line.encode("utf-8", "replace").decode("utf-8"), end="", flush=True)
            lines.append(line)
            if log_fh:
                log_fh.write(line)
                log_fh.flush()
            if on_line is not None:
                try:
                    on_line(line)
                except Exception:
                    pass
    finally:
        if log_fh:
            log_fh.close()
    code = proc.wait()
    if run_stream.last_abort:
        # The watchdog finishes its drain before the controller may classify.
        for _ in range(600):
            if run_stream.last_abort_outcome is not None:
                break
            time.sleep(0.05)
    return code, "".join(lines)




def git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        cp = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                            **subprocess_no_window_kwargs())
    except FileNotFoundError:
        return 127, "git-executable-unavailable"
    except OSError as exc:
        return 126, f"git-exec-error:{exc}"
    return cp.returncode, (cp.stdout + cp.stderr).strip()




def project_git_head(repo: Path) -> str | None:
    """Return the project-root Git HEAD only when this exact project owns it.

    Git discovery may find an ancestor repository for a nested non-Git project;
    Agent Core must not borrow that ancestor as this project's VCS authority.
    """
    cap = engine_git_capability(repo)
    return str(cap.get("head") or "").strip() or None if cap.get("has_head") else None



def detect_project(repo: Path) -> str:
    return str(load_profile(repo)["project_id"])




def _wave_targets_in_folder(repo: Path, project: str, state: str) -> list[tuple[str, Path]]:
    return engine_wave_targets_in_folder(repo, load_profile(repo), state)




def pending_targets(repo: Path, project: str) -> list[tuple[str, Path]]:
    return engine_pending_targets(repo, load_profile(repo))




def wave_location(repo: Path, project: str, target: str) -> tuple[Path | None, str | None]:
    return engine_wave_location(repo, load_profile(repo), target)




def canonical_from_wave(project: str, path: Path | None, repo: Path | None = None) -> str | None:
    if path is None:
        return None
    base = repo or path.resolve().parents[2]
    profile = load_profile(base)
    value = wave_metadata(path, profile).get("canonical_source")
    return str(value) if value else None




def current_target(repo: Path, project: str, override: str | None = None, *, allow_closed_owner_repair: bool = False) -> tuple[str | None, Path | None, str | None]:
    profile = load_profile(repo)
    if override:
        path, state = engine_wave_location(repo, profile, override)
        if path is None:
            raise RuntimeError(f"Routed owner {override} has no canonical Wave file in pending/done/blocked/postponed.")
        if state == "done" and not allow_closed_owner_repair:
            raise RuntimeError(f"CLOSED Wave {override} cannot become an active lifecycle target without explicit wave-reopen.")
        meta = wave_metadata(path, profile)
        return override, path, str(meta.get("canonical_source") or "") or None
    target, path = engine_current_target(repo, profile)
    if target is None or path is None:
        return None, None, None
    meta = wave_metadata(path, profile)
    return target, path, str(meta.get("canonical_source") or "") or None




def artifact_paths(repo: Path, project: str, target: str) -> tuple[Path | None, Path | None]:
    """Resolve canonical implementation/audit reports before historical fallbacks."""
    roots = [
        repo / "docs" / "wave-reports" / "v2" / "opencode",
        repo / "artifacts" / "opencode",
        repo / "artifacts",
        repo / "reports",
    ]
    candidates: list[Path] = []
    prefixes_cfg = (load_profile(repo).get("artifacts") or {}).get("report_prefixes")
    if isinstance(prefixes_cfg, list) and prefixes_cfg:
        prefixes = tuple(str(x).format(wave_id=target) for x in prefixes_cfg)
    else:
        prefixes = (f"{target}_", f"{target}-", f"WAVE_{target}_", f"WAVE-{target}-")
    upper_prefixes = tuple(x.upper() for x in prefixes)
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*.md"):
            name = p.name.upper()
            if name.startswith(upper_prefixes) and "REPORT" in name:
                candidates.append(p)
    audit = next((p for p in candidates if "AUDIT" in p.name.upper()), None)
    report = next((p for p in candidates if "AUDIT" not in p.name.upper()), None)
    return report, audit




def read_json_file(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except (FileNotFoundError, json.JSONDecodeError):
        return None




def routed_owner(findings_path: Path | None, current: str) -> str | None:
    if not findings_path or not findings_path.exists():
        return None
    data = read_json_file(findings_path)
    if not isinstance(data, dict):
        return None
    owners: list[str] = []
    for finding in data.get("findings", []) if isinstance(data.get("findings"), list) else []:
        if not isinstance(finding, dict) or finding.get("human_only"):
            continue
        owner = str(finding.get("execution_owner") or "").strip()
        # CLOSED owners are valid repair targets when a fresh current finding
        # explicitly routes to them. Lifecycle placement stays DONE; the
        # controller opens a bounded closed-owner repair transaction instead of
        # silently suppressing the route.
        if owner and owner != current and owner not in owners:
            owners.append(owner)
    def key(owner: str) -> tuple[int, str]:
        m = re.search(r"(\d+)", owner)
        return (int(m.group(1)) if m else 10**9, owner)
    return sorted(owners, key=key)[0] if owners else None




def progress_no_progress_key(target: str, phase: str, semantic: str, content_identity: str, progress_epoch: int) -> str:
    """Bound identical retries within one routing epoch, not across real owner progress.


    A true-owner transition (including a CLOSED-owner repair transaction) is
    semantic program progress even when implementation bytes are unchanged.
    Encoding the epoch prevents a legitimate repair -> return -> re-audit cycle
    from being mistaken for the same stuck operation.
    """
    scoped_semantic = f"{semantic}|progress_epoch={int(progress_epoch)}"
    return no_progress_key(target, phase, scoped_semantic, content_identity)


# Forward lifecycle edge per phase. A result is forward progress only when
# choose_after() routes it along this edge, so the bypass can never drift from
# the controller's real routing table.
FORWARD_LIFECYCLE_EDGE: dict[str, str] = {
    "plan": "run", "run": "audit", "repair": "audit", "audit": "close", "close": "reconcile",
}


def phase_result_bypasses_no_progress(phase: str, status: str) -> bool:
    """Successful forward handoffs must not consume identical-retry budget.

    `close:PASS` is authorization for the controller-owned pending -> done
    transition. Likewise `plan:READY/PASS`, `run/repair:READY_FOR_AUDIT`
    (and canonical READY/PASS aliases), and `audit:PASS` are forward
    lifecycle commits, not recovery attempts. Counting them as identical
    no-progress retries falsely stalls a clean Wave (for example plan READY
    followed by run READY_FOR_AUDIT followed by audit PASS with unchanged
    content identity reaching count 3 before close).

    Non-forward results (BLOCKED, REOPEN, FAIL, NO_PROGRESS, etc.) never
    bypass, so a real repair to audit to repair blocker loop with the same
    semantic and content identity still reaches identical_no_progress_cycle.
    Phase alone never bypasses: only (phase, status, choose_after(...)) on the
    forward edge.
    """
    phase = str(phase or "").lower()
    edge = FORWARD_LIFECYCLE_EDGE.get(phase)
    return edge is not None and choose_after(phase, {"status": str(status or "").upper(), "next_action": "none"}) == edge


EXPECTED_CANONICAL_SHA_RE = re.compile(r"(?im)^\*\*Expected canonical SHA-256:\*\*\s*`([0-9a-f]{64})`")
CANONICAL_SNAPSHOT_RE = re.compile(r"(?im)^\*\*Canonical source snapshot:\*\*\s*`([^`]+)`")


def canonical_content_sha256(data: bytes) -> str:
    """Canonical source fingerprint: SHA-256 of BOM-stripped, LF-normalized bytes.

    This equals the committed Git blob content, so a CRLF checkout
    (core.autocrlf=true) never reads as spec drift. Wave generation and
    validators must use this same algorithm.
    """
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def canonical_fingerprint_blocker(repo: Path, wave_path: Path) -> str | None:
    """Machine-enforced Stop Condition: spec fingerprint mismatch -> BLOCKED.

    Never left to worker prose. Waves that declare neither field are exempt.
    """
    text = read_text(wave_path)
    expected, snapshot = EXPECTED_CANONICAL_SHA_RE.search(text), CANONICAL_SNAPSHOT_RE.search(text)
    if not expected and not snapshot:
        return None
    if not expected or not snapshot:
        return "CANONICAL_FINGERPRINT_MISMATCH: Wave declares only one of snapshot / expected SHA-256"
    source = repo / snapshot.group(1)
    if not source.is_file():
        return f"CANONICAL_FINGERPRINT_MISMATCH: canonical snapshot missing: {snapshot.group(1)}"
    actual = canonical_content_sha256(source.read_bytes())
    if actual != expected.group(1).lower():
        return f"CANONICAL_FINGERPRINT_MISMATCH: {snapshot.group(1)} expected {expected.group(1).lower()} actual {actual}"
    return None




def bump_progress_epoch(state: dict[str, Any], reason: str | None = None) -> int:
    state["progress_epoch"] = int(state.get("progress_epoch", 0)) + 1
    if reason:
        state["progress_reason"] = reason
    return int(state["progress_epoch"])




def final_repair_owner(repo: Path, profile: dict[str, Any], failed_wave: str | None, state: dict[str, Any]) -> str | None:
    """Resolve a repository-owned final-validation failure back into the Wave graph."""
    if failed_wave:
        direct, _ = engine_wave_location(repo, profile, str(failed_wave))
        if direct is not None:
            return str(failed_wave)
        needle = re.search(r"(\d+)", str(failed_wave))
        if needle:
            canonical_num = needle.group(1)
            candidates: list[tuple[int, str]] = []
            for state_name in ("pending", "blocked", "postponed", "done"):
                for target, wave_path in engine_wave_targets_in_folder(repo, profile, state_name):
                    meta = wave_metadata(wave_path, profile)
                    source = str(meta.get("canonical_source") or "")
                    sm = re.search(r"(\d+)", source)
                    if sm and sm.group(1) == canonical_num:
                        # Aggregate/exit owner first, then deterministic numeric order.
                        rank = 0 if bool(meta.get("aggregate_close_owner")) else 1
                        candidates.append((rank, str(target)))
            if candidates:
                candidates.sort(key=lambda item: (item[0], int(re.search(r"(\d+)", item[1]).group(1)) if re.search(r"(\d+)", item[1]) else 10**9, item[1]))
                return candidates[0][1]
    last = str(state.get("last_closed_wave") or "").strip()
    if last and engine_wave_location(repo, profile, last)[0] is not None:
        return last
    done = engine_wave_targets_in_folder(repo, profile, "done")
    return str(done[-1][0]) if done else None




def effective_audit_status(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    text = read_text(path)
    lifecycle = list(LIFECYCLE_RE.finditer(text))
    if lifecycle:
        return lifecycle[-1].group(2).upper()
    if re.search(r"(?:Decision|Auditor decision):\s*PASS", text, re.I):
        return "PASS"
    plain = list(re.finditer(r"(?im)^\s*(?:\*\*)?Status:(?:\*\*)?\s*`?([A-Z_]+)`?\s*$", text))
    if plain:
        value = plain[-1].group(1).upper()
        if value in {"READY_FOR_AUDIT", "PENDING_INDEPENDENT_AUDIT"}:
            return "READY_FOR_AUDIT"
        if value in {"PASS", "BLOCKED", "REOPEN", "FAIL"}:
            return value
    return None




def audit_receipt_valid(repo: Path, profile: dict[str, Any], target: str,
                        state: dict[str, Any], content_identity: str) -> bool:
    """Accept only the controller's fresh, content-bound audit receipt.


    Reports are append-only human context.  The normalized result written by
    this controller is the close handoff authority.
    """
    if str(state.get("audit_status", "")).upper() != "PASS":
        return False
    if str(state.get("tested_wave", "")).upper() != str(target).upper():
        return False
    if state.get("tested_content_identity") != content_identity:
        return False
    result_path = state.get("audit_result_path")
    if not isinstance(result_path, str) or not result_path.strip():
        return False
    path = repo / result_path
    result = read_json_file(path)
    if not isinstance(result, dict) or str(result.get("status", "")).upper() != "PASS":
        return False
    cap = engine_git_capability(repo)
    recorded_head = str(state.get("audit_candidate_sha", "") or "").strip()
    if cap.get("has_head"):
        return bool(recorded_head) and recorded_head == str(cap.get("head") or "")
    # No Git/HEAD: the fresh normalized PASS + tested content identity above is sufficient.
    return not recorded_head




def recover_allowlisted_audit_receipt(repo: Path, run_dir: Path, profile: dict[str, Any],
                                      target: str, content_identity: str) -> dict[str, Any] | None:
    """Recover a real PASS when only allowlisted closeout files changed.


    This is a restart/handoff recovery path, not a report parser: it consumes
    normalized audit receipts and requires the candidate-to-HEAD diff to be
    entirely profile-allowlisted.
    """
    manifest = read_json_file(repo / f"artifacts/wave_{target}/WAVE_{target}_EVIDENCE_MANIFEST.json")
    candidate = str((manifest or {}).get("candidate_sha", "")).strip()
    head = project_git_head(repo)
    if not candidate or not head or candidate == head:
        return None
    code, diff = git(repo, "diff", "--name-only", f"{candidate}..{head}")
    if code != 0:
        return None
    allowed = profile.get("evidence", {}).get("allowed_closeout_only_paths", [])
    if any(not any(str(path).replace("\\", "/").startswith(str(prefix).rstrip("/") + "/")
                   or str(path).replace("\\", "/") == str(prefix).rstrip("/")
                   for prefix in allowed) for path in diff.splitlines() if path.strip()):
        return None
    receipts = sorted(run_dir.glob(f"*-{target}-audit-normalized.json"), reverse=True)
    for path in receipts:
        result = read_json_file(path)
        if isinstance(result, dict) and str(result.get("status", "")).upper() == "PASS":
            return {"audit_status": "PASS", "tested_wave": target,
                    "tested_content_identity": content_identity,
                    "audit_result_path": str(path.relative_to(repo)),
                    "audit_candidate_sha": head, "audit_passed_at": utcnow()}
    return None




def infer_reconcile_phase(repo: Path, project: str, target: str) -> str:
    report, audit = artifact_paths(repo, project, target)
    audit_status = effective_audit_status(audit)
    report_status = effective_audit_status(report)
    status = audit_status or report_status
    if status == "READY_FOR_AUDIT":
        return "audit"
    if status == "PASS":
        _path, state = wave_location(repo, project, target)
        # A historical PASS on a still-pending Wave may be bound to an older
        # candidate/dependency state. Re-audit it; a same-run audit PASS will
        # transition directly to close without another reconcile.
        return "reconcile" if state == "done" else "audit"
    if status in {"BLOCKED", "REOPEN", "FAIL"}:
        return "repair"
    if report and report.exists():
        return "run"
    return "plan"


def append_event(run_dir: Path, event: dict[str, Any]) -> None:
    event = {"utc": utcnow(), **event}
    with (run_dir / "events.ndjson").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")




def save_state(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utcnow()
    write_json(run_dir / "state.json", state)




def self_heal(repo: Path) -> None:
    script = repo / ".agents" / "repair-wave-skills.ps1"
    if not script.exists():
        return
    print("[program] Codex skill self-heal")
    code, output = run_stream([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)
    ], repo)
    if code != 0 or "CODEX_SKILL_HEALTH=PASS" not in output:
        raise RuntimeError("repair-wave-skills.ps1 did not reach CODEX_SKILL_HEALTH=PASS")




def validate_orchestration(repo: Path) -> None:
    path = repo / ".opencode" / "scripts" / "validate-wave-orchestration.py"
    if not path.exists():
        return
    print("[program] orchestration validator")
    cp = subprocess.run([sys.executable, str(path)], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
                        **subprocess_no_window_kwargs())
    print(cp.stdout, end="")
    if cp.stderr:
        print(cp.stderr, file=sys.stderr, end="")
    if cp.returncode != 0:
        raise RuntimeError("validate-wave-orchestration.py failed")




def validate_wave_authoring(repo: Path) -> list[str]:
    """Run the standalone authoring validator as the runtime pre-dispatch gate.

    Delegating to the validator gives runtime exactly the same semantics for
    filename/frontmatter identity, global ownership and shared parallel-group
    invariants without maintaining a second implementation.
    """
    here = Path(__file__).resolve()
    candidates = [
        repo / ".opencode" / "scripts" / "validate-wave-authoring.py",
        here.parent.parent / "validators" / "validate-wave-authoring.py",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return ["authoring-validator-missing"]
    cp = subprocess.run([sys.executable, str(path)], cwd=str(repo), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", **subprocess_no_window_kwargs())
    if cp.returncode == 0:
        return []
    detail = [line.strip()[6:] for line in cp.stdout.splitlines() if line.startswith("ERROR ")]
    if not detail:
        tail = (cp.stdout + "\n" + cp.stderr).strip().splitlines()[-5:]
        detail = ["authoring-validator-failed:" + " | ".join(tail)]
    return detail


def phase_schema(run_dir: Path) -> Path:
    p = run_dir / "phase-result.schema.json"
    if not p.exists():
        write_json(p, RESULT_SCHEMA)
    return p




def build_phase_prompt(repo: Path, project: str, target: str, wave_path: Path, phase: str,
                       canonical: str | None, findings_path: Path | None, no_progress: bool,
                       audit_receipt: dict[str, Any] | None = None,
                       content_identity: str = "unknown",
                       phase_instance_id: str | None = None,
                       progress_contract_version: int = 1) -> str:
    finding_note = ""
    if findings_path and findings_path.exists():
        finding_note = f"\nCurrent routed findings are in: {findings_path.relative_to(repo)}. Read them before acting."
    deeper = ""
    if no_progress:
        deeper = "\nThe previous blocker fingerprint repeated. You MUST change/deepen the diagnosis before acting; identical reruns are not progress."
    common = f"""
You are one deterministic lifecycle worker controlled by run-wave-program.py.
Repository: {repo}
Project: {project}
Target Wave: {target}
Canonical Wave file: {wave_path.relative_to(repo)}
Canonical source wave: {canonical or 'n/a'}
Phase: {phase}


Read AGENTS.md, .agents/skills/ac-wave-core/SKILL.md, the target Wave, repository rules, and only the authority/evidence files needed for THIS phase. Preserve unrelated user changes. Never ask the user whether to continue. Never schedule another Wave. Return only the structured result required by the provided output schema.{finding_note}{deeper}


On Windows, canonical text SHA-256 comparisons MUST use LF-normalized UTF-8 bytes; raw CRLF hashes are not evidence of a spec mismatch.

Backend-neutral progress contract (same semantics as the OpenCode bridge; native plan/TODO tools are never authority, state.json is):
- progress_contract_version: {int(progress_contract_version)} (fixed by the controller before this dispatch).
- PLAN emits one structured TODO block before the final schema result: a line containing only AC_WAVE_TODO_PLAN_BEGIN, then one JSON list of items like {{"id":"T01","title":"Inspect existing implementation","kind":"task","owner_phase":"run","status":"pending"}}, then a line containing only AC_WAVE_TODO_PLAN_END. Every item needs id, title, kind (task|test|audit|repair|retest|close|evidence) and owner_phase (plan|run|audit|repair|close); test/retest items belong to run or repair. These are declarations only: emit no fields beyond id/title/kind/owner_phase and optional status="pending"; never emit completion, provenance, detail, or evidence fields. {"Under contract 2 the block is MANDATORY: a missing, malformed or invalid block fails the PLAN (orchestration recovery)." if int(progress_contract_version) >= 2 else "Under contract 1 (legacy) the block is optional; omit it rather than emit an invalid one."}
- RUN/REPAIR emit live progress as standalone lines, one JSON object per line, prefixed with AC_WAVE_PROGRESS_EVENT: and shaped like {{"version":1,"event_id":"<unique>","phase_instance_id":"{phase_instance_id or '<from controller context>'}","wave_id":"<Wave>","phase":"<run|repair>","todo_id":"<known T..>","operation":"start|update|complete|block|cancel|note","action":"<concrete current action>","detail":"<detail>","evidence":["<test command and result>"]}} (this sentence is a template, not an event).
  start/update/complete/block/cancel require a known todo_id owned by this phase; generic actions such as "Worker running" are never progress. Only this marker updates the controller TODO view; arbitrary prose never becomes authority.
- AUDIT is read-only and has no TODO manifest authority. CLOSE reports progress only; the controller performs the lifecycle move.
"""
    if phase == "reconcile":
        return common + """
READ-ONLY. Reconcile live Git/pending/done/report/audit/evidence truth for this target and choose the next lifecycle action. Do not edit files. A repository-owned BLOCKED/REOPEN/validator-red state must choose repair, not none. COMPLETE is valid only when this target is already truthfully closed/done. HUMAN_DEFERRED requires concrete unavailable human/external authority.
"""
    if phase == "plan":
        return common + """
READ-ONLY planning phase. Produce/refresh the Wave plan if the repository contract uses one, resolve exact owners/dependencies/tests/evidence, and return READY/PASS when execution can proceed. Repository-owned uncertainty is not human deferred.
"""
    if phase == "run":
        return common + """
EXECUTE the target Wave's owned implementation/evidence work now. Run focused validation and update its canonical report/evidence as required. Do not merely summarize. Finish READY_FOR_AUDIT when the candidate is ready for a fresh independent audit; otherwise return REOPEN/BLOCKED with concrete findings.
"""
    if phase == "repair":
        return common + """
THIS IS A NON-TERMINAL REPAIR PHASE. Consume the current audit/validator/findings, resolve true ownership, and actually perform at least one concrete repository-owned repair/evidence-generation/routing action. For an aggregate validator can_close=false, enumerate failing IDs/reasons and repair the current/declared owner; do not stop after writing a status report. Run focused validation and refresh invalidated evidence. Set repair_hypothesis to a concise stable diagnosis ID; reuse it while testing the same diagnosis and change it only when the repair hypothesis materially changes. Finish READY_FOR_AUDIT when ready for a fresh audit. HUMAN_DEFERRED is allowed only for genuine unavailable authority.
"""
    if phase == "audit":
        return common + f"""
FRESH INDEPENDENT AUDIT. Do not edit product, tests, lifecycle, reports, or evidence. Re-read the frozen/current candidate and required proof. Run read-only validation where possible. Return PASS only if this target can proceed to close under its own contract; otherwise REOPEN/BLOCKED with concrete finding IDs and owners. Do not repair.


Controller identity handoff: current implementation content identity is {content_identity}. The profile's allowed closeout-only paths are authoritative; controller/profile/regression-test changes on the candidate-to-HEAD diff do not invalidate the tested Wave implementation. Existing evidence/report working-tree edits are Wave closeout artifacts and must be judged by the canonical validator, not treated as product-content drift. A prior executed GUI probe path under .tmp is disposable runtime scratch, not required persisted evidence; the manifest, exact test receipt, and validator are the authoritative proof.
"""
    if phase == "close":
        receipt = audit_receipt or {}
        receipt_note = f"""
Controller audit gate (authoritative; do not infer this from report markdown):
- fresh independent audit: {receipt.get('audit_status', 'MISSING')}
- tested Wave: {receipt.get('tested_wave', 'MISSING')}
- tested content identity: {receipt.get('tested_content_identity', 'MISSING')}
- audit candidate SHA: {receipt.get('audit_candidate_sha', 'MISSING')}
- normalized audit result: {receipt.get('audit_result_path', 'MISSING')}
Historical READY_FOR_AUDIT/BLOCKED/REOPEN prose in retained reports is context only and must not reopen this Wave when the controller audit gate is valid.
"""
        return common + receipt_note + """
SERIAL CLOSEOUT phase. The controller has already established the fresh audit PASS above. Do not return READY_FOR_AUDIT or reopen because of retained report prose or a disposable .tmp probe path. Run the closeout validator; when it is green, return PASS so the controller can perform the authorized close transaction. If a validator is red or evidence is substantively missing, return REOPEN/BLOCKED with concrete findings; do not fake PASS.
"""
    raise ValueError(phase)




def codex_exec_help() -> str:
    exe = shutil.which("codex")
    if not exe:
        raise RuntimeError("Codex CLI not found on PATH")
    cp = subprocess.run(
        [exe, "exec", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **subprocess_no_window_kwargs(),
    )
    blob = (cp.stdout or "") + "\n" + (cp.stderr or "")
    if cp.returncode != 0:
        raise RuntimeError(f"codex exec --help failed with exit {cp.returncode}: {blob[-2000:]}")
    return blob




# Every front end Agent Core supports. A front end that is not declared here is
# not a supported program, and the controller refuses to start rather than
# silently applying one front end's rules to another.
BACKENDS = ("codex", "claude", "opencode")

# Front ends whose CLI returns the machine result as schema JSON on stdout.
# This is a transport property, not a behavioural one: such a front end is read
# through the same validated result path so its decisions stay identical.
SCHEMA_JSON_BACKENDS = ("codex", "claude")


def _cli_help(binary: str, *args: str) -> str:
    exe = shutil.which(binary)
    if not exe:
        return ""
    try:
        cp = subprocess.run(
            [exe, *args, "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            **subprocess_no_window_kwargs(),
        )
    except OSError:
        return ""
    return (cp.stdout or "") + "\n" + (cp.stderr or "")


def claude_exec_args(run_dir: Path, sandbox: str, model: str | None) -> list[str]:
    """Build the Claude Code command from the installed CLI's actual option surface."""
    help_text = _cli_help("claude")
    exe = shutil.which("claude") or "claude"
    args = [exe, "-p"]
    if "--output-format" in help_text:
        args += ["--output-format", "json"]
    if "--permission-mode" in help_text:
        # Same intent as the Codex sandbox: read-only phases must not write.
        args += ["--permission-mode", "plan" if sandbox == "read-only" else "acceptEdits"]
    if model and "--model" in help_text:
        args += ["--model", model]
    if "--add-dir" in help_text and run_dir is not None:
        args += ["--add-dir", str(run_dir)]
    return args


def codex_exec_args(run_dir: Path, sandbox: str, model: str | None) -> list[str]:
    """Build the Codex exec command from the installed CLI's actual option surface."""
    help_text = codex_exec_help()
    exe = shutil.which("codex") or "codex"
    args = [exe, "exec"]


    if "--ephemeral" in help_text:
        args.append("--ephemeral")
    if "--sandbox" in help_text:
        args += ["--sandbox", sandbox]
    if "--ask-for-approval" in help_text:
        args += ["--ask-for-approval", "never"]


    required = ["--output-schema", "--output-last-message"]
    missing = [flag for flag in required if flag not in help_text]
    if missing:
        raise RuntimeError(
            "Installed Codex CLI lacks required non-interactive structured-output flags: "
            + ", ".join(missing)
        )
    args += [
        "--output-schema", str(phase_schema(run_dir)),
        "--output-last-message", str(run_dir / "__RESULT_PATH_PLACEHOLDER__"),
    ]


    if model:
        if "--model" not in help_text and " -m" not in help_text:
            raise RuntimeError("A model override was requested but this Codex CLI does not advertise --model")
        args += ["--model", model]
    return args


# How a front end's own CLI is invoked. This is the only place a front end name
# may influence what runs; every decision above it stays backend-neutral.
BACKEND_TRANSPORTS = {
    "codex": codex_exec_args,
    "claude": claude_exec_args,
}


def codex_exec(repo: Path, run_dir: Path, project: str, target: str, wave_path: Path, phase: str,
               canonical: str | None, findings_path: Path | None, model: str | None,
               no_progress: bool, seq: int, state: dict[str, Any] | None = None) -> dict[str, Any]:
    result_path = run_dir / f"{seq:04d}-{target}-{phase}-result.json"
    log_path = run_dir / f"{seq:04d}-{target}-{phase}.log"
    prompt_path = run_dir / f"{seq:04d}-{target}-{phase}.prompt.md"
    prompt = build_phase_prompt(repo, project, target, wave_path, phase, canonical, findings_path, no_progress,
                                state if phase == "close" else None,
                                state.get("content_identity", "unknown") if state else "unknown",
                                phase_instance_id=new_phase_instance_id(run_dir.name, seq, target, phase),
                                progress_contract_version=int((state or {}).get("progress_contract_version") or 1))
    prompt_path.write_text(prompt, encoding="utf-8")
    sandbox = "read-only" if phase in {"reconcile", "plan", "audit"} else "workspace-write"


    try:
        args = codex_exec_args(run_dir, sandbox, model)
    except RuntimeError as exc:
        return {
            "status": "BLOCKED",
            "summary": "Codex CLI compatibility repair required",
            "findings": [str(exc)],
            "changed_files": [],
            "next_action": "repair",
        }


    placeholder = str(run_dir / "__RESULT_PATH_PLACEHOLDER__")
    args = [str(result_path) if x == placeholder else x for x in args]
    args += ["-"]


    attempt = 0
    # Controller-owned progress entry and semantic phase instance for live TODO.
    _entry = None
    _instance = None
    if isinstance(state, dict):
        try:
            _entry = ensure_wave_entry(state, target, None)
            _entry["phase"] = str(phase).lower()
            _instance = new_phase_instance_id(run_dir.name, seq, target, phase)
            _entry["phase_instance_id"] = _instance
            progress_engine.bind_phase_todo(_entry, phase, _instance)
            _entry["dispatch_seq"] = int(_entry.get("dispatch_seq", 0) or 0) + 1
            if str(phase).lower() == "audit":
                progress_engine.record_audit_attempt(_entry)
            if str(phase).lower() == "repair":
                progress_engine.record_repair_attempt(_entry)
            if not str(_entry.get("current_action") or "").strip():
                _entry["current_action"] = controller_fallback_action(phase, target)
            save_state(run_dir, state)
        except Exception:
            _entry, _instance = None, None
    while attempt < AC_MAX_TRANSPORT_ATTEMPTS:
        attempt += 1
        append_event(run_dir, {"event": "codex_phase_start", "phase": phase, "target": target, "attempt": attempt,
                               "phase_instance_id": _instance})
        def _on_line(_line: str, _entry=_entry, _instance=_instance) -> None:
            if _entry is None or progress_engine.parse_progress_event_line(_line) is None:
                return
            outcome = drain_progress_deltas(_entry, _line, expected_phase=str(_entry.get("phase") or phase),
                                            expected_phase_instance_id=_instance)
            if outcome["applied"] or outcome["rejected"]:
                append_event(run_dir, {"event": "wave_progress", "wave": target, "applied": outcome["applied"], "rejected": outcome["rejected"], "details": outcome.get("details") or []})
                save_state(run_dir, state if isinstance(state, dict) else {"waves": {}})

        _lease = (state or {}).get("managed_job_lease") if isinstance(state, dict) else None
        _job = {"started_at": utcnow()}
        code, output = run_stream(args, repo, stdin_text=prompt, log_path=log_path, on_line=_on_line,
                                  abort_check=(lambda: lease_violation(_job, _entry, _lease)) if _lease else None)
        append_event(run_dir, {"event": "codex_phase_exit", "phase": phase, "target": target, "attempt": attempt, "exit": code})
        if getattr(run_stream, "last_abort", None):
            _reason = str(run_stream.last_abort)
            _outcome = getattr(run_stream, "last_abort_outcome", None) or {}
            if not _outcome.get("terminated"):
                append_event(run_dir, {"event": "managed_worker_unresolved", "wave": target, "phase": phase,
                                       "backend": "codex", "termination": _outcome})
                return {"status": "ORCHESTRATION_RECOVERY_REQUIRED", "unresolved_child": f"codex:{target}:{phase}",
                        "summary": f"codex worker tree not drained after {_reason}", "findings": [f"unresolved_managed_child:{_outcome}"],
                        "changed_files": [], "next_action": "reconcile"}
            append_event(run_dir, {"event": "managed_worker_timeout", "wave": target, "phase": phase, "reason": _reason,
                                   "backend": "codex"})
            return {"status": "ORCHESTRATION_RECOVERY_REQUIRED", "worker_timeout": _reason,
                    "summary": f"codex worker terminated: {_reason}", "findings": [f"managed_worker_timeout:{_reason}"],
                    "changed_files": [], "next_action": "reconcile", "phase_log_path": str(log_path.relative_to(repo))}
        if code == 0 and result_path.exists():
            try:
                parsed = json.loads(read_text(result_path))
                if isinstance(parsed, dict):
                    # PLAN TODO blocks and backend-neutral progress evidence live
                    # in the durable phase log, exactly like OpenCode bridges.
                    # Binding the log path here lets the controller reducer use
                    # one PLAN contract for Codex and OpenCode.
                    parsed.setdefault("phase_log_path", str(log_path.relative_to(repo)))
                return parsed
            except json.JSONDecodeError:
                pass
        blob = output + "\n" + read_text(result_path)
        if HUMAN_RE.search(blob):
            return {"status": "HUMAN_DEFERRED", "summary": blob[-2000:], "findings": [blob[-1200:]], "changed_files": [], "next_action": "none"}
        if CONFIG_RE.search(blob):
            return {"status": "BLOCKED", "summary": "Codex exec/config incompatibility", "findings": [blob[-2000:]], "changed_files": [], "next_action": "repair"}
        delay = min(60, 2 ** min(attempt, 6))
        if not TRANSIENT_RE.search(blob) and attempt >= 3:
            delay = 60
        print(f"[program] codex exec retry phase={phase} attempt={attempt}/{AC_MAX_TRANSPORT_ATTEMPTS} delay={delay}s", flush=True)
        time.sleep(delay)
    return {"status":"ORCHESTRATION_RECOVERY_REQUIRED","summary":"Codex transport retries exhausted",
            "findings":[f"phase={phase} target={target} retries={AC_MAX_TRANSPORT_ATTEMPTS}"],
            "changed_files":[],"next_action":"reconcile"}




ROLE_BY_PHASE = {"doctor": "controller", "reopen": "controller", "plan": "planner", "run": "executor",
                 "resume": "executor", "repair": "executor", "audit": "auditor", "close": "closer"}


def configured_model_candidates(repo: Path, family: str, phase: str) -> list[str]:
    """Read the canonical family/phase model chain; first available entry is primary."""
    paths = (repo / ".opencode/protocol/AC_MODELS.json", repo / "AC_MODELS.json")
    path = next((candidate for candidate in paths if candidate.is_file()), None)
    if path is None:
        raise RuntimeError("missing AC model catalog (.opencode/protocol/AC_MODELS.json)")
    try:
        catalog = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid AC model catalog: {path}: {exc}") from exc
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        raise RuntimeError(f"unsupported AC model catalog schema: {path}")
    family_routes = (catalog.get("models") or {}).get(family)
    candidates = family_routes.get(phase, family_routes.get("default")) if isinstance(family_routes, dict) else None
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError(f"missing non-empty model candidate list for {family}/{phase} in {path}")
    if any(not isinstance(model, str) or not re.fullmatch(r"[^\s#]+/[^\s#]+(?:#[^\s#]+)?", model) for model in candidates):
        raise RuntimeError(f"invalid model identifier in {family}/{phase} in {path}")
    if len(set(candidates)) != len(candidates):
        raise RuntimeError(f"duplicate model candidate in {family}/{phase} in {path}")
    return candidates


def program_family(program: str) -> str | None:
    for family in ("luna-openai", "opencode", "hybrid"):
        if program.startswith(f"ac-wave-{family}-"):
            return family
    return None


def split_model_thinking(model: str | None) -> tuple[str, str]:
    """`provider/model#variant` -> (model, variant); no variant is backend-default, never guessed."""
    if not model:
        return "unknown", "unknown"
    base, _, variant = str(model).partition("#")
    return base.strip() or "unknown", variant.strip() or "backend-default"


def resolve_phase_route(repo: Path, program: str, phase: str, backend: str = "opencode",
                        codex_model: str | None = None) -> dict[str, str]:
    """Requested (configured) route for a phase dispatch, from structured config only."""
    role = ROLE_BY_PHASE.get(phase, "unknown")
    if backend == "codex":
        model, thinking = split_model_thinking(codex_model)
        return {"role": role, "backend": "codex", "family": "codex", "agent": "codex-exec",
                "model": model, "thinking": thinking}
    family = program_family(program) or "unknown"
    candidates = configured_model_candidates(repo, family, phase)
    model, thinking = split_model_thinking(candidates[0])
    return {"role": role, "backend": "opencode", "family": family, "agent": f"ac-wave-{family}-{role}",
            "model": model, "thinking": thinking}


def route_divergence(requested: dict[str, str], record: dict[str, Any] | None) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Effective route from the launcher's dispatch record plus visible fallback/override notices."""
    if not isinstance(record, dict):
        return {**requested, "model": "unknown", "thinking": "unknown"}, [
            {"event": "MODEL_FALLBACK", "requested": requested["model"], "effective": "unknown",
             "reason": "launcher dispatch record missing"}]
    effective = {**requested, "model": str(record.get("effective_model") or "unknown"),
                 "thinking": str(record.get("effective_thinking") or "unknown")}
    notices = []
    if effective["model"] != requested["model"]:
        notices.append({"event": "MODEL_FALLBACK", "requested": requested["model"], "effective": effective["model"],
                        "reason": str(record.get("reason") or "launcher selected a different model")})
    if effective["thinking"] != requested["thinking"]:
        notices.append({"event": "THINKING_OVERRIDE", "requested": requested["thinking"], "effective": effective["thinking"],
                        "reason": str(record.get("reason") or "launcher selected a different thinking level")})
    return effective, notices


def format_route(route: dict[str, str]) -> str:
    return f"role={route['role']} | backend={route['backend']} | model={route['model']} | thinking={route['thinking']}"


def print_program_routing(repo: Path, program: str, backend: str, codex_model: str | None) -> None:
    print(f"[routing] program={program} backend={backend}", flush=True)
    for phase in ("doctor", "reopen", "plan", "run", "resume", "repair", "audit", "close"):
        route = resolve_phase_route(repo, program, phase, backend, codex_model)
        print(f"[routing] {route['role']:<10} | agent={route['agent']} | model={route['model']} | thinking={route['thinking']}", flush=True)


def models_used_lines(history: list[dict[str, Any]]) -> list[str]:
    counts: dict[tuple[str, str, str, bool], int] = {}
    for item in history or []:
        key = (str(item.get("role")), str(item.get("model")), str(item.get("thinking")), bool(item.get("fallback")))
        counts[key] = counts.get(key, 0) + 1
    return [f"[models-used] {role}: {model} / thinking={thinking}: {n} dispatch{'es' if n != 1 else ''}{' (fallback)' if fb else ''}"
            for (role, model, thinking, fb), n in sorted(counts.items())]


def serial_job_is_current(job: dict[str, Any], *, target: str, phase: str, program: str,
                          run_id: str, phase_instance_id: str | None) -> bool:
    """Serial reattach identity: same Wave/phase/program AND same run + phase instance."""
    if not job_matches(job, target=target, phase=phase, program=program):
        return False
    return not phase_job_identity_mismatches(job, {"run_id": run_id, "phase_instance_id": phase_instance_id})


def settle_foreign_phase_job(repo: Path, run_dir: Path, job_path: Path, reason: str) -> bool:
    """Fail-closed handling of a managed child that is not the current instance.

    It is never adopted as authority and never left orphaned: while it may
    still be alive the controller waits (JOIN) before any replacement worker
    can start in the same tree, then records it as discarded.
    """
    job = read_phase_job(job_path)
    if not job or str(job.get("status") or "").upper() == "CONSUMED":
        return True
    if phase_job_liveness(job) != "dead":
        append_event(run_dir, {"event": "managed_phase_job_mismatch_wait", "job": str(job_path),
                               "pid": job.get("pid"), "reason": reason})
        print(f"[program] waiting for non-current phase worker PID={job.get('pid')} to exit ({reason})", flush=True)
        # Bounded: a hung non-current child is terminated (identity-verified) at the hard runtime cap.
        done = join_phase_jobs([{"job_path": job_path, "log_path": Path(str(job.get("log_path") or job_path.with_suffix(".log")))}],
                               poll_seconds=1.0, echo=False,
                               max_wait_seconds=float(engine_managed_job_lease(load_profile(repo))["max_phase_runtime_seconds"]) or None
                               if (repo / ".opencode/protocol/WAVE_PROJECT_PROFILE.json").is_file() else None)
        if any(d.get("unresolved") for d in done):
            append_event(run_dir, {"event": "managed_phase_job_unresolved", "job": str(job_path), "pid": job.get("pid"),
                                   "reason": reason})
            return False  # caller must not start a replacement in the same tree
    mark_phase_job_result(job_path, status="IDENTITY_MISMATCH_DISCARDED", consumed=True)
    append_event(run_dir, {"event": "managed_phase_job_discarded", "job": str(job_path), "reason": reason})
    return True


def wait_phase_job_live(
    *,
    job_path: Path,
    log_path: Path,
    proc=None,
    run_dir: Path,
    state: dict[str, Any],
    entry: dict[str, Any] | None = None,
    phase_instance_id: str | None = None,
    poll_seconds: float = 1.0,
    lease: dict[str, Any] | None = None,
) -> tuple[int | None, str]:
    """Managed wait that streams structured progress events to controller state live.

    Only recognized AC_WAVE_PROGRESS_EVENT markers update TODO/current_action;
    arbitrary prose never becomes authority. State is saved atomically on every
    applied event so the operator view updates before child exit.
    """
    job = read_phase_job(job_path)
    pid = int(job.get("pid") or 0)
    expected_start = str(job.get("process_start_time") or "") or None
    # Durable cursor in canonical state (bound to this phase instance + log):
    # a fresh job starts at 0 and a reattach resumes where the last controller
    # stopped, so an event emitted before this wait began is never skipped.
    cursor_entry = entry if entry is not None else {"wave_id": None}
    instance = str(phase_instance_id or cursor_entry.get("phase_instance_id") or "")

    def _consume(final: bool) -> None:
        before = (cursor_entry.get("progress_cursor") or {}).get("offset")
        text, outcome = consume_progress_log(cursor_entry, log_path, run_id=run_dir.name,
                                             phase_instance_id=instance, final=final)
        if text:
            try:
                print(text, end="", flush=True)
            except UnicodeEncodeError:
                print(text.encode("utf-8", "replace").decode("utf-8"), end="", flush=True)
        if entry is None:
            return
        if outcome["applied"] or outcome["rejected"]:
            append_event(run_dir, {"event": "wave_progress_final" if final else "wave_progress", "wave": entry.get("wave_id"),
                                   "applied": outcome["applied"], "rejected": outcome["rejected"], "details": outcome.get("details") or []})
        if outcome["applied"] or outcome["rejected"] or before != entry["progress_cursor"]["offset"]:
            save_state(run_dir, state)

    last_heartbeat = 0.0
    while True:
        # Liveness first: once the child is gone its log is complete, so the
        # read that follows is final and cannot miss a last-moment event.
        if proc is not None:
            try:
                alive = proc.poll() is None
            except Exception:
                alive = False
        else:
            from phase_job import pid_is_running as _pid_running

            alive = _pid_running(pid, expected_start)
        _consume(final=not alive)
        if alive and lease and enforce_lease(run_dir, job_path, entry, lease,
                                             str((entry or {}).get("wave_id") or ""), str((entry or {}).get("phase") or "")):
            time.sleep(max(0.1, poll_seconds))
            continue  # terminated: the next pass sees it gone and drains the final log
        now = time.monotonic()
        if now - last_heartbeat >= 5.0:
            current = read_phase_job(job_path) or job
            current["heartbeat_at"] = utcnow()
            current["controller_pid"] = os.getpid()
            from phase_job import write_job as _write_job

            _write_job(job_path, current)
            job = current
            last_heartbeat = now
        if not alive:
            break
        time.sleep(max(0.1, poll_seconds))
    exit_code = None
    try:
        exit_code = proc.poll() if proc is not None else None
    except Exception:
        exit_code = None
    job = read_phase_job(job_path) or job
    job["status"] = "EXITED"
    job["exit_code"] = exit_code
    job["exited_at"] = utcnow()
    job["heartbeat_at"] = utcnow()
    from phase_job import write_job as _write_job2

    _write_job2(job_path, job)
    try:
        output = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        output = ""
    return exit_code, output


def opencode_phase(repo: Path, target: str, phase: str, seq: int, run_dir: Path, program: str,
                   state: dict[str, Any], controller_context_path: Path | None = None) -> dict[str, Any]:
    if program.startswith("ac-wave-luna-openai-"):
        script_name = "run-ac-wave-luna-openai-phase.ps1"
        family = "Luna/OpenAI-only"
    elif program.startswith("ac-wave-opencode-"):
        script_name = "run-ac-wave-opencode-phase.ps1"
        family = "OpenCode-only"
    elif program.startswith("ac-wave-hybrid-"):
        script_name = "run-ac-wave-hybrid-phase.ps1"
        family = "Hybrid"
    else:
        raise RuntimeError(f"Unsupported Agent Core program family: {program}")
    script = SCRIPT_ROOT / script_name
    if not script.exists():
        raise RuntimeError(f"Missing {family} OpenCode phase runner: {script}")

    log_path = run_dir / f"{seq:04d}-{target}-{phase}-opencode.log"
    job_path = run_dir / f"{seq:04d}-{target}-{phase}-job.json"
    proc = None
    active_rel = state.get("active_phase_job")
    if isinstance(active_rel, str) and active_rel.strip():
        candidate = repo / active_rel
        job = read_phase_job(candidate)
        expected_instance = ((state.get("waves") or {}).get(str(target)) or {}).get("phase_instance_id")
        if serial_job_is_current(job, target=target, phase=phase, program=program,
                                 run_id=run_dir.name, phase_instance_id=expected_instance):
            job_path = candidate
            logged = str(job.get("log_path") or "").strip()
            if logged:
                log_path = Path(logged)
            append_event(run_dir, {"event":"managed_phase_job_resume","target":target,"phase":phase,
                                   "job":str(job_path.relative_to(repo)),"pid":job.get("pid")})
        else:
            if not settle_foreign_phase_job(repo, run_dir, candidate, reason=f"not current {target}/{phase}"):
                return {"status": "ORCHESTRATION_RECOVERY_REQUIRED", "unresolved_child": str(candidate),
                        "summary": "non-current managed child could not be resolved",
                        "findings": [f"unresolved_managed_child:{candidate}"], "changed_files": [], "next_action": "reconcile"}
            state.pop("active_phase_job", None)
            state.pop("active_phase_pid", None)
            active_rel = None

    requested = resolve_phase_route(repo, program, phase)
    dispatch_path = job_path.with_name(job_path.name.replace("-job.json", "-dispatch.json"))
    state["active_route"] = {**requested, "wave": target, "phase": phase, "dispatch_id": dispatch_path.name,
                             "started_at": (state.get("active_route") or {}).get("started_at") if active_rel else utcnow()}
    print(f"[dispatch] {target} {phase.upper()} {'reattached' if active_rel else 'started'} | {format_route(requested)}", flush=True)
    # Controller-owned per-Wave progress entry and phase instance identity.
    try:
        _meta = wave_metadata(repo / str(state.get("wave_file") or "") if state.get("wave_file") else None, load_profile(repo)) if state.get("wave_file") else None
    except Exception:
        _meta = None
    entry = ensure_wave_entry(state, target, _meta)
    entry["phase"] = str(phase).lower()
    if active_rel:
        phase_instance_id = str(entry.get("phase_instance_id") or new_phase_instance_id(run_dir.name, seq, target, phase))
    else:
        phase_instance_id = new_phase_instance_id(run_dir.name, seq, target, phase)
        entry["phase_instance_id"] = phase_instance_id
        progress_engine.bind_phase_todo(entry, phase, phase_instance_id)
        entry["dispatch_seq"] = int(entry.get("dispatch_seq", 0) or 0) + 1
        # Semantic counters increment only on fresh dispatches, never on
        # heartbeat/poll/reattach/transport/provider retries.
        if str(phase).lower() == "audit":
            progress_engine.record_audit_attempt(entry)
        if str(phase).lower() == "repair":
            progress_engine.record_repair_attempt(entry)
        if not str(entry.get("current_action") or "").strip() or entry.get("current_action") == controller_fallback_action(phase, target):
            entry["current_action"] = controller_fallback_action(phase, target)
        save_state(run_dir, state)
    if not active_rel:
        try:
            _num, _ch = engine_parse_wave_id(target)
        except ValueError:
            _num, _ch = 0, ""
        exe = shutil.which("powershell") or "powershell"
        args = [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                phase, target, "-RepoRoot", str(repo), "-DispatchRecordPath", str(dispatch_path)]
        if controller_context_path is not None and controller_context_path.exists():
            args += ["-ControllerContextPath", str(controller_context_path)]
        append_event(run_dir, {"event": "phase_dispatch", "run_id": run_dir.name, "dispatch_id": dispatch_path.name,
                               "wave": target, "phase": phase, "role": requested["role"], "backend": requested["backend"],
                               "agent": requested["agent"], "requested_model": requested["model"],
                               "requested_thinking": requested["thinking"],
                               "phase_instance_id": phase_instance_id})
        proc = start_phase_job(
            args=args, cwd=repo, log_path=log_path, job_path=job_path,
            metadata={"seq":seq,"target":target,"wave_id":target,"phase":phase,"program":program,
                      "backend":"opencode","controller_pid":os.getpid(),
                      "run_id":run_dir.name,"phase_instance_id":phase_instance_id,
                      "parallel_group":_num,"channel":_ch,
                      "progress_contract_version":effective_contract_version(state),
                      "todo_plan_state":str(entry.get("todo_plan_state") or "") or None},
        )
        state["active_phase_job"] = str(job_path.relative_to(repo))
        state["active_phase_pid"] = int(proc.pid)
        save_state(run_dir, state)
        append_event(run_dir, {"event":"managed_phase_job_start","target":target,"phase":phase,
                               "job":str(job_path.relative_to(repo)),"pid":proc.pid,
                               "phase_instance_id":phase_instance_id})

    code, output = wait_phase_job_live(
        job_path=job_path, log_path=log_path, proc=proc, run_dir=run_dir,
        state=state, entry=entry, phase_instance_id=phase_instance_id,
        lease=state.get("managed_job_lease"),
    )
    _tjob = read_phase_job(job_path)
    _timeout = _tjob.get("timeout_reason")
    if _timeout and not (_tjob.get("timeout_termination") or {}).get("terminated"):
        state["active_route"] = None
        mark_phase_job_result(job_path, status="UNRESOLVED_CHILD")
        return {"status": "ORCHESTRATION_RECOVERY_REQUIRED", "unresolved_child": str(job_path.relative_to(repo)),
                "summary": f"managed worker tree not drained after {_timeout}",
                "findings": [f"unresolved_managed_child:{_tjob.get('timeout_termination')}"],
                "changed_files": [], "next_action": "reconcile", "phase_log_path": str(log_path.relative_to(repo))}
    if _timeout:
        # Hung worker, terminated under the controller lease: never a result.
        state["active_route"] = None
        mark_phase_job_result(job_path, status="WORKER_TIMEOUT")
        return {"status": "ORCHESTRATION_RECOVERY_REQUIRED", "worker_timeout": str(_timeout),
                "summary": f"managed worker terminated: {_timeout}", "findings": [f"managed_worker_timeout:{_timeout}"],
                "changed_files": [], "next_action": "reconcile", "phase_log_path": str(log_path.relative_to(repo))}
    effective, notices = route_divergence(requested, read_json_file(dispatch_path) if dispatch_path.exists() else None)
    for notice in notices:
        print(f"{notice['event']} requested={notice['requested']} effective={notice['effective']} reason={notice['reason']}", flush=True)
        append_event(run_dir, {**notice, "wave": target, "phase": phase, "role": requested["role"], "dispatch_id": dispatch_path.name})
    append_event(run_dir, {"event": "phase_dispatch_effective", "run_id": run_dir.name, "dispatch_id": dispatch_path.name,
                           "wave": target, "phase": phase, "role": requested["role"], "backend": requested["backend"],
                           "requested_model": requested["model"], "effective_model": effective["model"],
                           "requested_thinking": requested["thinking"], "effective_thinking": effective["thinking"]})
    state.setdefault("route_history", []).append({"role": effective["role"], "model": effective["model"],
                                                  "thinking": effective["thinking"], "fallback": bool(notices)})
    state["active_route"] = None
    try:
        machine = parse_machine_result(bridge_authoritative_output(output), phase)
    except ValueError as exc:
        status = "ORCHESTRATION_RECOVERY_REQUIRED"
        result = {
            "status": status,
            "summary": output[-3000:],
            "findings": [str(exc)],
            "changed_files": [],
            "next_action": "reconcile",
            "phase_log_path": str(log_path.relative_to(repo)),
        }
        if PROVIDER_QUOTA_MARKER in output:
            result["provider_quota"] = True
        mark_phase_job_result(job_path, status=status)
        return result

    raw_status = machine["status"]
    status = "HUMAN_DEFERRED" if "HUMAN" in raw_status else raw_status
    mapping = {
        "READY":"READY", **LEGACY_STATUS_ALIASES,
        "READY_FOR_AUDIT":"READY_FOR_AUDIT", "PASS":"PASS", "REOPEN":"REOPEN",
        "BLOCKED":"BLOCKED", "FAIL":"FAIL", "HUMAN_DEFERRED":"HUMAN_DEFERRED",
        "ORCHESTRATION_RECOVERY_REQUIRED":"ORCHESTRATION_RECOVERY_REQUIRED",
    }
    status = mapping.get(status, "FAIL")
    result = {
        "status":status, "summary":output[-3000:],
        "findings":[output[-1600:]] if status in {"REOPEN","BLOCKED","FAIL","HUMAN_DEFERRED"} else [],
        "changed_files":[],
        "next_action":"reconcile" if status == "ORCHESTRATION_RECOVERY_REQUIRED" else "none",
        "phase_log_path": str(log_path.relative_to(repo)),
    }
    if "repair_hypothesis" in machine:
        result["repair_hypothesis"] = machine["repair_hypothesis"]
    mark_phase_job_result(job_path, status=status)
    return result


def phase_controller_context(repo: Path, run_dir: Path, seq: int, target: str, phase: str,
                             content_identity: str, state: dict[str, Any], findings_path: Path | None) -> Path:
    path = run_dir / f"{seq:04d}-{target}-{phase}-controller-context.json"
    # Paths only (the worker reads them): saves the next worker rediscovering what the plan/last attempt found.
    results = sorted(run_dir.glob(f"*-{target}-*-normalized.json"))
    plans = [p for p in results if p.name.endswith("-plan-normalized.json")]
    previous = read_json_file(results[-1]) if results else None
    payload = {
        "target": target,
        "wave_id": target,
        "phase": phase,
        # The dispatch for this seq uses exactly this instance id; workers copy
        # it into every AC_WAVE_PROGRESS_EVENT or the controller rejects it.
        "phase_instance_id": new_phase_instance_id(run_dir.name, seq, target, phase),
        # Fixed before dispatch from the project profile; 2 = structured PLAN
        # TODO mandatory, 1 = legacy optional (see evaluate_plan_todo).
        "progress_contract_version": int(state.get("progress_contract_version") or 1),
        "content_identity": content_identity,
        "findings_path": str(findings_path.relative_to(repo)) if findings_path and findings_path.exists() else None,
        "plan_result_path": str(plans[-1].relative_to(repo)) if plans else None,
        "previous_phase": {
            "phase": results[-1].name.split("-")[-2],
            "status": previous.get("status"),
            "repair_hypothesis": previous.get("repair_hypothesis"),
            "result_path": str(results[-1].relative_to(repo)),
        } if isinstance(previous, dict) else None,
        "audit_receipt": {
            "audit_status": state.get("audit_status"),
            "tested_wave": state.get("tested_wave"),
            "tested_content_identity": state.get("tested_content_identity"),
            "audit_candidate_sha": state.get("audit_candidate_sha"),
            "audit_result_path": state.get("audit_result_path"),
            "audit_passed_at": state.get("audit_passed_at"),
            "audit_report_path": state.get("audit_report_path"),
        },
    }
    write_json(path, payload)
    return path


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)


# Machine-specific absolute paths that the repository hygiene rule in
# validators/validate-ac-core.py rejects. These deliberately mirror that rule's own
# patterns so a persisted closeout artifact can never reintroduce what the validator
# refuses. A trailing quote/bracket is never part of the path, so matching stops there.
_ENVIRONMENT_PATH_PATTERNS = (
    re.compile(r"(?i)\b[A-Z]:/(?:Users|Projects|Repos|Workspace|Workspaces)/[^\r\n\"'\]\)}]*"),
    re.compile(r"(?i)(?<![\w./-])/(?:home|Users|mnt|workspace)/[^\r\n\"'\]\)}]*"),
    re.compile(r"(?i)\b[A-Z]:\\(?:Users|Projects|Repos|Workspace|Workspaces)\\[^\r\n\"'\]\)}]*"),
)

_ENVIRONMENT_PATH_REDACTION = "[redacted-absolute-environment-path]"


def _redact_environment_paths(text: str) -> str:
    """Strip machine-specific absolute paths from text bound for a durable in-repo artifact.

    Persisted closeout evidence quotes phase logs verbatim, and a phase log legitimately
    contains whatever the worker tool printed - including this machine's scratch-output
    paths. Keeping them would bake an environment-specific path into a tracked .md file
    and redden the hygiene validator for every later Wave, so they are redacted at the
    persistence boundary instead. The unredacted phase log stays the authoritative source.
    """
    for pattern in _ENVIRONMENT_PATH_PATTERNS:
        text = pattern.sub(_ENVIRONMENT_PATH_REDACTION, text)
    return text


def persist_fresh_audit_report(repo: Path, project: str, target: str, result: dict[str, Any],
                               normalized_path: Path) -> Path | None:
    """Persist the independent auditor output without granting the auditor product write authority.

    OpenCode audit agents may intentionally run with edit denied. The controller owns the durable
    handoff artifact: it copies the already-completed auditor phase log into the canonical audit
    report location and binds it to the normalized receipt. This is closeout evidence only.
    """
    if str(result.get("status", "")).upper() != "PASS":
        return None
    log_rel = result.get("phase_log_path")
    if not isinstance(log_rel, str) or not log_rel.strip():
        return None
    log_path = repo / log_rel
    if not log_path.exists():
        return None
    _report, audit = artifact_paths(repo, project, target)
    if audit is None:
        audit = repo / "artifacts" / "opencode" / f"wave_{target}" / f"WAVE_{target}_AUDIT_REPORT.md"
    audit.parent.mkdir(parents=True, exist_ok=True)
    raw = _redact_environment_paths(_strip_ansi(read_text(log_path))).strip()
    envelope = (
        f"\n\n## Controller-persisted fresh independent audit — {utcnow()}\n\n"
        f"- Wave: `{target}`\n"
        f"- Normalized receipt: `{normalized_path.relative_to(repo)}`\n"
        f"- Phase log: `{log_path.relative_to(repo)}`\n"
        f"- Controller receipt status: `PASS`\n\n"
        "The auditor executed independently; controller persistence is the durable artifact handoff.\n\n"
        "```text\n" + raw + "\n```\n\n"
        "WAVE_PHASE_STATUS: PASS\n"
    )
    if audit.exists():
        with audit.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(envelope)
    else:
        audit.write_text(f"# Wave {target} Audit Report\n" + envelope.lstrip(), encoding="utf-8", newline="\n")
    return audit


def print_phase_result_summary(target: str, phase: str, result: dict[str, Any], normalized: Path, repo: Path) -> None:
    status = str(result.get("status", "UNKNOWN")).upper()
    summary = re.sub(r"\s+", " ", str(result.get("summary") or "")).strip()
    if len(summary) > 500:
        summary = summary[-500:]
    print(f"[phase-result] target={target} phase={phase} status={status}", flush=True)
    if result.get("repair_hypothesis"):
        print(f"[phase-result] repair_hypothesis={result['repair_hypothesis']}", flush=True)
    if summary:
        print(f"[phase-result] summary={summary}", flush=True)
    print(f"[phase-result] normalized={normalized.relative_to(repo)}", flush=True)


def print_terminal_summary(state: dict[str, Any], run_dir: Path) -> None:
    print("AC_WAVE_PROGRAM_TERMINAL", flush=True)
    print(f"TERMINAL_CLASS={state.get('terminal_class') or 'UNKNOWN'}", flush=True)
    print(f"CURRENT_WAVE={state.get('current_wave') or ''}", flush=True)
    print(f"PHASE={state.get('phase') or ''}", flush=True)
    print(f"STALL_REASON={state.get('stall_reason') or ''}", flush=True)
    repo_path = Path(str(state.get("repository_identity") or run_dir.parents[3])).resolve()
    git_now = engine_git_capability(repo_path)
    initial_status = str(state.get("git_initial_status") or "unknown"); initial_head = str(state.get("git_initial_head") or "")
    final_head = str(git_now.get("head") or "")
    print(f"GIT_INITIAL_STATUS={initial_status.upper()}", flush=True)
    print(f"GIT_FINAL_STATUS={str(git_now.get('status') or 'unknown').upper()}", flush=True)
    print(f"GIT_INITIAL_HEAD={initial_head}", flush=True); print(f"GIT_FINAL_HEAD={final_head}", flush=True)
    print(f"GIT_HEAD_CHANGED={'YES' if initial_head != final_head else 'NO'}", flush=True)
    print("CONTROLLER_GIT_MUTATION=NONE", flush=True)
    for line in models_used_lines(state.get("route_history") or []): print(line, flush=True)
    print(f"RUN_DIR={run_dir}", flush=True)


def run_validator(repo: Path, profile: dict[str, Any], canonical: str | None, run_dir: Path, seq: int) -> Path | None:
    if not canonical or not canonical.isdigit():
        return None
    script_rel = str((profile.get("aggregate") or {}).get("validator_script") or "").strip()
    if not script_rel:
        return None
    script = repo / script_rel
    if not script.exists():
        raise RuntimeError(f"Declared aggregate validator is missing: {script_rel}")
    out_path = run_dir / f"{seq:04d}-validator-{canonical}.json"
    cp = subprocess.run([sys.executable, str(script), "--wave", canonical], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
                        **subprocess_no_window_kwargs())
    blob = cp.stdout.strip()
    # Keep the JSON even when the validator intentionally exits nonzero on can_close=false.
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        data = {"can_close": False, "failure_reasons": [blob[-4000:] or cp.stderr[-4000:]], "exit_code": cp.returncode}
    write_json(out_path, data)
    return out_path




def route_findings(repo: Path, run_dir: Path, target: str, canonical: str | None,
                   audit_path: Path | None, validator_path: Path | None, seq: int,
                   phase_result: Path | None = None) -> Path:
    router = SCRIPT_ROOT / "route-wave-findings.py"
    out_path = run_dir / f"{seq:04d}-{target}-findings.json"
    if not router.exists():
        write_json(out_path, {"wave": target, "finding_count": 0, "human_only": False, "findings": []})
        return out_path
    cmd = [sys.executable, str(router), "--repo", str(repo), "--wave", target, "--out", str(out_path)]
    manifest = repo / "artifacts" / f"wave_{canonical}" / f"WAVE_{canonical}_EVIDENCE_MANIFEST.json" if canonical else None
    if manifest and manifest.exists():
        cmd += ["--manifest", str(manifest.relative_to(repo))]
    if validator_path and validator_path.exists():
        cmd += ["--validator-json", str(validator_path.relative_to(repo))]
    if audit_path and audit_path.exists():
        cmd += ["--audit-report", str(audit_path.relative_to(repo))]
    if phase_result and phase_result.exists():
        cmd += ["--phase-result", str(phase_result.relative_to(repo))]
    cp = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace",
                        **subprocess_no_window_kwargs())
    if cp.stdout:
        print(cp.stdout)
    if cp.returncode != 0:
        raise RuntimeError(f"route-wave-findings.py failed: {cp.stderr}")
    return out_path




NEGATION_RE = re.compile(r"\b(?:no|not|without|never|none|nor)\b|n't\b", re.I)


def _affirmed_human_blocker(text: str) -> bool:
    """A human-authority keyword counts only when not negated earlier in the same clause
    ("No human deferral: no missing MFA/credential" is repository-owned prose, not a blocker)."""
    for match in HUMAN_RE.finditer(text):
        clause = re.split(r"[.;:\n]", text[:match.start()])[-1]
        if not NEGATION_RE.search(clause):
            return True
    return False


def human_deferred_is_real(result: dict[str, Any]) -> bool:
    findings = result.get("findings") or []
    if not findings:
        return False
    return all(_affirmed_human_blocker(str(x)) for x in findings)




def account_no_progress_attempt(state: dict[str, Any], repo: Path, profile: dict[str, Any],
                               program: str, key: str, run_id: str) -> int:
    """Count one identical no-progress attempt, durably across program runs.

    The per-run `state["fingerprints"]` map is only the fast path: it lives in a
    disposable run directory, so an operator restart used to hand an unchanged
    blocker a fresh retry budget. Real consequence: three separate runs each
    replayed count 1->3 and stalled on a byte-identical fingerprint for one
    unresolved blocker. The program-scoped ledger is the authority; the per-run
    map is kept in step for state readability.
    """
    run_count = int(state.setdefault("fingerprints", {}).get(key, 0)) + 1
    state["fingerprints"][key] = run_count
    durable = record_progress_attempt(repo, profile, program, key,
                                      str(state.get("run_id") or run_id),
                                      AC_MAX_IDENTICAL_RECOVERY)
    if durable > run_count:
        state["fingerprints"][key] = durable
        return durable
    return run_count


def result_fingerprint(target: str, phase: str, result: dict[str, Any]) -> str:
    raw_findings = [str(x) for x in (result.get("findings") or [])]
    finding_ids = sorted({m.group(0).upper() for text in raw_findings for m in FINDING_ID_RE.finditer(text)})
    if finding_ids:
        findings = finding_ids
    else:
        # No stable ID: the raw prose is all we have, and prose drifts. Collapse a
        # recognised machine error class to a durable token so the same outage
        # keeps one identity across rewordings. Without this, a reworded
        # "required model X unavailable" hashes differently every time, the
        # identical-retry budget never accumulates, and the Wave spins.
        findings = sorted(
            {classify_finding_identity(re.sub(r"\b[0-9a-f]{40}\b", "<sha>", text, flags=re.I).strip())
             for text in raw_findings}
        )
    # Phase/status are routing state, not the semantic blocker identity.
    # Keep the same finding stable across repair -> audit -> close loops.
    data = {
        "target": target,
        "findings": findings,
        "repair_hypothesis": str(result.get("repair_hypothesis") or "").strip().lower(),
    }
    import hashlib
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()




def implementation_identity(repo: Path, profile: dict[str, Any]) -> str:
    ignored = profile.get("evidence", {}).get("allowed_closeout_only_paths", [])
    return repository_content_identity(repo, ignored)




def validator_can_close(path: Path | None) -> tuple[bool, list[str]]:
    if path is None or not path.exists():
        return False, ["aggregate validator output missing"]
    data = read_json_file(path)
    if not isinstance(data, dict):
        return False, ["aggregate validator output is not valid JSON"]
    reasons = data.get("failure_reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    return bool(data.get("can_close")), [str(x) for x in reasons]




def controller_runtime_fingerprint(repo: Path, profile: dict[str, Any]) -> str:
    import hashlib
    h = hashlib.sha256()
    for rel in sorted(str(x) for x in profile.get("controller_restart_paths", [])):
        p = repo / rel
        h.update(rel.encode("utf-8")); h.update(b"\0")
        try:
            h.update(p.read_bytes())
        except OSError:
            h.update(b"<missing>")
        h.update(b"\0")
    return h.hexdigest()




def final_program_validation(repo: Path, profile: dict[str, Any], run_dir: Path, seq: int) -> tuple[bool, list[str], Path, str | None]:
    cfg = profile.get("final_validation") or {}
    out = run_dir / f"{seq:04d}-final-canonical-sweep.json"
    if not cfg.get("enabled", False):
        payload = {"can_close": True, "disabled": True, "results": {}, "failure_reasons": []}
        write_json(out, payload); return True, [], out, None
    script_rel = str(cfg.get("validator_script") or profile.get("aggregate", {}).get("validator_script") or "").strip()
    wave_ids = [str(x) for x in cfg.get("canonical_wave_ids", [])]
    failures: list[str] = []
    results: dict[str, Any] = {}
    first_failed: str | None = None
    if not script_rel or not wave_ids:
        failures.append("final validation profile is missing validator_script or canonical_wave_ids")
    script = repo / script_rel if script_rel else None
    if script is None or not script.is_file():
        failures.append(f"final canonical validator missing: {script_rel or '<unset>'}")
    if not failures:
        for wid in wave_ids:
            cp = subprocess.run([sys.executable, str(script), "--wave", wid], cwd=str(repo), capture_output=True,
                                text=True, encoding="utf-8", errors="replace", check=False,
                                **subprocess_no_window_kwargs())
            try:
                data = json.loads(cp.stdout.strip())
            except json.JSONDecodeError:
                data = {"can_close": False, "failure_reasons": [(cp.stdout or cp.stderr)[-4000:] or f"validator exit={cp.returncode}"]}
            results[wid] = data
            if cp.returncode != 0 or data.get("can_close") is not True:
                if first_failed is None: first_failed = wid
                reasons = data.get("failure_reasons") or [f"validator exit={cp.returncode}"]
                if not isinstance(reasons, list): reasons = [str(reasons)]
                failures.extend(f"{wid}: {reason}" for reason in reasons)
    payload = {"can_close": not failures, "canonical_wave_ids": wave_ids, "results": results,
               "first_failed_wave": first_failed, "failure_reasons": failures}
    write_json(out, payload)
    return not failures, failures, out, first_failed




def run_postrun_checks(repo: Path, profile: dict[str, Any], run_dir: Path, seq: int) -> tuple[bool, list[str], Path]:
    out = run_dir / f"{seq:04d}-postrun-checks.json"
    failures: list[str] = []; results: list[dict[str, Any]] = []
    for rel in [str(x) for x in profile.get("postrun_checks", [])]:
        p = repo / rel
        if not p.is_file():
            failures.append(f"postrun check missing: {rel}"); results.append({"path": rel, "exit": None}); continue
        command = [sys.executable, str(p)] if p.suffix.lower() == ".py" else [str(p)]
        try:
            cp = subprocess.run(command, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
                                **subprocess_no_window_kwargs())
        except OSError as exc:
            # One unlaunchable entry (for example a non-Python document launched with no
            # interpreter) must not abort the sweep. The remaining entries still have to
            # run and the report still has to be written; otherwise every entry after the
            # first failure is silently unaccounted for and no postrun verdict exists.
            detail = f"{type(exc).__name__}: {exc}"
            failures.append(f"postrun check not launchable: {rel} ({detail})")
            results.append({"path": rel, "exit": None, "launched": False, "error": detail})
            continue
        results.append({"path": rel, "exit": cp.returncode, "launched": True, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-4000:]})
        if cp.returncode != 0: failures.append(f"postrun check failed: {rel} exit={cp.returncode}")
    write_json(out, {"pass": not failures, "results": results, "failure_reasons": failures})
    return not failures, failures, out




def find_run_state(repo: Path, profile: dict[str, Any], program: str, run_id: str) -> tuple[Path | None, str | None]:
    canonical = program_run_root(repo, profile, program) / run_id / "state.json"
    if canonical.is_file():
        return canonical, "canonical"
    for root in legacy_program_roots(repo, profile, program):
        candidate = root / run_id / "state.json"
        if candidate.is_file():
            return candidate, "legacy"
    return None, None




def controller_close_wave(repo: Path, profile: dict[str, Any], project: str, target: str) -> None:
    ensure_lifecycle_integrity(repo, profile, apply_safe=True, reason=f"before-close:{target}")
    path, state = engine_wave_location(repo, profile, target)
    if state == "done":
        return
    if path is None or state not in {"pending", "blocked", "postponed"}:
        raise RuntimeError(f"Cannot close {target}: lifecycle file is not in an active Wave directory")
    done = repo / profile["paths"]["done"]
    done.mkdir(parents=True, exist_ok=True)
    destination = done / path.name
    if destination.exists() and destination.resolve() != path.resolve():
        raise RuntimeError(f"Cannot close {target}: canonical done copy already exists")
    path.replace(destination)
    ensure_lifecycle_integrity(repo, profile, apply_safe=True, reason=f"after-close:{target}")


def owner_route_key(target: str, owner: str, findings: dict[str, Any] | None) -> str:
    """Identity of a target->owner route: the finding IDs routed to that owner."""
    ids = sorted({str(f.get("finding_id")) for f in (findings or {}).get("findings", [])
                  if isinstance(f, dict) and str(f.get("execution_owner")) == str(owner)})
    return f"{target}->{owner}::" + hashlib.sha256("|".join(ids).encode("utf-8")).hexdigest()[:16]


def revert_worker_lifecycle_mutation(repo: Path, project: str, target: str, phase: str, status: str,
                                     pre_state: str | None, pre_path: Path | None) -> dict[str, str] | None:
    """Only controller_close_wave may archive a Wave: undo a worker's move to done made during this phase."""
    moved_path, moved_state = wave_location(repo, project, target)
    if (pre_state == "done" or moved_state != "done" or moved_path is None or pre_path is None
            or (phase == "close" and status.upper() == "PASS")):
        return None
    moved_path.replace(pre_path)
    return {"from": str(moved_path.relative_to(repo)), "to": str(pre_path.relative_to(repo))}


def choose_after(phase: str, result: dict[str, Any]) -> str:
    status = str(result.get("status", "FAIL")).upper()
    next_hint = str(result.get("next_action", "none")).lower()
    if status == "HUMAN_DEFERRED":
        return "human"
    if status in {"MISSING_STATUS", "ORCHESTRATION_RECOVERY_REQUIRED"}:
        return phase
    if phase == "reconcile":
        if status == "COMPLETE" or next_hint == "next_wave":
            return "reconcile"
        if next_hint in {"plan", "run", "repair", "audit", "close"}:
            return next_hint
        return "repair" if status in {"REOPEN", "BLOCKED", "FAIL", "NO_PROGRESS"} else "run"
    if phase == "plan":
        return "run" if status in {"READY", "PASS"} else "repair"
    if phase in {"run", "repair"}:
        return "audit" if status in {"READY_FOR_AUDIT", "PASS", "READY"} else "repair"
    if phase == "audit":
        return "close" if status == "PASS" else "repair"
    if phase == "close":
        return "reconcile" if status == "PASS" else "repair"
    return "repair"




def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic unattended Wave program controller")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--backend", choices=BACKENDS, default="codex")
    ap.add_argument("--program", choices=[
        "ac-wave-luna-openai-auto","ac-wave-luna-openai-end","ac-wave-luna-openai-parallel",
        "ac-wave-opencode-auto","ac-wave-opencode-end","ac-wave-opencode-parallel",
        "ac-wave-hybrid-auto","ac-wave-hybrid-end","ac-wave-hybrid-parallel"
    ], default="ac-wave-hybrid-end")
    ap.add_argument("--model", help="Optional Codex model override; omit to use CLI/default config")
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--resume-run-id", help="Manual/debug override. Normal invocation auto-resumes.")
    ap.add_argument("--new-run", action="store_true", help="Explicitly ignore unfinished runs and start from repository truth")
    ap.add_argument("--max-iterations", type=int, default=0, help="0 = use profile/default hard safety ceiling")
    args = ap.parse_args()
    if args.new_run and args.resume_run_id:
        raise SystemExit("--new-run and --resume-run-id are mutually exclusive")


    repo = Path(args.repo).resolve()
    # Git is optional and controller startup is read-only with respect to VCS.
    profile = load_profile(repo)
    git_initial = engine_git_capability(repo)
    print(f"AC_WAVE_GIT_STATUS={str(git_initial.get('status') or 'unknown').upper()}", flush=True)

    self_heal(repo)
    profile = load_profile(repo)
    lifecycle_preflight = ensure_lifecycle_integrity(repo, profile, apply_safe=True, reason="controller-preflight")
    if lifecycle_preflight.get("repairs"):
        print(f"[lifecycle-self-heal] repaired={len(lifecycle_preflight['repairs'])} receipt={lifecycle_preflight.get('receipt')}", flush=True)
    validate_orchestration(repo)
    authoring_errors = validate_wave_authoring(repo)
    if authoring_errors:
        raise RuntimeError("validate-wave-authoring.py failed: " + "; ".join(authoring_errors[:8]))
    project = str(profile["project_id"])
    ensure_temp_layout(repo, profile)
    program = args.program


    source_path: Path | None = None
    source_kind: str | None = None
    if args.resume_run_id:
        source_path, source_kind = find_run_state(repo, profile, program, args.resume_run_id)
        if source_path is None:
            raise SystemExit(f"Unknown run id: {args.resume_run_id}")
    elif not args.new_run and bool(profile.get("scheduler", {}).get("auto_resume", True)):
        source_path, source_kind = discover_unfinished_run(repo, profile, program)


    saved = read_json_file(source_path) if source_path else None
    classification, truth_target, truth_phase = resume_classification(repo, profile, saved if isinstance(saved, dict) else None, source_kind)


    if source_path is not None and source_kind == "canonical" and not args.new_run:
        run_dir = source_path.parent
        run_id = run_dir.name
        state = dict(saved or {})
    else:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        run_dir = program_run_root(repo, profile, program) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        state = dict(saved or {}) if source_path is not None and not args.new_run else {}
        if source_path is not None:
            state["migrated_from"] = str(source_path.parent.relative_to(repo))
            state["legacy_run_id"] = source_path.parent.name


    configure_temp_environment(repo, profile, run_id)
    lock = ControllerLock.acquire(repo, profile, program, run_id)
    atexit.register(lock.release)


    identity = repo_identity(repo)
    defaults = {
        "run_id": run_id, "backend": args.backend, "project": project, "started_at": utcnow(),
        "updated_at": utcnow(), "iteration": 0, "current_wave": None, "phase": "reconcile",
        "terminal": False, "terminal_class": None, "fingerprints": {}, "recovery_counts": {}, "owner_stack": [],
        "target_override": None, "findings_path": None, "seq": 0, "closed_owner_repair": False,
        "progress_epoch": 0, "active_phase_job": None, "active_phase_pid": None,
        "state_schema_version": STATE_SCHEMA_VERSION, "waves": {}, "parallel_groups": {},
        "progress_contract_version": 2, "progress_contract_source": "default", "progress_enabled": True,
    }
    defaults.update(state)
    state = migrate_state(defaults)
    state.update({
        "run_id": run_id, "backend": args.backend, "project": project, "terminal": False,
        "terminal_class": None, "resume_classification": classification,
        "repository_identity": identity["repo_root"], "branch": identity["branch"],
        "saved_head": state.get("current_head") or state.get("saved_head"), "current_head": identity["head"],
        "controller_pid": os.getpid(), "controller_process_start_marker": process_start_marker(os.getpid()),
        # Decided per multi-channel group by record_parallel_strategy(), never assumed.
        "parallel_strategy": "undetermined" if program.endswith("-parallel") else None,
    })
    state.setdefault("fingerprints", {})
    state.setdefault("owner_stack", [])
    # Worker progress contract is decided here, from config, before any
    # dispatch; worker output never changes it (see evaluate_plan_todo).
    # This is the single pre-dispatch resolution point: the engine normalizer is
    # the only place that decides the effective default (enabled + v2 when the
    # profile is silent), and the resolved `source` is recorded so a deliberate
    # legacy stanza stays visible in state/status instead of looking like a
    # missing-field fallback.
    try:
        _progress = engine_normalize_progress_profile(profile)
        state["progress_contract_version"] = int(_progress["contract_version"])
        state["progress_contract_source"] = str(_progress["source"])
        state["progress_enabled"] = bool(_progress["enabled"])
        # Controller-owned worker lease (profile `controller` block), snapshotted per run.
        state["managed_job_lease"] = engine_managed_job_lease(profile)
    except ValueError as exc:
        raise SystemExit(f"Invalid project profile: {exc}")


    # Repository truth beats stale run routing. A CLOSED Wave remains lifecycle-CLOSED;
    # the controller may nevertheless resume an explicit bounded repair transaction.
    override = state.get("target_override")
    active_closed_owner_transaction = False
    if override:
        _, override_state = engine_wave_location(repo, profile, str(override))
        active_closed_owner_transaction = bool(override_state == "done" and state.get("closed_owner_repair"))
        if override_state == "done" and not active_closed_owner_transaction:
            append_event(run_dir, {"event": "stale_closed_owner_route_discarded", "owner": override})
            state["target_override"] = None
            state["owner_stack"] = []
            classification = "RECONCILE_FORWARD"
        elif active_closed_owner_transaction:
            classification = "RESUME_CLOSED_OWNER_REPAIR"
    if classification in {"RECONCILE_FORWARD", "STALE_RUN", "NEW_RUN_FROM_REPO_TRUTH"} and not active_closed_owner_transaction:
        state["current_wave"] = truth_target
        state["phase"] = "reconcile"
        state["target_override"] = None
        state["owner_stack"] = []
        state["findings_path"] = None
    elif classification == "IMPORT_LEGACY_RUN" and truth_target and state.get("current_wave") != truth_target:
        state["current_wave"] = truth_target
        state["phase"] = truth_phase


    event_name = "program_resume" if source_path else "program_start"
    append_event(run_dir, {"event": event_name, "backend": args.backend, "project": project, "classification": classification,
                           "source": str(source_path.parent.relative_to(repo)) if source_path else None})
    print_program_routing(repo, program, args.backend, args.model)
    observe_controller_provenance(repo, profile, run_dir, state)
    save_state(run_dir, state)
    sweep_stale_managed_worktrees(repo, profile, run_dir, state)
    write_json(run_dir / "phase-result.schema.json", RESULT_SCHEMA)


    if args.preflight_only:
        target, wave_path, canonical = current_target(repo, project, state.get("target_override"), allow_closed_owner_repair=bool(state.get("closed_owner_repair")))
        print(json.dumps({"status":"READY","project":project,"current_wave":target,
                          "wave_file":str(wave_path) if wave_path else None,"canonical":canonical,
                          "run_id":run_id,"run_dir":str(run_dir.relative_to(repo)),
                          "resume_classification":classification,
                          # Resolved progress contract, so a deliberate legacy
                          # stanza is visible here and not mistaken for a
                          # missing-field fallback.
                          "progress": {"enabled": bool(state.get("progress_enabled")),
                                       "contract_version": int(state.get("progress_contract_version") or 1),
                                       "source": str(state.get("progress_contract_source") or "default")}},
                          indent=2))
        lock.release()
        return 0


    controller_cfg = profile.get("controller") or {}
    safety_iteration_limit = args.max_iterations if args.max_iterations and args.max_iterations > 0 else int(controller_cfg.get("max_iterations", 1000))
    if safety_iteration_limit < 1:
        safety_iteration_limit = 1000


    phase = str(state.get("phase") or "reconcile")
    target_cache: str | None = state.get("current_wave") if state.get("target_override") else None
    stored_findings = state.get("findings_path")
    findings_path: Path | None = (repo / stored_findings) if isinstance(stored_findings, str) and stored_findings else None
    no_progress = False
    seq = int(state.get("seq", 0))
    controller_boot_fingerprint = controller_runtime_fingerprint(repo, profile)


    while True:
        lock.heartbeat()
        try:
            lifecycle_guard = ensure_lifecycle_integrity(repo, profile, apply_safe=True, reason="controller-iteration")
        except RuntimeError as exc:
            detail = str(exc)
            key = "lifecycle_integrity::" + detail
            recovery_counts = state.setdefault("recovery_counts", {})
            recovery_counts[key] = int(recovery_counts.get(key, 0)) + 1
            append_event(run_dir, {"event":"LIFECYCLE_INTEGRITY_CONFLICT","detail":detail,
                                   "count":recovery_counts[key]})
            print(f"[lifecycle-conflict] {detail}", flush=True)
            if recovery_counts[key] >= AC_MAX_IDENTICAL_RECOVERY:
                state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                              "stall_reason":"ambiguous_lifecycle_authority"})
                save_state(run_dir,state)
                append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","reason":"ambiguous_lifecycle_authority",
                                      "count":recovery_counts[key]})
                print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
            save_state(run_dir,state); time.sleep(1); continue
        if lifecycle_guard.get("repairs"):
            append_event(run_dir, {"event":"lifecycle_self_heal","repairs":lifecycle_guard.get("repairs"),
                                   "receipt":lifecycle_guard.get("receipt")})
            print(f"[lifecycle-self-heal] repaired={len(lifecycle_guard['repairs'])} receipt={lifecycle_guard.get('receipt')}", flush=True)
        state["iteration"] = int(state.get("iteration",0)) + 1
        observe_controller_provenance(repo, profile, run_dir, state)
        if state["iteration"] > safety_iteration_limit:
            state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                          "stall_reason":"controller_iteration_safety_ceiling"})
            save_state(run_dir,state)
            append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","reason":"controller_iteration_safety_ceiling",
                                  "limit":safety_iteration_limit})
            print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30


        override = state.get("target_override")
        if override:
            _, override_state = engine_wave_location(repo, profile, str(override))
            if override_state == "done" and not state.get("closed_owner_repair"):
                append_event(run_dir, {"event":"closed_owner_kept_closed","owner":override,"action":"no_lifecycle_reopen"})
                state["target_override"] = None; state["owner_stack"] = []; override = None; phase = "reconcile"
            elif override_state == "done":
                append_event(run_dir, {"event":"closed_owner_repair_transaction","owner":override,"lifecycle_state":"done"})

        # Managed parallel group barrier (controller authority). Eligible
        # channels of the minimum numeric group may run concurrently; the next
        # numeric group must not start until the previous group is DONE.
        if program.endswith("-parallel") and not override:
            try:
                _groups = pending_parallel_groups(repo, profile)
            except Exception as exc:
                _groups = []
                append_event(run_dir, {"event": "parallel_group_enumeration_failed", "detail": str(exc)[:500]})
            # Real barrier: the active group is the minimum non-DONE scheduled
            # group across pending/done/blocked/postponed — never pending-only.
            try:
                _barrier_active = active_scheduled_group(repo, profile)
            except Exception:
                _barrier_active = None
            if _groups:
                _active_num, _active_members = _groups[0]
                if _barrier_active is not None and int(_barrier_active[0]) < int(_active_num):
                    # A non-DONE earlier group (e.g. BLOCKED) exists: later
                    # groups are not eligible. Never dispatch W102 here.
                    append_event(run_dir, {"event": "parallel_group_barrier_blocked", "active_group": int(_barrier_active[0]),
                                           "members": [f"{w}:{s}" for w, s in _barrier_active[1]],
                                           "withheld_group": int(_active_num)})
                    _groups = []
            if _groups:
                _active_num, _active_members = _groups[0]
                # Barrier visibility: later groups wait while the active group is open.
                if len(_groups) > 1:
                    _later = [str(w) for _, grp in _groups[1:] for w, _ in grp][:6]
                    append_event(run_dir, {"event": "parallel_group_barrier", "active_group": _active_num,
                                           "active": [str(w) for w, _ in _active_members], "waiting_groups": _later})
                if len(_active_members) > 1:
                    _gkey = str(int(_active_num))
                    _gstate = state.setdefault("parallel_groups", {}).setdefault(_gkey, {})
                    if not _gstate.get("integrated") and not _gstate.get("failed"):
                        # Full standalone authoring semantics are the runtime
                        # pre-dispatch gate; the in-process group helper remains
                        # the deterministic focused check used by tests/callers.
                        _auth_errors = validate_wave_authoring(repo)
                        if not _auth_errors:
                            _auth_errors = validate_parallel_group_authoring(repo, profile, _active_members)
                        if _auth_errors:
                            # Badly authored group fails closed; never silent fallback.
                            state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                          "phase": "stalled", "stall_reason": "parallel_authoring_invalid",
                                          "current_wave": str(_active_members[0][0])})
                            append_event(run_dir, {"event": "parallel_authoring_invalid", "group": _active_num, "errors": _auth_errors})
                            save_state(run_dir, state)
                            print("PROGRAM_TECHNICAL_STALLED")
                            print_terminal_summary(state, run_dir)
                            lock.release()
                            return 30
                        from wave_state_engine import parallel_config as _parallel_cfg_fn
                        _pcfg = _parallel_cfg_fn(profile)
                        _ok, _reason = workspace_engine.can_isolate_parallel(repo)
                        _synthetic = False
                        if (not _ok and str(_reason).startswith("dirty-working-tree:")
                                and dirt_is_controller_owned(repo, profile, state)):
                            # Only this run's own promoted/phase work is uncommitted:
                            # freeze it as a controller-owned synthetic base.
                            _ok, _synthetic = True, True
                        _policy = str(_pcfg.get("dirty_tree_policy") or "serial_fallback")
                        if not _ok and _policy == "block":
                            state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED", "phase": "stalled",
                                          "stall_reason": f"parallel_dirty_tree_blocked:{_reason}",
                                          "current_wave": str(_active_members[0][0])})
                            append_event(run_dir, {"event": "parallel_dirty_tree_blocked", "group": _active_num, "reason": _reason})
                            save_state(run_dir, state)
                            print("PROGRAM_TECHNICAL_STALLED")
                            print_terminal_summary(state, run_dir)
                            lock.release()
                            return 30
                        if not _ok and _policy != "serial_fallback":
                            state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED", "phase": "stalled",
                                          "stall_reason": f"parallel_dirty_tree_policy_unsupported:{_policy}",
                                          "current_wave": str(_active_members[0][0])})
                            save_state(run_dir, state)
                            print("PROGRAM_TECHNICAL_STALLED")
                            print_terminal_summary(state, run_dir)
                            lock.release()
                            return 30
                        if not _ok:
                            record_parallel_strategy(run_dir, state, "serial_fallback", int(_active_num), _reason)
                        else:
                            if str(_pcfg.get("mode") or "managed") != "managed":
                                record_parallel_strategy(run_dir, state, "serial_fallback", int(_active_num),
                                                         f"parallel-mode:{_pcfg.get('mode')}")
                            elif str(_pcfg.get("isolation") or "git_worktree") != "git_worktree":
                                state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                              "phase": "stalled", "stall_reason": "parallel_isolation_unsupported",
                                              "current_wave": str(_active_members[0][0])})
                                append_event(run_dir, {"event": "parallel_isolation_unsupported", "group": _active_num,
                                                       "isolation": _pcfg.get("isolation")})
                                save_state(run_dir, state)
                                print("PROGRAM_TECHNICAL_STALLED")
                                print_terminal_summary(state, run_dir)
                                lock.release()
                                return 30
                            elif str(_pcfg.get("group_barrier") or "lifecycle_done") != "lifecycle_done":
                                state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                              "phase": "stalled", "stall_reason": "parallel_barrier_unsupported",
                                              "current_wave": str(_active_members[0][0])})
                                append_event(run_dir, {"event": "parallel_barrier_unsupported", "group": _active_num,
                                                       "barrier": _pcfg.get("group_barrier")})
                                save_state(run_dir, state)
                                print("PROGRAM_TECHNICAL_STALLED")
                                print_terminal_summary(state, run_dir)
                                lock.release()
                                return 30
                            elif str(_pcfg.get("integration_order") or "channel") != "channel":
                                state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                              "phase": "stalled", "stall_reason": "parallel_order_unsupported",
                                              "current_wave": str(_active_members[0][0])})
                                append_event(run_dir, {"event": "parallel_order_unsupported", "group": _active_num,
                                                       "order": _pcfg.get("integration_order")})
                                save_state(run_dir, state)
                                print("PROGRAM_TECHNICAL_STALLED")
                                print_terminal_summary(state, run_dir)
                                lock.release()
                                return 30
                            else:
                                # Immutable frozen base: computed once at group start,
                                # then reused from authoritative group state on resume.
                                # Main HEAD is never re-frozen on restart.
                                if isinstance(_gstate.get("frozen"), dict) and _gstate["frozen"].get("base_head"):
                                    _frozen = _gstate["frozen"]
                                    append_event(run_dir, {"event": "parallel_frozen_reused", "group": _active_num,
                                                           "base_head": _frozen.get("base_head")})
                                else:
                                    try:
                                        if _synthetic:
                                            _frozen = workspace_engine.synthetic_base(
                                                repo, run_dir.name, int(_active_num), lambda r: implementation_identity(r, profile))
                                            append_event(run_dir, {"event": "parallel_synthetic_base", "group": _active_num,
                                                                   "base_head": _frozen.get("base_head"),
                                                                   "main_head": _frozen.get("main_head")})
                                        else:
                                            _frozen = workspace_engine.frozen_base(repo, lambda r: implementation_identity(r, profile))
                                    except Exception as exc:
                                        _frozen = {"base_head": None, "base_content_identity": None}
                                        append_event(run_dir, {"event": "parallel_frozen_base_failed", "group": _active_num, "detail": str(exc)[:500]})
                                    _gstate.update({"frozen": _frozen, "started_at": utcnow(), "members": [str(w) for w, _ in _active_members]})
                                if not isinstance(_frozen, dict) or not _frozen.get("base_head"):
                                    _gstate["failed"] = "frozen-base-unavailable"
                                state["active_parallel_group"] = int(_active_num)
                                save_state(run_dir, state)
                                # Isolated workspaces at the frozen base with identity check.
                                # Stale worktrees are recreated, never silently reused.
                                if not _gstate.get("failed"):
                                    workspace_engine.create_group_workspace(repo, run_dir.name, int(_active_num))
                                for _wid, _ in ([] if _gstate.get("failed") else _active_members):
                                    if _discover_live_wave_jobs(run_dir, str(_wid), set()):
                                        # A live child still works here: never recreate its
                                        # worktree underneath it. Reattach/quarantine owns it;
                                        # a stale-base candidate is rejected at collection.
                                        append_event(run_dir, {"event": "parallel_worktree_in_use",
                                                               "wave": str(_wid), "group": _active_num})
                                        continue
                                    try:
                                        _, _outcome = workspace_engine.ensure_channel_worktree(
                                            repo, run_dir.name, int(_active_num), str(_wid),
                                            (_frozen.get("base_head") if isinstance(_frozen, dict) else None))
                                        if _outcome == "recreated-stale":
                                            append_event(run_dir, {"event": "parallel_worktree_recreated_stale",
                                                                   "wave": str(_wid), "group": _active_num,
                                                                   "base_head": (_frozen.get("base_head") if isinstance(_frozen, dict) else None)})
                                    except Exception as exc:
                                        _gstate["failed"] = f"worktree-create-failed:{_wid}:{exc}"
                                        break
                                if _gstate.get("failed"):
                                    cleanup_group_worktrees(repo, run_dir, state, int(_active_num), str(_gstate.get("failed")))
                                    record_parallel_strategy(run_dir, state, "serial_fallback", int(_active_num), str(_gstate.get("failed")))
                                else:
                                    record_parallel_strategy(run_dir, state, "managed", int(_active_num))
                                    append_event(run_dir, {"event": "parallel_group_start", "group": _active_num,
                                                           "members": [str(w) for w, _ in _active_members],
                                                           "frozen_base": (_frozen.get("base_head") if isinstance(_frozen, dict) else None),
                                                           "max_concurrency": max_parallel_concurrency(profile)})
                                    _result = run_parallel_group_implement(
                                        repo=repo, profile=profile, program=program, run_dir=run_dir,
                                        state=state, group=int(_active_num), members=_active_members,
                                        frozen=_frozen if isinstance(_frozen, dict) else {}, seq_start=seq,
                                        backend=args.backend, codex_model=args.model,
                                    )
                                    seq = int(_result.get("next_seq", seq))
                                    state["seq"] = seq
                                    if _result.get("errors"):
                                        append_event(run_dir, {"event": "parallel_implement_errors", "group": _active_num, "errors": _result.get("errors")})
                                    # Explicit JOIN is inside run_parallel_group_implement; verify it here.
                                    append_event(run_dir, {"event": "parallel_joined", "group": _active_num, "joined": _result.get("joined")})
                                    if _result.get("unresolved"):
                                        # A live child could not be killed or verified: stop
                                        # deterministically; its worktree stays (cleanup skips live).
                                        _reason = ",".join(sorted(_result["unresolved"]))
                                        _gstate["failed"] = f"unresolved_managed_child:{_reason}"
                                        state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                                      "phase": "stalled", "stall_reason": _gstate["failed"],
                                                      "unresolved_children": _result["unresolved"],
                                                      "current_wave": sorted(_result["unresolved"])[0]})
                                        append_event(run_dir, {"event": "PROGRAM_TECHNICAL_STALLED", "group": _active_num,
                                                               "reason": state["stall_reason"]})
                                        save_state(run_dir, state)
                                        cleanup_group_worktrees(repo, run_dir, state, int(_active_num), "unresolved-child")
                                        print("PROGRAM_TECHNICAL_STALLED")
                                        print_terminal_summary(state, run_dir)
                                        lock.release()
                                        return 30
                                    if _result.get("timeouts"):
                                        # A hung channel was terminated: nothing of this group
                                        # integrates, the group is not DONE, the barrier holds.
                                        _reason = ",".join(f"{w}:{r}" for w, r in sorted(_result["timeouts"].items()))
                                        _gstate["failed"] = f"managed_worker_timeout:{_reason}"
                                        state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                                      "phase": "stalled", "stall_reason": f"managed_worker_timeout:{_reason}",
                                                      "current_wave": sorted(_result["timeouts"])[0]})
                                        append_event(run_dir, {"event": "PROGRAM_TECHNICAL_STALLED", "group": _active_num,
                                                               "reason": state["stall_reason"]})
                                        save_state(run_dir, state)
                                        cleanup_group_worktrees(repo, run_dir, state, int(_active_num), "worker-timeout")
                                        print("PROGRAM_TECHNICAL_STALLED")
                                        print_terminal_summary(state, run_dir)
                                        lock.release()
                                        return 30
                                    if _result.get("no_progress_exhausted"):
                                        # A channel used up its bounded repair
                                        # budget: nothing of this group may
                                        # integrate, the barrier holds, and the
                                        # program stops with a durable reason.
                                        _ex = _result["no_progress_exhausted"]
                                        _reason = ",".join(
                                            f"{x['wave']}:{x['count']}/{x['limit']}" for x in _ex)
                                        _gstate["failed"] = f"wave_no_progress_budget_exhausted:{_reason}"
                                        state.update({"terminal": True,
                                                      "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                                      "phase": "stalled", "stall_reason": _gstate["failed"],
                                                      "current_wave": str(_ex[0]["wave"])})
                                        append_event(run_dir, {"event": "PROGRAM_TECHNICAL_STALLED",
                                                               "group": _active_num, "reason": state["stall_reason"]})
                                        save_state(run_dir, state)
                                        cleanup_group_worktrees(repo, run_dir, state, int(_active_num),
                                                                 str(_gstate.get("failed")))
                                        print("PROGRAM_TECHNICAL_STALLED")
                                        print_terminal_summary(state, run_dir)
                                        lock.release()
                                        return 30
                                    if _result.get("owner_route"):
                                        _route = _result["owner_route"]
                                        _owner, _owner_state = str(_route["owner"]), str(_route.get("owner_state") or "")
                                        _data = read_json_file(repo / _route["findings_path"]) or {}
                                        _rk = owner_route_key(str(_route["from"]), _owner, _data)
                                        _rc = state.setdefault("owner_route_counts", {})
                                        _rc[_rk] = int(_rc.get(_rk, 0)) + 1
                                        # The group attempt is invalid: no candidate, fresh base on rerun.
                                        cleanup_group_worktrees(repo, run_dir, state, int(_active_num), f"owner-route:{_owner}")
                                        _hist = list(_gstate.get("owner_routes") or []) + [{**_route, "at": utcnow()}]
                                        state["parallel_groups"][str(int(_active_num))] = {"owner_routes": _hist}
                                        state.pop("active_parallel_group", None)
                                        if _rc[_rk] >= AC_MAX_IDENTICAL_RECOVERY:
                                            state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                                          "phase": "stalled", "stall_reason": "owner_route_no_progress",
                                                          "current_wave": str(_route["from"])})
                                            save_state(run_dir, state)
                                            print("PROGRAM_TECHNICAL_STALLED")
                                            print_terminal_summary(state, run_dir)
                                            lock.release()
                                            return 30
                                        _prior_closed = bool(state.get("closed_owner_repair"))
                                        state.setdefault("owner_stack", []).append({
                                            "blocked_target": str(_route["from"]), "owner": _owner,
                                            "findings_path": _route["findings_path"], "blocked_phase": "run",
                                            "prior_closed_owner_repair": _prior_closed, "parallel_group": int(_active_num)})
                                        state["target_override"] = _owner
                                        state["closed_owner_repair"] = _prior_closed or _owner_state == "done"
                                        state["findings_path"] = _route["findings_path"]
                                        findings_path = repo / _route["findings_path"]
                                        bump_progress_epoch(state, "parallel_owner_route")
                                        append_event(run_dir, {"event": "closed_owner_true_route" if _owner_state == "done" else "true_owner_route",
                                                               "from": _route["from"], "to": _owner, "owner_state": _owner_state,
                                                               "findings": _route["findings_path"], "parallel_group": int(_active_num)})
                                        phase = "repair" if _owner_state == "done" else "reconcile"
                                        state["phase"] = phase
                                        target_cache = None
                                        save_state(run_dir, state)
                                        continue
                                    _cands = _result.get("candidates") or {}
                                    _worktrees = {wid: workspace_engine.channel_workspace(repo, run_dir.name, int(_active_num), wid) for wid, _ in _active_members}
                                    _integ = integrate_parallel_candidates(
                                        repo=repo, profile=profile, run_dir=run_dir, program=program,
                                        group=int(_active_num), members=_active_members, candidates=_cands,
                                        worktrees=_worktrees, frozen=_frozen if isinstance(_frozen, dict) else {},
                                    )
                                    if not _integ.get("ok"):
                                        _gstate["failed"] = str(_integ.get("reason"))
                                        state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                                                      "phase": "stalled", "stall_reason": str(_integ.get("reason") or "parallel_integration_failed"),
                                                      "current_wave": str(_active_members[0][0])})
                                        save_state(run_dir, state)
                                        cleanup_group_worktrees(repo, run_dir, state, int(_active_num),
                                                                f"integration-failed:{_integ.get('reason')}")
                                        print("PROGRAM_TECHNICAL_STALLED")
                                        print_terminal_summary(state, run_dir)
                                        lock.release()
                                        return 30
                                    _gstate["integrated"] = True
                                    _gstate["candidates"] = sorted(_cands.keys(), key=engine_wave_sort_key)
                                    observe_controller_provenance(repo, profile, run_dir, state, record=True)
                                    state.pop("active_parallel_group", None)
                                    save_state(run_dir, state)
                                    # Promotion is durable; candidates live in the object store + manifests.
                                    cleanup_group_worktrees(repo, run_dir, state, int(_active_num), "integrated")
                                    # Fall through to serial audit/close for the integrated members.
                                    continue
            # Single-channel groups and serial programs use the serial lifecycle below.


        target, wave_path, canonical = current_target(repo, project, override, allow_closed_owner_repair=bool(state.get("closed_owner_repair")))
        # Serial barrier gate: a later group is never eligible while an
        # earlier scheduled group has any non-DONE channel (pending, blocked,
        # or postponed). Redirect to the active group's actionable member.
        if target is not None and wave_path is not None and not override:
            try:
                _gate_active = active_scheduled_group(repo, profile)
            except Exception:
                _gate_active = None
            if _gate_active is not None:
                try:
                    _tnum = int(engine_wave_number_of(str(target)))
                except ValueError:
                    _tnum = None
                if _tnum is not None and int(_gate_active[0]) < int(_tnum):
                    _members = list(_gate_active[1])
                    _redirect = None
                    for _state_name in ("blocked", "postponed", "pending"):
                        cands = sorted([w for w, s in _members if s == _state_name], key=engine_wave_sort_key)
                        if cands:
                            _redirect = cands[0]
                            break
                    if _redirect is not None:
                        _rpath, _rstate = engine_wave_location(repo, profile, str(_redirect))
                        if _rpath is not None:
                            append_event(run_dir, {"event": "serial_group_barrier_redirect", "withheld": str(target),
                                                   "active_group": int(_gate_active[0]), "redirect": str(_redirect),
                                                   "redirect_state": str(_rstate)})
                            target, wave_path = str(_redirect), _rpath
                            try:
                                _rmeta = wave_metadata(wave_path, profile)
                                canonical = str(_rmeta.get("canonical_source") or "") or None
                            except Exception:
                                pass
                            target_cache = None
        if target is None or wave_path is None:
            seq += 1; state["seq"] = seq
            post_ok, post_reasons, post_path = run_postrun_checks(repo, profile, run_dir, seq)
            seq += 1; state["seq"] = seq
            ok, final_reasons, final_path, failed_wave = final_program_validation(repo, profile, run_dir, seq)
            all_reasons = [*post_reasons, *final_reasons]
            append_event(run_dir,{"event":"final_program_validation","can_close":post_ok and ok,
                                  "postrun_output":str(post_path.relative_to(repo)),
                                  "validator_output":str(final_path.relative_to(repo)),"reasons":all_reasons})
            if not (post_ok and ok):
                repair_owner = final_repair_owner(repo, profile, failed_wave, state)
                if repair_owner:
                    _owner_path, owner_state = engine_wave_location(repo, profile, repair_owner)
                    state.update({"terminal":False,"terminal_class":"PROGRAM_FINAL_VALIDATION_BLOCKED",
                                  "target_override":repair_owner,"closed_owner_repair":owner_state == "done",
                                  "current_wave":repair_owner,"phase":"repair",
                                  "final_validation_path":str(final_path.relative_to(repo))})
                    findings_path = run_dir / f"{seq:04d}-{repair_owner}-final-validation-findings.json"
                    write_json(findings_path,{"blocked_wave":repair_owner,"canonical_source":failed_wave,
                        "findings":[{"finding_id":f"FINAL_VALIDATION::{failed_wave or repair_owner}",
                                     "execution_owner":repair_owner,"owner_state":owner_state or "unknown",
                                     "classification":"repository-owned","human_only":False,"summary":r}
                                    for r in all_reasons]})
                    state["findings_path"] = str(findings_path.relative_to(repo))
                    bump_progress_epoch(state, "final_validation_owner_route")
                    target_cache=None; phase="repair"; save_state(run_dir,state); continue
                # A repository-owned final-validation defect is never a program terminal.
                # With no resolvable Wave owner, keep the controller alive at a
                # reconciliation boundary and require deeper controller diagnosis.
                append_event(run_dir,{"event":"FINAL_VALIDATION_OWNER_UNRESOLVED","reasons":all_reasons})
                key = "final_validation_owner_unresolved::" + repository_content_identity(repo, profile) + "::" + "|".join(sorted(all_reasons))
                recovery_counts = state.setdefault("recovery_counts", {})
                recovery_counts[key] = int(recovery_counts.get(key, 0)) + 1
                if recovery_counts[key] >= AC_MAX_IDENTICAL_RECOVERY:
                    state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","current_wave":None,
                                  "phase":"stalled","final_validation_path":str(final_path.relative_to(repo)),
                                  "stall_reason":"final_validation_owner_unresolved"})
                    save_state(run_dir,state); append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","key":key,"count":recovery_counts[key]})
                    print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
                bump_progress_epoch(state, "final_validation_owner_unresolved")
                state.update({"terminal":False,"terminal_class":"PROGRAM_FINAL_VALIDATION_BLOCKED","current_wave":None,
                              "phase":"reconcile","final_validation_path":str(final_path.relative_to(repo))})
                save_state(run_dir,state); time.sleep(1); continue
            state.update({"terminal":True,"terminal_class":"PROGRAM_COMPLETE","current_wave":None,"phase":"done",
                          "final_validation_path":str(final_path.relative_to(repo))})
            save_state(run_dir,state); append_event(run_dir,{"event":"program_complete","final_validation":str(final_path.relative_to(repo))})
            print("PROGRAM_COMPLETE"); print_terminal_summary(state, run_dir); lock.release(); return 0


        if target_cache != target:
            target_cache = target
            preserve_direct_owner_repair = bool(
                state.get("target_override") and state.get("closed_owner_repair")
                and phase == "repair" and findings_path is not None
            )
            if not preserve_direct_owner_repair:
                phase = "reconcile"
            if not state.get("target_override"): findings_path = None
            no_progress = False


        _canonical_path, target_state = wave_location(repo, project, target)
        meta = wave_metadata(wave_path, profile)
        content_identity = implementation_identity(repo, profile)
        state.update({"current_wave":target,"wave_file":str(wave_path.relative_to(repo)),"wave_state":target_state,
                      "canonical_source_wave":canonical,"phase":phase,"target_cache":target_cache,
                      "content_identity":content_identity})
        try:
            _entry = ensure_wave_entry(state, target, meta)
            if str(meta.get("wave_title") or "").strip():
                _entry["wave_title"] = str(meta["wave_title"]).strip()
            if target_state != "done":
                _entry.setdefault("execution_state", "active")
        except Exception:
            pass
        save_state(run_dir,state)


        receipt_valid = audit_receipt_valid(repo, profile, target, state, content_identity)
        if not receipt_valid and phase == "reconcile":
            recovered = recover_allowlisted_audit_receipt(repo, run_dir, profile, target, content_identity)
            if recovered:
                state.update(recovered)
                save_state(run_dir, state)
                receipt_valid = True
                append_event(run_dir, {"event": "audit_receipt_recovered_from_allowlisted_handoff",
                                       "target": target, "audit_result_path": recovered["audit_result_path"]})
        if phase == "close" and not receipt_valid:
            append_event(run_dir,{"event":"audit_receipt_invalid_before_close","target":target,
                                  "tested_content_identity":state.get("tested_content_identity"),
                                  "current_content_identity":content_identity,
                                  "audit_result_path":state.get("audit_result_path")})
            phase="audit"; state["phase"]=phase; save_state(run_dir,state); continue
        if phase == "reconcile" and receipt_valid:
            append_event(run_dir,{"event":"fresh_audit_receipt_precedes_historical_report","target":target,
                                  "audit_result_path":state.get("audit_result_path"),
                                  "tested_content_identity":content_identity})
            phase="close"; state["phase"]=phase; save_state(run_dir,state); continue

        # Progress contract v2: RUN/REPAIR never start without the Wave's validated
        # structured TODO plan (reconcile/report inference or owner routing may skip
        # PLAN). Run PLAN first, then resume the requested phase (repair keeps its
        # findings context). Same helper and semantics as the parallel path: only
        # an accepted plan passes, so `pending` and `rejected` both force PLAN.
        _plan_state = v2_plan_gate_violation(state, ensure_wave_entry(state, target, meta), phase)
        if _plan_state is not None:
            append_event(run_dir, {"event": "v2_plan_required_before_phase", "target": target,
                                   "requested_phase": phase, "todo_plan_state": _plan_state,
                                   "contract": effective_contract_version(state)})
            state["resume_phase_after_plan"] = {"target": target, "phase": phase}
            phase = "plan"; state["phase"] = phase; save_state(run_dir, state); continue


        active_job = {}
        active_rel = state.get("active_phase_job")
        if isinstance(active_rel, str) and active_rel.strip():
            active_job = read_phase_job(repo / active_rel)
        _expected_instance = ((state.get("waves") or {}).get(str(target)) or {}).get("phase_instance_id")
        if serial_job_is_current(active_job, target=target, phase=phase, program=program,
                                 run_id=run_dir.name, phase_instance_id=_expected_instance):
            seq = int(active_job.get("seq") or state.get("seq") or seq)
            state["seq"] = seq
            append_event(run_dir,{"event":"managed_phase_job_attach","target":target,"phase":phase,
                                  "job":active_rel,"pid":active_job.get("pid")})
        else:
            if active_rel:
                # Never drop a possibly-live child from accounting: wait for it
                # before a replacement can start in the same tree.
                if not settle_foreign_phase_job(repo, run_dir, repo / active_rel, reason=f"not current {target}/{phase}"):
                    state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                                  "stall_reason":f"unresolved_managed_child:{active_rel}","current_wave":target})
                    save_state(run_dir,state); append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","reason":state["stall_reason"]})
                    print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
                state["active_phase_job"] = None
                state["active_phase_pid"] = None
            seq += 1; state["seq"] = seq
        save_state(run_dir, state)
        print(f"\n[program] target={target} phase={phase} backend={args.backend}\n", flush=True)


        if phase == "reconcile" and state.get("target_override"):
            inferred = infer_reconcile_phase(repo, project, target)
            if inferred == "reconcile":
                frame = state.get("owner_stack", []).pop() if state.get("owner_stack") else None
                remaining = state.get("owner_stack", [])
                state["target_override"] = (frame.get("blocked_target") if isinstance(frame,dict) and remaining else None)
                target_cache=None
                findings_path=(repo/frame["findings_path"]) if isinstance(frame,dict) and frame.get("findings_path") else None
                state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
                state["phase"]="reconcile"; save_state(run_dir,state); continue
            phase=inferred; state["phase"]=phase; save_state(run_dir,state); continue


        fingerprint_blocker = (None if phase in {"repair", "reconcile"}
                               or job_matches(active_job, target=target, phase=phase, program=program)
                               else canonical_fingerprint_blocker(repo, wave_path))
        if fingerprint_blocker:
            # Fail closed before any worker runs: no model can report READY/PASS over spec drift.
            append_event(run_dir,{"event":"canonical_fingerprint_preflight_blocked","target":target,"phase":phase,"detail":fingerprint_blocker})
            result={"status":"BLOCKED","summary":"Canonical source fingerprint preflight failed",
                    "findings":[fingerprint_blocker],"changed_files":[],"next_action":"repair"}
        elif args.backend == "codex":
            # Codex model is passed explicitly (--model) or is the CLI default, reported as unknown.
            codex_route = resolve_phase_route(repo, program, phase, "codex", args.model)
            print(f"[dispatch] {target} {phase.upper()} started | {format_route(codex_route)}", flush=True)
            append_event(run_dir, {"event": "phase_dispatch", "run_id": run_dir.name, "wave": target, "phase": phase,
                                   "role": codex_route["role"], "backend": "codex",
                                   "requested_model": codex_route["model"], "effective_model": codex_route["model"],
                                   "requested_thinking": codex_route["thinking"], "effective_thinking": codex_route["thinking"]})
            state.setdefault("route_history", []).append({"role": codex_route["role"], "model": codex_route["model"],
                                                          "thinking": codex_route["thinking"], "fallback": False})
            result = codex_exec(repo,run_dir,project,target,wave_path,phase,canonical,findings_path,args.model,no_progress,seq,state)
        else:
            if phase == "reconcile":
                inferred=infer_reconcile_phase(repo,project,target)
                if inferred == "reconcile" and state.get("target_override"):
                    frame=state.get("owner_stack",[]).pop() if state.get("owner_stack") else None
                    remaining=state.get("owner_stack",[])
                    state["target_override"]=(frame.get("blocked_target") if isinstance(frame,dict) and remaining else None)
                    phase="reconcile"; target_cache=None
                    findings_path=(repo/frame["findings_path"]) if isinstance(frame,dict) and frame.get("findings_path") else None
                    state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
                    state["phase"]=phase; save_state(run_dir,state); continue
                phase="plan" if inferred=="reconcile" else inferred
                state["phase"]=phase; save_state(run_dir,state); continue
            controller_context_path = phase_controller_context(
                repo, run_dir, seq, target, phase, content_identity, state, findings_path
            )
            result=opencode_phase(repo,target,phase,seq,run_dir,program,state,controller_context_path)

        # Progress contract v2: a PLAN READY without a valid structured TODO
        # block is a worker contract violation -> orchestration recovery
        # (bounded by recovery_counts), never a silent legacy fallback.
        if phase == "plan" and str(result.get("status","")).upper() in {"READY","PASS"}:
            _contract = int(state.get("progress_contract_version") or 1)
            _verdict = evaluate_plan_todo(plan_output_text(repo, result), _contract)
            if _verdict["violation"]:
                ensure_wave_entry(state, target, None)["todo_plan_state"] = TODO_PLAN_REJECTED
                append_event(run_dir, {"event":"wave_todo_plan_rejected","wave":target,"contract":_contract,
                                       "error":_verdict["error"]})
                result = {"status":"ORCHESTRATION_RECOVERY_REQUIRED",
                          "summary":f"PLAN violated progress contract v{_contract}: {_verdict['error']}",
                          "findings":[str(_verdict["error"])],"changed_files":[],"next_action":"reconcile",
                          "phase_log_path":result.get("phase_log_path")}


        aggregate_validator: Path | None = None
        if phase == "close" and str(result.get("status","")).upper() == "PASS" and aggregate_validation_required(profile,meta,phase):
            aggregate_validator = run_validator(repo, profile, canonical, run_dir, seq)
            can_close, reasons = validator_can_close(aggregate_validator)
            append_event(run_dir,{"event":"aggregate_validator_gate","target":target,"canonical":canonical,"can_close":can_close,"reasons":reasons})
            if not can_close:
                result={"status":"BLOCKED","summary":"Controller aggregate validator rejected source closeout",
                        "findings":reasons or ["aggregate validator can_close=false"],"changed_files":[],"next_action":"repair"}


        if (phase == "audit" and str(result.get("status","")).upper() == "PASS" and target_state == "done"
                and state.get("target_override") == target and aggregate_validation_required(profile, meta, "close")):
            # A closed aggregate owner hands control back only when its canonical source is green;
            # audit prose alone would re-route the blocked Wave back here forever.
            aggregate_validator = run_validator(repo, profile, canonical, run_dir, seq)
            gate_ok, gate_reasons = validator_can_close(aggregate_validator)
            append_event(run_dir,{"event":"closed_owner_aggregate_gate","owner":target,"canonical":canonical,"can_close":gate_ok,"reasons":gate_reasons})
            if not gate_ok:
                result={"status":"REOPEN","summary":"Closed aggregate owner audit PASS but canonical aggregate validator is red",
                        "findings":gate_reasons or ["aggregate validator can_close=false"],"changed_files":[],"next_action":"repair"}


        reverted = revert_worker_lifecycle_mutation(repo, project, target, phase, str(result.get("status","")), target_state, wave_path)
        if reverted:
            append_event(run_dir,{"event":"worker_lifecycle_mutation_reverted","target":target,"phase":phase,**reverted})
            print(f"[lifecycle] {target} {phase.upper()} worker moved the Wave to done; reverted (controller-owned transition)", flush=True)


        if phase == "close" and str(result.get("status","")).upper() == "PASS":
            post_identity=implementation_identity(repo,profile)
            if state.get("tested_content_identity") and post_identity != state.get("tested_content_identity"):
                result={"status":"BLOCKED","summary":"Implementation content changed after the fresh audit",
                        "findings":["tested_content_identity no longer matches current implementation content"],
                        "changed_files":result.get("changed_files",[]),"next_action":"audit"}


        append_event(run_dir,{"event":"phase_result","target":target,"phase":phase,"result":result})
        normalized=run_dir/f"{seq:04d}-{target}-{phase}-normalized.json"
        # Same persistence boundary as persist_fresh_audit_report: a worker's prose can quote
        # whatever its tooling printed, including this machine's scratch-output paths. Redact
        # here too so a receipt can never reintroduce what the hygiene validator refuses.
        normalized.write_text(
            _redact_environment_paths(json.dumps(result,ensure_ascii=False,indent=2))+"\n",
            encoding="utf-8")
        if phase == "audit" and str(result.get("status", "")).upper() == "PASS":
            audit_report = persist_fresh_audit_report(repo, project, target, result, normalized)
            if audit_report is not None:
                state["audit_report_path"] = str(audit_report.relative_to(repo))
                append_event(run_dir,{"event":"audit_report_persisted","target":target,
                                      "path":state["audit_report_path"],
                                      "normalized":str(normalized.relative_to(repo))})
                save_state(run_dir,state)
        print_phase_result_summary(target, phase, result, normalized, repo)
        try:
            apply_phase_result_to_progress(state, run_dir, repo, target, phase, result)
        except Exception as exc:
            append_event(run_dir, {"event": "wave_progress_error", "wave": target, "detail": str(exc)[:500]})
        active_rel = state.get("active_phase_job")
        if isinstance(active_rel, str) and active_rel.strip():
            mark_phase_job_result(repo / active_rel, status=str(result.get("status", "FAIL")),
                                  result_path=str(normalized.relative_to(repo)), consumed=True)
            state["active_phase_job"] = None
            state["active_phase_pid"] = None
            save_state(run_dir, state)


        current_controller_fingerprint = controller_runtime_fingerprint(repo, profile)
        if current_controller_fingerprint != controller_boot_fingerprint:
            state.update({"phase":"reconcile","controller_restart_required":True,"last_phase_result":str(normalized.relative_to(repo))})
            save_state(run_dir,state)
            append_event(run_dir,{"event":"controller_restart_boundary","target":target,"phase":phase})
            lock.release()
            os.execv(sys.executable, [sys.executable, *sys.argv])


        post_phase_identity = implementation_identity(repo, profile)
        observe_controller_provenance(repo, profile, run_dir, state, record=True)
        if post_phase_identity != content_identity:
            prior_identity = content_identity
            content_identity = post_phase_identity
            state["content_identity"] = post_phase_identity
            bump_progress_epoch(state, "content_change")
            append_event(run_dir,{"event":"content_identity_progress","target":target,"phase":phase,
                                  "before":prior_identity,"after":post_phase_identity,
                                  "progress_epoch":int(state.get("progress_epoch",0))})
            save_state(run_dir,state)

        status=str(result.get("status","")).upper()
        if phase == "audit" and status != "PASS":
            for key in ("audit_status", "audit_result_path", "audit_candidate_sha", "audit_passed_at"):
                state.pop(key, None)
        if result.get("provider_quota"):
            # External provider quota/rate limit: wait, never spend the identical-recovery budget.
            wait = state.setdefault("provider_wait", {"attempts": 0, "waited": 0})
            delay = provider_wait_delay(int(wait["attempts"]))
            if int(wait["waited"]) + delay > AC_MAX_PROVIDER_WAIT_SECONDS:
                state.update({"terminal":True,"terminal_class":"PROGRAM_HUMAN_DEFERRED","phase":phase,
                              "stall_reason":"provider_quota_exhausted","current_wave":target})
                save_state(run_dir,state); append_event(run_dir,{"event":"PROVIDER_QUOTA_EXHAUSTED","target":target,"phase":phase,"waited":wait["waited"]})
                print("PROGRAM_HUMAN_DEFERRED"); print_terminal_summary(state, run_dir); lock.release(); return 20
            wait["attempts"] = int(wait["attempts"]) + 1; wait["waited"] = int(wait["waited"]) + delay
            append_event(run_dir,{"event":"provider_quota_wait","target":target,"phase":phase,"attempt":wait["attempts"],"delay":delay})
            print(f"[provider-wait] {target} {phase.upper()} provider quota/rate limit | retry in {delay}s | waited={wait['waited']}s/{AC_MAX_PROVIDER_WAIT_SECONDS}s", flush=True)
            state["phase"]=phase; save_state(run_dir,state); time.sleep(delay); continue
        state.pop("provider_wait", None)
        if result.get("unresolved_child"):
            state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                          "stall_reason":f"unresolved_managed_child:{result['unresolved_child']}","current_wave":target})
            save_state(run_dir,state); append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","reason":state["stall_reason"]})
            print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
        if result.get("worker_timeout"):
            # Hung managed worker, terminated under the controller lease. Not a
            # transport retry and not a semantic iteration: deterministic stall.
            state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                          "stall_reason":f"managed_worker_timeout:{result['worker_timeout']}","current_wave":target})
            save_state(run_dir,state); append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","target":target,"phase":phase,
                                                             "reason":state["stall_reason"]})
            print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
        if status in {"MISSING_STATUS","ORCHESTRATION_RECOVERY_REQUIRED"}:
            append_event(run_dir,{"event":"orchestration_recovery","target":target,"phase":phase,"reason":result.get("summary")})
            recovery_key = f"transport::{target}::{phase}::{content_identity}::{status}"
            recovery_counts = state.setdefault("recovery_counts", {})
            recovery_counts[recovery_key] = int(recovery_counts.get(recovery_key, 0)) + 1
            if recovery_counts[recovery_key] >= AC_MAX_IDENTICAL_RECOVERY:
                state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                              "stall_reason":status,"current_wave":target})
                save_state(run_dir,state); append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","key":recovery_key,"count":recovery_counts[recovery_key]})
                print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
            state["phase"]=phase; state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
            save_state(run_dir,state); continue


        if status == "HUMAN_DEFERRED":
            if human_deferred_is_real(result):
                state.update({"terminal":True,"terminal_class":"PROGRAM_HUMAN_DEFERRED","phase":phase}); save_state(run_dir,state)
                print("PROGRAM_HUMAN_DEFERRED"); print(json.dumps(result,ensure_ascii=False,indent=2)); print_terminal_summary(state, run_dir); lock.release(); return 20
            result["status"]="BLOCKED"; status="BLOCKED"
            result.setdefault("findings",[]).append("Human deferral lacked a concrete external-authority dependency; keep as repository-owned repair.")


        if phase_result_bypasses_no_progress(phase, status):
            no_progress = False
            # A forward lifecycle commit is real progress: retire the durable
            # budget for this Wave so the next genuine blocker is measured from
            # zero rather than inheriting an already-spent allowance.
            _dkey = progress_no_progress_key(target, phase, result_fingerprint(target, phase, result),
                                             content_identity, int(state.get("progress_epoch", 0)))
            clear_progress_entry(repo, profile, program, _dkey)
            append_event(run_dir,{"event":"NO_PROGRESS_BYPASS_FOR_LIFECYCLE_COMMIT",
                                  "target":target,"phase":phase,"status":status,
                                  "progress_epoch":int(state.get("progress_epoch",0))})
            save_state(run_dir,state)
        else:
            semantic = result_fingerprint(target, phase, result)
            fp=progress_no_progress_key(target,phase,semantic,content_identity,int(state.get("progress_epoch",0)))
            count = account_no_progress_attempt(state, repo, profile, program, fp, run_dir.name)
            no_progress=count>=2
            if count>=2:
                append_event(run_dir,{"event":"NO_PROGRESS_CYCLE","target":target,"phase":phase,"semantic_finding":semantic,
                                      "content_identity":content_identity,"count":count,
                                      "progress_epoch":int(state.get("progress_epoch",0)),
                                      "durable":True})
                no_progress = True
                state["last_no_progress"] = {"target":target,"phase":phase,"semantic_finding":semantic,
                                             "content_identity":content_identity,"count":count,
                                             "durable":True}
            if count >= AC_MAX_IDENTICAL_RECOVERY:
                # Name the runs that contributed, so a stall caused by restarts is
                # diagnosable instead of looking like a single run's own doing.
                _runs = sorted({str(r) for r in (load_progress_ledger(repo, profile, program)
                                                 .get(fp, {}) or {}).get("seen_runs", [])})
                state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                              "stall_reason":"identical_no_progress_cycle","current_wave":target,
                              "no_progress_key":fp,"no_progress_count":count,
                              "no_progress_contributing_runs":_runs})
                save_state(run_dir,state)
                append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","target":target,"phase":phase,
                                      "semantic_finding":semantic,"content_identity":content_identity,"count":count})
                print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
            save_state(run_dir,state)


        next_phase=choose_after(phase,result)
        _resume = state.get("resume_phase_after_plan")
        if (phase == "plan" and status in {"READY","PASS"} and isinstance(_resume, dict)
                and str(_resume.get("target")) == str(target)):
            next_phase = str(_resume.get("phase") or next_phase)   # the phase the PLAN gate deferred
            state.pop("resume_phase_after_plan", None)
        routed=False
        if phase in {"audit","close"} and status != "PASS":
            report,audit=artifact_paths(repo,project,target)
            findings_path=route_findings(repo,run_dir,target,canonical,audit,aggregate_validator,seq,normalized)
            next_phase="repair"; routed=True
        if phase == "repair" and status not in {"READY_FOR_AUDIT","PASS","READY"}:
            report,audit=artifact_paths(repo,project,target)
            findings_path=route_findings(repo,run_dir,target,canonical,audit,None,seq,normalized)
            next_phase="repair"; routed=True


        if routed:
            data=read_json_file(findings_path) if findings_path else {}
            closed_owners=sorted({str(f.get("execution_owner")) for f in (data or {}).get("findings",[])
                                  if isinstance(f,dict) and str(f.get("owner_state","")).lower()=="done"})
            for owner in closed_owners:
                append_event(run_dir,{"event":"closed_owner_repair_transaction","owner":owner,"current_wave":target,
                                      "finding_ledger":str(findings_path.relative_to(repo)) if findings_path else None})
            owner=routed_owner(findings_path,target)
            if owner:
                owner_path,owner_state=wave_location(repo,project,owner)
                if owner_path is None:
                    append_event(run_dir,{"event":"owner_route_unresolved","target":target,"owner":owner})
                else:
                    stack=state.setdefault("owner_stack",[])
                    active_owners={str(frame.get("owner")) for frame in stack if isinstance(frame,dict)}
                    if owner == state.get("target_override") or owner in active_owners:
                        append_event(run_dir,{"event":"owner_route_cycle_guard","target":target,"owner":owner})
                    else:
                        # Each route bumps the epoch, so bound identical owner round trips separately:
                        # the same target->owner route with an unchanged finding set is no progress.
                        route_key = owner_route_key(target, owner, data)
                        route_counts = state.setdefault("owner_route_counts", {})
                        route_counts[route_key] = int(route_counts.get(route_key, 0)) + 1
                        if route_counts[route_key] >= AC_MAX_IDENTICAL_RECOVERY:
                            state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                                          "stall_reason":"owner_route_no_progress","current_wave":target})
                            save_state(run_dir,state)
                            append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","target":target,"owner":owner,
                                                  "route_key":route_key,"count":route_counts[route_key]})
                            print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
                        prior_closed = bool(state.get("closed_owner_repair"))
                        stack.append({"blocked_target":target,"owner":owner,
                                      "findings_path":str(findings_path.relative_to(repo)) if findings_path else None,
                                      "blocked_phase":phase,"prior_closed_owner_repair":prior_closed})
                        state["target_override"]=owner
                        state["closed_owner_repair"] = prior_closed or owner_state == "done"
                        state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
                        bump_progress_epoch(state, "closed_owner_route" if owner_state == "done" else "true_owner_route")
                        append_event(run_dir,{"event":"closed_owner_true_route" if owner_state == "done" else "true_owner_route",
                                              "from":target,"to":owner,"owner_state":owner_state,
                                              "findings":state["findings_path"]})
                        if phase == "audit":
                            # Finding accepted + owner routing final: one semantic iteration.
                            record_audit_reopen_transition(state, run_dir, target, status)
                        phase="repair" if owner_state == "done" else "reconcile"
                        state["phase"]=phase; target_cache=None; save_state(run_dir,state); continue


        if phase == "audit" and next_phase == "repair":
            # Classified semantic finding, routing final, lifecycle -> REPAIR.
            # Recovery/transport/provider outcomes already `continue`d above.
            record_audit_reopen_transition(state, run_dir, target, status)
        # Bounded recovery: a Wave that keeps consuming its no-progress budget
        # must stop the program, not only be labelled `stalled`. Without this the
        # per-Wave budget is a display value: a Wave can exceed it many times
        # over and the program keeps looping, because every other terminal path
        # is keyed on an identical fingerprint, an owner route or a worker
        # lease -- none of which fire for a Wave that keeps changing its
        # diagnosis slowly.
        _npe = ensure_wave_entry(state, target, None)
        _npcount = int(_npe.get("no_progress_count", 0) or 0)
        _nplimit = int(_npe.get("no_progress_limit", 3) or 3)
        if _npcount >= _nplimit:
            state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                          "phase": "stalled",
                          "stall_reason": f"wave_no_progress_budget_exhausted:{target}:{_npcount}/{_nplimit}",
                          "current_wave": target})
            save_state(run_dir, state)
            append_event(run_dir, {"event": "PROGRAM_TECHNICAL_STALLED", "target": target, "phase": phase,
                                   "reason": state["stall_reason"],
                                   "no_progress_count": _npcount, "no_progress_limit": _nplimit})
            print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
        # Controller-level no-meaningful-progress bound. The lease already bounds
        # a single worker; the controller itself must also be bounded, or a
        # program that keeps dispatching slow but non-identical work never
        # reaches a terminal classification on its own.
        _lease = engine_managed_job_lease(profile)
        _nmp = int(_lease.get("max_no_meaningful_progress_seconds", 0) or 0)
        if _nmp > 0:
            _last = _npe.get("last_meaningful_progress_ts")
            try:
                _idle = time.time() - float(_last) if _last is not None else 0.0
            except (TypeError, ValueError):
                _idle = 0.0
            if _idle > _nmp:
                state.update({"terminal": True, "terminal_class": "PROGRAM_TECHNICAL_STALLED",
                              "phase": "stalled",
                              "stall_reason": f"controller_no_meaningful_progress:{target}:{int(_idle)}s/{_nmp}s",
                              "current_wave": target})
                save_state(run_dir, state)
                append_event(run_dir, {"event": "PROGRAM_TECHNICAL_STALLED", "target": target, "phase": phase,
                                       "reason": state["stall_reason"],
                                       "idle_seconds": int(_idle), "limit_seconds": _nmp})
                print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
        if phase == "plan" and status in {"READY","PASS"}: state["last_planned_wave"]=target
        if phase == "audit" and status == "PASS":
            _aentry = ensure_wave_entry(state, target, None)
            progress_engine.complete_phase_todo(_aentry, "audit", str(_aentry.get("phase_instance_id") or ""), "PASS")
            state["tested_content_identity"] = implementation_identity(repo,profile)
            state["tested_wave"] = target
            state["audit_passed_at"] = utcnow()
            state["audit_status"] = "PASS"
            state["audit_result_path"] = str(normalized.relative_to(repo))
            state["audit_candidate_sha"] = project_git_head(repo)
            if state.get("target_override") == target and target_state == "done":
                frame=state.get("owner_stack",[]).pop() if state.get("owner_stack") else None
                append_event(run_dir,{"event":"historical_owner_revalidated","owner":target,"return_target":frame.get("blocked_target") if isinstance(frame,dict) else None})
                remaining=state.get("owner_stack",[])
                state["target_override"]=(frame.get("blocked_target") if isinstance(frame,dict) and remaining else None)
                state["closed_owner_repair"] = bool(frame.get("prior_closed_owner_repair")) if isinstance(frame,dict) else False
                bump_progress_epoch(state, "owner_audit_pass_return")
                target_cache=None
                findings_path=(repo/frame["findings_path"]) if isinstance(frame,dict) and frame.get("findings_path") else None
                state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
                phase="reconcile"; state["phase"]=phase; save_state(run_dir,state); continue


        if phase == "close" and status == "PASS":
            _centry = ensure_wave_entry(state, target, None)
            progress_engine.complete_phase_todo(_centry, "close", str(_centry.get("phase_instance_id") or ""), "PASS")
            save_state(run_dir, state)
            try:
                controller_close_wave(repo,profile,project,target)
            except RuntimeError as exc:
                append_event(run_dir,{"event":"close_lifecycle_guard_rejected","target":target,"detail":str(exc)})
                state["phase"]="reconcile"
                state["stall_reason"]="close_lifecycle_integrity_conflict"
                save_state(run_dir,state)
                phase="reconcile"
                time.sleep(1)
                continue
            _, closed_state=wave_location(repo,project,target)
            if closed_state != "done":
                raise RuntimeError(f"Close PASS for {target} did not produce canonical CLOSED/done lifecycle state")
            engine_reconcile_active_wave_tracker(
                repo, profile, reason=f"Wave {target} closed; next pending execution wave."
            )
            indexed = engine_reconcile_waves_index(repo, profile)
            if indexed:
                append_event(run_dir,{"event":"waves_index_reconciled","target":target,"added":indexed})
            state["last_closed_wave"]=target
            observe_controller_provenance(repo, profile, run_dir, state, record=True)
            # Terminal Wave: no controller-completed phase may leave a live TODO.
            _stale = [t for t in _centry.get("todos") or [] if str(t.get("status")) in {"pending", "in_progress"}]
            for _t in _stale:
                _t["status"] = "cancelled"
                _t["detail"] = "superseded: Wave closed by controller"
            if _stale:
                append_event(run_dir, {"event": "wave_todo_superseded_on_close", "wave": target,
                                       "todos": [str(t.get("id")) for t in _stale]})
            _centry["execution_state"] = "done"
            state["closure_content_identity"]=implementation_identity(repo,profile)
            state["closure_commit_sha"] = project_git_head(repo)
            if state.get("target_override") == target:
                frame=state.get("owner_stack",[]).pop() if state.get("owner_stack") else None
                remaining=state.get("owner_stack",[])
                state["target_override"]=(frame.get("blocked_target") if isinstance(frame,dict) and remaining else None)
                state["closed_owner_repair"] = bool(frame.get("prior_closed_owner_repair")) if isinstance(frame,dict) else False
                findings_path=(repo/frame["findings_path"]) if isinstance(frame,dict) and frame.get("findings_path") else None
            else:
                findings_path=None
            bump_progress_epoch(state, "wave_close_pass")
            target_cache=None; next_phase="reconcile"


        phase=next_phase
        state["phase"]=phase; state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
        state["target_cache"]=target_cache; state["seq"]=seq; save_state(run_dir,state)




if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("OPERATOR_CANCELLED", file=sys.stderr)
        raise SystemExit(130)
