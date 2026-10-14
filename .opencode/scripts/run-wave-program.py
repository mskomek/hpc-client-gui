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
# Shared transport primitives are implemented in the phase runtime; these
# imports intentionally preserve the runner-facing compatibility surface.
import controller_phase_runtime as _phase_runtime
import _scoped_write_guards as _scoped_guards
from controller_phase_runtime import (
    AC_MAX_TRANSPORT_ATTEMPTS,
    AC_MAX_PROVIDER_WAIT_SECONDS,
    PROVIDER_QUOTA_MARKER,
    provider_wait_delay,
    run_stream,
)
# --- W46 U02 replay why/cross-run re-export (AC-REPLAY-021/022; canonical home wave_run_replay) ---
from wave_run_replay import explain_transition as explain_transition, render_cross_run_view as render_cross_run_view
AC_MAX_IDENTICAL_RECOVERY = 3
MANUAL_MODEL_MARKER = "AC_WAVE_MANUAL_MODEL_CHANGE_REQUIRED:"
AC_PROVIDER_MODEL_COOLDOWN_SECONDS = int(os.environ.get("AC_PROVIDER_MODEL_COOLDOWN_SECONDS", "3600"))
AC_MAX_WAVE_REPAIRS = int(os.environ.get("AC_MAX_WAVE_REPAIRS", "12"))
AC_MAX_SEMANTIC_PROBLEM_CYCLES = int(os.environ.get("AC_MAX_SEMANTIC_PROBLEM_CYCLES", "4"))
# Wave W21 U01: the Wave-wide repair budget above is a secondary exceptional
# guard only (see the WAVE_REPAIR_BUDGET_EXHAUSTED stall path). The primary
# ordinary-repair accounting key is (leaf_id, semantic_problem_id) recorded in
# per-leaf first-pass telemetry (controller_state.ensure_first_pass_telemetry
# and record_leaf_*). A second fresh audit reporting the same leaf+problem
# must not enter another ordinary repair; the controller selects reslice,
# replan, owner routing, or a genuine human/environmental block instead.
# These constants declare that accounting intent; they change no routing,
# lifecycle, retry, or model-selection behavior.
PRIMARY_REPAIR_ACCOUNTING_KEY = ("leaf_id", "semantic_problem_id")
WAVE_REPAIR_BUDGET_ROLE = "secondary-exceptional-guard"
# --- W21 U02 leaf+problem ordinary-repair ceiling (pure gate) ---------------
# Pure predicates only; the controller loop consults these before dispatch.
def may_ordinary_repair(audits: Any, repairs: Any) -> bool:
    """Exactly one ordinary repair: first fresh audit only, zero repairs yet."""
    try:
        return int(audits) == 1 and int(repairs) == 0
    except (TypeError, ValueError):
        return False

def ordinary_repair_allowed(entry: Any, leaf_id: str, problem_id: str) -> bool:
    """Gate one leaf+problem pair; unseen pairs keep their first opportunity."""
    try:
        table = (entry or {}).get("leaf_telemetry") or {}
        rec = table.get(str(leaf_id or "").strip().upper()) or {}
        item = (rec.get("problems") or {}).get(str(problem_id or "").strip())
        if not isinstance(item, dict):
            return True
        return may_ordinary_repair(item.get("audits"), item.get("repairs"))
    except Exception:
        return False

def select_structural_after_ceiling(classification: str = "",
                                    has_units: bool = False,
                                    owner_mismatch: bool = False,
                                    genuine_block: bool = False) -> str:
    """Structural branch once ordinary repair is forbidden (pure, never raises)."""
    try:
        if bool(genuine_block):
            return "genuine-block"
        if bool(owner_mismatch) or str(classification or "").strip().upper() == "OWNER_MISMATCH":
            return "owner-route"
        if str(classification or "").strip().upper() == "DECOMPOSITION_DEFECT" and bool(has_units):
            return "reslice"
        return "replan"
    except Exception:
        return "replan"

# W21 U01 per-leaf record sites live in _runner_first_pass_telemetry (canonical home);
# the same-name imports below keep runner.<name> importable unchanged.
from _runner_first_pass_telemetry import (
    _first_pass_state_module, _capacity_module, _origin_store,
    note_first_pass_dispatch, note_first_pass_audit, note_first_pass_repair,
    note_first_pass_structural, note_first_pass_scope_signal, note_first_pass_failure,
    project_first_pass_telemetry, _first_pass_leaf_id, _first_pass_entry)
from controller_risk_record import refresh_integration_risk as refresh_integration_risk  # W37 U03 risk-refresh home; keeps runner.refresh_integration_risk importable.
from controller_close_gate import decide_ship_close as decide_ship_close  # W39 U03 close-requires-current-plan home; keeps runner.decide_ship_close importable.
from controller_race_plan import build_race_plan as build_race_plan  # W40 U02 frozen race-plan home; keeps runner.build_race_plan importable.
from controller_race_promotion import RACE_PROMOTION_VERSION as RACE_PROMOTION_VERSION  # W42 U02 winner-promotion home; keeps runner.RACE_PROMOTION_VERSION importable.
from controller_race_promotion import reconfirm_race_winner as reconfirm_race_winner  # W42 U02 winner reconfirmation; keeps runner.reconfirm_race_winner importable.
from controller_race_promotion import require_race_promotion_route as require_race_promotion_route  # W42 U02 transactional-route gate; keeps runner.require_race_promotion_route importable.
from controller_race_promotion import examine_promotion_gates as examine_promotion_gates  # W42 U02 promotion gate checklist; keeps runner.examine_promotion_gates importable.
from controller_race_promotion import record_race_promotion as record_race_promotion  # W42 U02 promotion record; keeps runner.record_race_promotion importable.
from controller_scan_contracts import SCAN_CONTRACT_VERSION as SCAN_CONTRACT_VERSION, build_scan_contract as build_scan_contract, validate_scan_contract as validate_scan_contract, freeze_scan_contract as freeze_scan_contract, scan_contract_id as scan_contract_id, is_scan_contract_current as is_scan_contract_current, normalize_scan_finding as normalize_scan_finding, validate_scan_finding as validate_scan_finding, reduce_scan_findings as reduce_scan_findings, check_scan_coverage_obligations as check_scan_coverage_obligations  # W43 U03 scan contracts home; keeps runner.<name> importable.
def _observe_first_pass_outcome(entry: dict[str, Any], phase: str, result: Any, leaf_id: str) -> None:
    """Count audit/repair/structural/failure outcomes best-effort; never raises or gates."""
    try:
        if not isinstance(entry, dict) or not isinstance(result, dict):
            return
        handoff = result.get("handoff") if isinstance(result.get("handoff"), dict) else {}
        status = str(result.get("status") or "").strip().upper()
        problem = str(result.get("semantic_problem_id") or handoff.get("semantic_problem_id") or "").strip()
        name = str(phase or "").lower()
        if name == "audit" and status:
            note_first_pass_audit(entry, leaf_id, status, problem or None)
        elif name in {"repair", "repair_plan"} and status in {"READY", "READY_FOR_AUDIT", "READY_FOR_REPAIR"}:
            note_first_pass_repair(entry, leaf_id, problem or None)
        nxt = str(result.get("next_action") or handoff.get("next_action") or "").strip().lower()
        if nxt in {"reslice", "replan"}:
            note_first_pass_structural(entry, leaf_id, nxt)
        if str(result.get("audit_classification") or "").strip().upper() in {"SCOPE_MISS", "PLAN_DEFECT"}:
            note_first_pass_scope_signal(entry, leaf_id)
        if status in {"BLOCKED", "FAIL", "ORCHESTRATION_RECOVERY_REQUIRED"}:
            _origin_store().record_leaf_failure_with_origin(entry, leaf_id, result)
        _capacity_module().observe_outcome(entry, name, result)
        node_engine.observe_sizing_feedback(entry, name, result,
                                            capacity_module=_capacity_module())
    except Exception:
        pass

def _with_first_pass_telemetry(state: dict[str, Any] | None, target: str, phase: str, fn, *, launch: dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
    """Dispatch wrapper: split-or-refuse oversized unit_run leaves, then count and observe."""
    entry = _first_pass_entry(state, target)
    if entry is not None and str(phase or "").lower() == "run":
        refused = node_engine.pre_execution_refusal(entry)
        if refused is not None:
            _observe_first_pass_outcome(entry, phase, refused, _first_pass_leaf_id(entry))
            return refused
    leaf = _first_pass_leaf_id(entry)
    if entry is not None:
        note_first_pass_dispatch(entry, leaf)
    if entry is not None and str(phase or "").lower() in ("run", "repair"):
        # W30 U02: freeze the accepted packet before dispatch; fail closed
        # when the live packet no longer matches the frozen contract.
        frozen = node_engine.require_frozen_execution_contract(state, target, phase)
    else:
        frozen = None
    guard = None
    if launch is not None and frozen is not None and str((state or {}).get("executor_mode") or "delegated") != "direct":
        guard = _guard_launch_dispatch(run_dir=launch["run_dir"], repo=launch["repo"], backend=launch["backend"], program=launch["program"], seq=launch["seq"], target=target, phase=phase, entry=entry, frozen=frozen)
        if guard["duplicate"]:
            _event_identity.record_run_transition(entry, kind="reattach", wave_id=target, current_node=str((entry or {}).get("node") or "unit_run"), next_node=str(phase or "run"), reason_code="reattach-result-reuse", reason_evidence=[f"dispatch_id={guard['dispatch_id']}", "identical dispatch already active"], dispatch_id=str(guard.get("dispatch_id") or ""), contract_id=str((frozen or {}).get("contract_id") or ""))
            return {"status": "ORCHESTRATION_RECOVERY_REQUIRED", "summary": f"duplicate dispatch {guard['dispatch_id']} suppressed: identical dispatch already active; no second worker spawned", "findings": ["duplicate-dispatch-suppressed"], "changed_files": [], "next_action": "reconcile"}
    try:
        out = fn()
    except Exception:
        if entry is not None:
            _origin_store().record_leaf_failure_with_origin(entry, leaf, {"failure_class": "PROVIDER_TRANSPORT"})
        raise
    if guard is not None:
        _settle_launch_dispatch(repo=launch["repo"], state=state, guard=guard, out=out, entry=entry, phase=phase, target=target)
    if entry is not None:
        _observe_first_pass_outcome(entry, phase, out, leaf)
    return out

# Semantic node contracts are loaded from protocol/AC_WAVE_NODE_CONTRACTS.json.
# Model routing remains AC_MODELS authority; capacity may size work only.

# Wave W15 U02: wave_repairs_since_definition lives in controller_loop
# (canonical home); the same-name re-export below keeps runner.<name>
# importable with unchanged semantics.

# Model selection is manual-only. Capacity, quota and availability are
# observations; none of them may mutate the configured node route.

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from runner_domain_bindings import *  # noqa: F401,F403
from runner_orchestration_bindings import *  # noqa: F401,F403
_phase_contract.configure(globals())
bind_runner_namespace(globals())

# Forward lifecycle edge per phase. A result is forward progress only when
# choose_after() routes it along this edge, so the bypass can never drift from
# the controller's real routing table.

# Wave W15 U02: semantic_result_bypasses_no_progress lives in controller_loop
# (canonical home, verbatim move); the same-name import below keeps
# runner.semantic_result_bypasses_no_progress importable unchanged.

OWNER_ROUTING_RULE = _phase_contract.OWNER_ROUTING_RULE

# Every front end Agent Core supports. A front end that is not declared here is
# not a supported program, and the controller refuses to start rather than
# silently applying one front end's rules to another.
BACKENDS = ("codex", "claude", "opencode")

# Wave W15 U02: _cli_help and claude_exec_args live in controller_parallel
# (canonical home, identical logic); the same-name imports below keep
# runner.<name> importable with unchanged semantics.

# How a front end's own CLI is invoked. This is the only place a front end name
# may influence what runs; every decision above it stays backend-neutral.
BACKEND_TRANSPORTS = {
    "codex": codex_exec_args,
    "claude": claude_exec_args,
}

def codex_exec(repo: Path, run_dir: Path, project: str, target: str, wave_path: Path, phase: str,
               canonical: str | None, findings_path: Path | None, model: str | None,
               no_progress: bool, seq: int, state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Runner-compatible entrypoint; inject controller and monkeypatch seams explicitly."""
    dependencies = {name: globals()[name] for name in (
        "build_phase_prompt", "default_node_for_phase", "phase_controller_context", "read_json_file",
        "new_phase_instance_id", "codex_exec_args", "ensure_wave_entry", "progress_engine",
        "ensure_parallel_repair_todos", "controller_fallback_action", "save_state", "append_event",
        "drain_progress_deltas", "lease_violation", "utcnow", "run_stream", "read_text",
        "validate_result_object",
        "supervision_tick", "supervision_lease", "is_supervised_program",
        "PROVIDER_QUOTA_RE", "MODEL_UNAVAILABLE_RE", "HUMAN_RE", "CONFIG_RE", "TRANSIENT_RE") }
    dependencies["run_stream_diagnostics"] = _phase_runtime.run_stream
    return _with_first_pass_telemetry(
        state, target, phase,
        lambda: _phase_runtime.codex_exec(repo, run_dir, project, target, wave_path, phase, canonical,
            findings_path, model, no_progress, seq, state, dependencies=dependencies),
        launch={"repo": repo, "run_dir": run_dir, "backend": "codex", "program": "codex", "seq": seq})

ROLE_BY_PHASE = _phase_contract.ROLE_BY_PHASE
ROLE_BY_NODE = _phase_contract.ROLE_BY_NODE

SESSION_DISPOSITIONS = _phase_contract.SESSION_DISPOSITIONS
SESSION_EXECUTOR_NODES = _phase_contract.SESSION_EXECUTOR_NODES
SESSION_INDEPENDENT_NODES = _phase_contract.SESSION_INDEPENDENT_NODES
SESSION_RECOMMENDER_NODES = _phase_contract.SESSION_RECOMMENDER_NODES

session_workspace_identity = _phase_contract.session_workspace_identity

session_route_key = _phase_contract.session_route_key

_session_artifact_rel = _phase_contract._session_artifact_rel

_read_session_artifact = _phase_contract._read_session_artifact

_session_state = _phase_contract._session_state

_session_problem_counts = _phase_contract._session_problem_counts

_choose_executor_session = _phase_contract._choose_executor_session

_adaptive_session_prompt = _phase_contract._adaptive_session_prompt

session_dispatch_context = _phase_contract.session_dispatch_context

record_session_invocation = _phase_contract.record_session_invocation

record_session_recommendation = _phase_contract.record_session_recommendation

session_fresh_escape_after_failed_fork = _phase_contract.session_fresh_escape_after_failed_fork

configured_model_candidates = _phase_contract.configured_model_candidates

model_capacity_profile = _phase_contract.model_capacity_profile

node_phase = _phase_contract.node_phase

default_node_for_phase = _phase_contract.default_node_for_phase

resume_checkpoint_target = _phase_contract.resume_checkpoint_target

REPAIR_STRATEGY_RESUME_NODES = _phase_contract.REPAIR_STRATEGY_RESUME_NODES
REPAIR_HYPOTHESIS_NODES = _phase_contract.REPAIR_HYPOTHESIS_NODES

resume_node_for_phase = _phase_contract.resume_node_for_phase

reset_unit_plan_authority = _phase_contract.reset_unit_plan_authority

program_family = _phase_contract.program_family

split_model_thinking = _phase_contract.split_model_thinking

resolve_phase_route = _phase_contract.resolve_phase_route

route_divergence = _phase_contract.route_divergence

format_route = _phase_contract.format_route

print_program_routing = _phase_contract.print_program_routing

models_used_lines = _phase_contract.models_used_lines

def serial_job_is_current(job: dict[str, Any], *, target: str, phase: str, program: str,
                          run_id: str, phase_instance_id: str | None) -> bool:
    """Runner-compatible entrypoint; managed execution lives in the phase runtime."""
    dependencies = {name: globals()[name] for name in _phase_runtime.RUNNER_SERIAL_JOB_DEPENDENCIES}
    return _phase_runtime.serial_job_is_current(job, target=target, phase=phase, program=program,
                                                run_id=run_id, phase_instance_id=phase_instance_id,
                                                dependencies=dependencies)

def settle_foreign_phase_job(repo: Path, run_dir: Path, job_path: Path, reason: str) -> bool:
    """Runner-compatible entrypoint; managed execution lives in the phase runtime."""
    dependencies = {name: globals()[name] for name in _phase_runtime.RUNNER_SETTLE_JOB_DEPENDENCIES}
    return _phase_runtime.settle_foreign_phase_job(repo, run_dir, job_path, reason,
                                                      dependencies=dependencies)

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
    """Runner-compatible entrypoint; managed execution lives in the phase runtime."""
    dependencies = {name: globals()[name] for name in _phase_runtime.RUNNER_WAIT_JOB_DEPENDENCIES}
    return _phase_runtime.wait_phase_job_live(job_path=job_path, log_path=log_path, proc=proc, run_dir=run_dir,
                                              state=state, entry=entry, phase_instance_id=phase_instance_id,
                                              poll_seconds=poll_seconds, lease=lease,
                                              dependencies=dependencies)

def opencode_phase(repo: Path, target: str, phase: str, seq: int, run_dir: Path, program: str,
                   state: dict[str, Any], controller_context_path: Path | None = None) -> dict[str, Any]:
    """Runner-compatible entrypoint; managed execution lives in the phase runtime."""
    dependencies = {name: globals()[name] for name in _phase_runtime.RUNNER_OPENCODE_PHASE_DEPENDENCIES}
    return _with_first_pass_telemetry(
        state, target, phase,
        lambda: _phase_runtime.opencode_phase(repo, target, phase, seq, run_dir, program, state, controller_context_path,
                                            dependencies=dependencies),
        launch={"repo": repo, "run_dir": run_dir, "backend": "opencode", "program": program, "seq": seq})

def claude_phase(repo: Path, target: str, phase: str, seq: int, run_dir: Path, program: str,
                 state: dict[str, Any], controller_context_path: Path | None = None) -> dict[str, Any]:
    """Runner-compatible entrypoint; managed execution lives in the phase runtime."""
    dependencies = {name: globals()[name] for name in _phase_runtime.RUNNER_CLAUDE_PHASE_DEPENDENCIES}
    return _with_first_pass_telemetry(
        state, target, phase,
        lambda: _phase_runtime.claude_phase(repo, target, phase, seq, run_dir, program, state, controller_context_path,
                                          dependencies=dependencies),
        launch={"repo": repo, "run_dir": run_dir, "backend": "claude", "program": program, "seq": seq})

controller_audit_finding = _phase_contract.controller_audit_finding

WAVE_LEDGER_PRIOR_RUNS = _phase_contract.WAVE_LEDGER_PRIOR_RUNS

wave_ledger = _phase_contract.wave_ledger

phase_controller_context = _phase_contract.phase_controller_context

_strip_ansi = _phase_contract._strip_ansi

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

_redact_environment_paths = _phase_contract._redact_environment_paths

persist_fresh_audit_report = _phase_contract.persist_fresh_audit_report

# W31 U02 contract-drift gates live in _parallel_workspace_contract_drift
# (canonical home); the same-name imports below keep runner.<name> importable
# with unchanged semantics.
from _parallel_workspace_contract_drift import (
    drift_gate_check, exact_contract_equivalence, invalidate_prior_receipts,
    retry_contract_preservation, verify_restart_contract_binding)

# --- W32 U03 duplicate-launch guard (launcher boundary) ----------------------
# Thin guard over frozen U01 derivation and U02 reservation primitives. Every
# transport flows through _with_first_pass_telemetry, so one guard covers all
# backends identically with no scheduler, routing, contract, evidence, or
# locking semantics of its own. An active identical dispatch_id on a second
# path returns without a second spawn.
import phase_job as _phase_job
import wave_event_identity as _event_identity

def _stored_stale_identity(existing: Any) -> dict[str, str]:
    """Flatten a stored reservation into the stale-identity comparison surface (W45 U02)."""
    source = existing if isinstance(existing, dict) else {}
    inner = source.get("identity") if isinstance(source.get("identity"), dict) else {}
    return {"dispatch_id": str(source.get("dispatch_id") or ""),
            "contract_id": str(source.get("contract_id") or inner.get("contract_id") or ""),
            "content_identity": str(source.get("content_identity") or inner.get("content_identity") or ""),
            "semantic_problem_id": str(source.get("semantic_problem_id") or inner.get("semantic_problem_id") or "")}

def _guard_launch_dispatch(*, run_dir, repo, backend, program, seq, target, phase, entry, frozen):
    """Reserve before spawn, or settle the second path without spawning."""
    node = str((entry or {}).get("node") or default_node_for_phase(phase)).strip()
    contract = frozen.get("contract") if isinstance(frozen.get("contract"), dict) else {}
    identity = _phase_runtime.normalize_dispatch_identity({
        "repo_identity": str(session_workspace_identity(repo)),
        "wave_id": str(target), "leaf_id": str(frozen.get("leaf_id") or ""),
        "node_phase": f"{node}/{phase}",
        "contract_id": str(frozen.get("contract_id") or ""),
        "semantic_problem_id": str(contract.get("semantic_problem_id") or ""),
        "attempt_generation": int(frozen.get("generation") or 1),
        "backend_route_identity": f"{backend}/{program or backend}",
        "candidate_generation": 0})
    dispatch_id = _phase_runtime.compute_dispatch_id(identity)
    path = Path(run_dir) / f"dispatch-{dispatch_id.replace(':', '-')}-{target}-{phase}-reservation.json"
    record = _phase_job.build_dispatch_reservation(
        dispatch_id=dispatch_id, identity=identity,
        contract_id=str(frozen.get("contract_id") or ""),
        recovery={"controller_pid": os.getpid(), "reserved_at": _phase_job.utcnow(),
                  "job_path": f"{int(seq):04d}-{target}-{phase}-job.json"})
    # W36 U02 (AC-CAP-031): compile network/tool authority before dispatch.
    # The claude transport shares the opencode bridge; truly unknown backends
    # stay UNSUPPORTED. HARD mismatch and widening raise fail-closed here.
    network_backend = {"claude": "opencode"}.get(backend, backend)
    network_policy = _phase_job.gate_network_tool_dispatch(node, network_backend)
    try:
        _phase_job.reserve_dispatch(path, record)
        # W35 U02 (AC-CAP-020/021): baseline snapshot; settle verifies.
        _scoped_guards.capture_scoped_write_baseline(
            repo, target=target, phase=phase, node=node,
            leaf_id=str(frozen.get("leaf_id") or ""), frozen=frozen, path=path)
        _phase_job.attach_network_tool_policy(path, network_policy=network_policy["network_tool"])
        from controller_state import append_event as _append_event
        _append_event(run_dir, {"event": "network_tool_dispatch", "dispatch_id": dispatch_id,
            "node": node, "backend": backend, "authority": network_policy["network_tool"]["authority"],
            "enforcement": network_policy["network_enforcement"], "native": network_policy["network_native"],
            "worktree_confined": True, "guard_version": network_policy["network_guard_version"]})
        return {"dispatch_id": dispatch_id, "path": path, "duplicate": False}
    except ValueError:
        pass
    existing = _phase_job.read_dispatch_reservation(path)
    try:
        _phase_runtime.validate_dispatch_id(identity, str(existing.get("dispatch_id") or ""))
    except ValueError:
        # W45 U02 (AC-REPLAY-012): record the stale-identity rejection with
        # compared durable IDs, then fail closed; recording never raises.
        _event_identity.record_stale_rejection(
            entry, wave_id=str(target or ""),
            current_node=str((entry or {}).get("node") or node),
            next_node=str(phase or "run"),
            stored=_stored_stale_identity(existing),
            presented={"dispatch_id": dispatch_id,
                       "contract_id": str(identity.get("contract_id") or ""),
                       "content_identity": "",
                       "semantic_problem_id": str(identity.get("semantic_problem_id") or "")})
        raise ValueError(f"dispatch reservation identity mismatch at {path}")
    if not _phase_job.dispatch_reservation_active(existing):
        _phase_job.reserve_dispatch(path, record)
        _phase_job.attach_network_tool_policy(path, network_policy=network_policy["network_tool"])
        return {"dispatch_id": dispatch_id, "path": path, "duplicate": False}
    stored = (existing or {}).get("network_tool_policy")
    if stored is not None:
        _phase_job.verify_network_tool_policy(stored, node=node)
    # W33 U02 (AC-DSP-021): crash-window recovery lives in
    # controller_phase_runtime.settle_dispatch_crash_window; stays thin here.
    return _phase_runtime.settle_dispatch_crash_window(
        path=path, existing=existing, dispatch_id=dispatch_id, entry=entry,
        record=record, result_available=_phase_job.dispatch_result_available(existing))

# W45 U02 (AC-REPLAY-012): settle moved to wave_event_identity (canonical home) with one compact journal event per outcome; same-name import keeps runner.<name> importable unchanged.
from wave_event_identity import _settle_launch_dispatch as _settle_launch_dispatch

def print_phase_result_summary(*args, **kwargs): return _origin_store().emit_phase_result_summary(_phase_contract.print_phase_result_summary, *args, **kwargs)

def print_terminal_summary(*args, **kwargs): return _origin_store().emit_terminal_summary(_phase_contract.print_terminal_summary, *args, **kwargs)

# Wave W15 U02: account_no_progress_attempt lives in controller_progress
# (canonical home, verbatim move); the same-name import above keeps
# runner.account_no_progress_attempt importable with unchanged semantics.

def main() -> int:
    """Thin entrypoint (Wave W15 U02): parse args, bootstrap, delegate loop."""
    args = parse_controller_args()
    ctx = bootstrap_controller(args)
    if ctx.preflight_exit_code is not None:
        return ctx.preflight_exit_code
    return run_controller_loop(
        ctx,
        build_controller_bindings(
            AC_MAX_IDENTICAL_RECOVERY=AC_MAX_IDENTICAL_RECOVERY,
            AC_MAX_SEMANTIC_PROBLEM_CYCLES=AC_MAX_SEMANTIC_PROBLEM_CYCLES,
            AC_MAX_WAVE_REPAIRS=AC_MAX_WAVE_REPAIRS,
            account_no_progress_attempt=account_no_progress_attempt,
            codex_exec=codex_exec,
            opencode_phase=opencode_phase,
            run_parallel_group_implement=run_parallel_group_implement,
            semantic_result_bypasses_no_progress=semantic_result_bypasses_no_progress,
            serial_job_is_current=serial_job_is_current,
            settle_foreign_phase_job=settle_foreign_phase_job,
            wave_repairs_since_definition=wave_repairs_since_definition,
        ),
    )

_phase_contract.configure(globals())

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("OPERATOR_CANCELLED", file=sys.stderr)
        raise SystemExit(130)
