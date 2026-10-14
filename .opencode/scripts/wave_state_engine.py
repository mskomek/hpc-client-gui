from __future__ import annotations

from _wave_state_git import (_read_text, subprocess_no_window_kwargs, _which_git, _git,
    git_capability, _norm_rel, _is_under, surface_key, surface_contains,
    surfaces_overlap, controller_owned_surfaces, reserved_surface_hits,
    AGENT_CORE_OWNED_SURFACES)
from _wave_state_telemetry import TELEMETRY_COUNTERS, record_telemetry, timed_telemetry
from _wave_state_progress import (managed_job_lease, normalize_progress_profile,
    progress_contract_version, load_profile, ensure_temp_layout, configure_temp_environment,
    program_run_root, program_progress_root, progress_ledger_path, load_progress_ledger,
    save_progress_ledger, record_progress_attempt, clear_progress_entry, legacy_program_roots,
    PROFILE_REL, TEMP_SUBDIRS, MANAGED_JOB_LEASE_DEFAULTS, PROGRESS_CONTRACT_VERSIONS,
    PROGRESS_CONTRACT_DEFAULT_VERSION, PROGRESS_CONTRACT_DEFAULT_ENABLED,
    PROGRESS_PROFILE_KEYS, LEDGER_MAX_ENTRIES)
from _wave_state_waves import (in_scheduler_scope, pending_only_selection, _simple_yaml_value, _parse_frontmatter,
    _wave_match, _format_wave_id, parse_wave_id, wave_number_of, wave_channel_of,
    wave_part_of, as_group, group_label, wave_group_of, wave_sort_key, wave_id_equal,
    wave_title_of, group_members, parallel_config, check_parallel_group_invariants,
    wave_metadata, _wave_metadata_uncached, wave_targets_in_folder, wave_location,
    pending_targets, pending_override_is_frontier, FRONTMATTER_RE, VALID_PHASES, WAVE_ID_RE, WAVE_ID_BARE_RE,
    _WAVE_METADATA_CACHE)
from _wave_state_selection import eligible_pending_targets
from _wave_state_gate_receipts import bind_gate_receipt as bind_gate_receipt, classify_gate_receipt as classify_gate_receipt, partition_current_gate_receipts as partition_current_gate_receipts, require_current_gate_receipt as require_current_gate_receipt, validate_parallel_gate_receipts as validate_parallel_gate_receipts
from _wave_state_lifecycle import (lifecycle_authority_ids, _wave_in_authority_scope,
    lifecycle_entries, lifecycle_conflicts, _lexical_abspath, _repo_relative_posix,
    _lifecycle_quarantine_root, safe_repair_lifecycle, ensure_lifecycle_integrity,
    current_target, reconcile_active_wave_tracker, waves_index_missing,
    reconcile_waves_index, aggregate_validation_required, repo_identity,
    repository_content_identity)
from _wave_state_runs import (_read_state, is_resumable_window_exhausted,
    is_terminal_run_state, _supervisor_hard_cap_reached, _run_has_live_controller,
    is_abandoned_hard_capped_run, discover_unfinished_run, resume_classification,
    semantic_finding_key, no_progress_key, process_start_marker,
    _windows_start_ticks, _lock_retryable, live_controller_locks,
    TERMINAL_RUN_CLASSES, _process_start_marker, ControllerLock)
_ORIGIN_STORE_NAMES = frozenset({"record_leaf_failure_with_origin", "ensure_failure_origin",
    "stamp_failure_origin", "summarize_failure_origins"})
_RETRY_COUNTER_NAMES = frozenset({"RETRY_COUNTER_FAMILIES", "TECHNICAL_RETRY_FAMILIES",
    "SEMANTIC_RETRY_FAMILIES", "default_retry_counters", "ensure_retry_counters",
    "sync_legacy_retry_fields", "record_retry_attempt", "retry_counters_snapshot",
    "migrate_retry_counters"})
_DECISION_JOURNAL_NAMES = frozenset({"DECISION_JOURNAL_VERSION", "DECISION_JOURNAL_LIMIT",
    "REASON_FAMILIES", "REASON_CODES", "validate_decision_event",
    "decision_journal", "append_decision_event"})
# --- W46 U01 deterministic run replay (AC-REPLAY-020; snapshot-only, no execution path) ---
# Pure read-only renderer over frozen snapshots plus the W45 decision journal
# and the W32-W33 dispatch-result registry. No model, subprocess, Git,
# transition, or lock path exists in this section by construction: only
# dict/list/str operations on the caller-supplied snapshot, never mutated.
REPLAY_VERSION = 1
REPLAY_VIEWS = ("full", "wave", "problem", "dispatch")
REPLAY_NOT_RECORDED = "not recorded"


def _replay_gap(value: object) -> str:
    text = str(value or "").strip()
    return text if text else REPLAY_NOT_RECORDED


def _replay_reason_codes() -> dict[str, str]:
    try:
        import wave_decision_journal as _journal
        codes = getattr(_journal, "REASON_CODES", {})
        if isinstance(codes, dict) and codes:
            return {str(k): str(v) for k, v in codes.items()}
    except Exception:
        pass
    return {"progress-plan-run": "normal-progression"}


def validate_replay_identity(snapshot: object, expected: object = None) -> dict[str, object]:
    """Snapshot-only identity check; never reads disk, locks, or mutates."""
    if not isinstance(snapshot, dict):
        return {"ok": False, "reason": "snapshot-must-be-object", "compared": {}}
    compared: dict[str, object] = {}
    if not isinstance(expected, dict):
        return {"ok": True, "reason": "no-expected-identity", "compared": compared}
    for key in ("run_id", "repository_identity", "content_identity"):
        want = str(expected.get(key) or "").strip()
        if not want:
            continue
        got = str(snapshot.get(key) or "").strip()
        compared[key] = {"expected": want, "observed": got if got else REPLAY_NOT_RECORDED}
        if got != want:
            return {"ok": False, "reason": f"stale-identity:{key}", "compared": compared}
    return {"ok": True, "reason": "identity-match", "compared": compared}


def _replay_journal_rows(entry: object, wave_id: str) -> list[dict[str, object]]:
    codes = _replay_reason_codes()
    raw = entry.get("decision_journal") if isinstance(entry, dict) else None
    rows: list[dict[str, object]] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, dict):
            rows.append({"wave_id": wave_id, "gap": True,
                         "reason": "malformed-journal-segment",
                         "detail": REPLAY_NOT_RECORDED})
            continue
        seq = item.get("seq")
        code = str(item.get("reason_code") or "").strip()
        if not isinstance(seq, int) or code not in codes:
            rows.append({"wave_id": wave_id, "gap": True,
                         "reason": "malformed-journal-segment",
                         "detail": _replay_gap(item.get("transition_identity"))})
            continue
        rows.append({"wave_id": wave_id, "gap": False, "seq": int(seq),
                     "current_node": _replay_gap(item.get("current_node")),
                     "next_node": _replay_gap(item.get("next_node")),
                     "reason_code": code, "reason_family": str(codes[code]),
                     "reason_evidence": [str(v) for v in (item.get("reason_evidence") or [])
                                         if str(v or "").strip()][:8],
                     "transition_identity": _replay_gap(item.get("transition_identity")),
                     "event_id": _replay_gap(item.get("event_id"))})
    rows.sort(key=lambda r: (int(r.get("seq") or 0) if not r.get("gap") else 10**9,
                             str(r.get("transition_identity") or "")))
    return rows


def _replay_dispatch_rows(snapshot: object) -> list[dict[str, object]]:
    registry = snapshot.get("dispatch_results") if isinstance(snapshot, dict) else None
    if not isinstance(registry, dict):
        return []
    seen: dict[str, dict[str, object]] = {}
    for dispatch_id in sorted(str(k) for k in registry):
        record = registry.get(dispatch_id)
        if not isinstance(record, dict):
            continue
        # Duplicate restart/recovered dispatch renders once: first record wins,
        # keyed by versioned dispatch id; no duplicate execution is invented.
        if dispatch_id in seen:
            continue
        seen[dispatch_id] = {"dispatch_id": dispatch_id,
                             "phase_instance_id": _replay_gap(record.get("phase_instance_id")),
                             "contract_id": _replay_gap(record.get("contract_id")),
                             "state": _replay_gap(record.get("state")),
                             "consumed": bool(record.get("consumed")),
                             "recorded_at": _replay_gap(record.get("recorded_at"))}
    return [seen[k] for k in sorted(seen)]


def render_run_replay(snapshot: object, view: str = "full", wave_id: str = "",
                      dispatch_id: str = "") -> dict[str, object]:
    """Deterministic text/JSON replay payload from a frozen snapshot copy."""
    name = str(view or "full").strip().lower()
    if name not in REPLAY_VIEWS:
        raise ValueError(f"unknown replay view: {view!r}")
    state = snapshot if isinstance(snapshot, dict) else {}
    waves = state.get("waves") if isinstance(state.get("waves"), dict) else {}
    journal_rows: list[dict[str, object]] = []
    for wid in sorted(str(k) for k in waves):
        if name == "wave" and wave_id and wid != str(wave_id):
            continue
        journal_rows.extend(_replay_journal_rows(waves.get(wid), wid))
    dispatch_rows = _replay_dispatch_rows(state)
    if name == "dispatch" and dispatch_id:
        dispatch_rows = [r for r in dispatch_rows
                         if str(r.get("dispatch_id")) == str(dispatch_id)]
    problems: dict[str, object] = {}
    if name in ("full", "problem"):
        for wid in sorted(str(k) for k in waves):
            entry = waves.get(wid)
            hist = entry.get("semantic_problem_history") if isinstance(entry, dict) else None
            if isinstance(hist, dict) and hist:
                problems[wid] = {str(k): dict(v) if isinstance(v, dict) else v
                                 for k, v in sorted(hist.items())}
    lines: list[str] = []
    counter = 0
    for row in journal_rows:
        counter += 1
        if row.get("gap"):
            lines.append(f"[{counter:03d}] GAP")
            lines.append(f"      reason: malformed-journal-segment")
            lines.append(f"      detail: {row.get('detail')}")
            continue
        lines.append(f"[{counter:03d}] {row.get('current_node')} -> {row.get('next_node')}")
        lines.append(f"      reason: {row.get('reason_code')}")
        lines.append(f"      contract: {row.get('transition_identity')}")
        for evidence in (row.get("reason_evidence") or []):
            lines.append(f"      evidence: {evidence}")
    for row in dispatch_rows if name in ("full", "dispatch") else []:
        counter += 1
        lines.append(f"[{counter:03d}] DISPATCH {row.get('dispatch_id')}")
        lines.append(f"      contract: {row.get('contract_id')}")
        lines.append(f"      state: {row.get('state')}")
    payload: dict[str, object] = {"version": REPLAY_VERSION, "view": name,
                                  "run_id": _replay_gap(state.get("run_id")),
                                  "journal": journal_rows, "dispatches": dispatch_rows,
                                  "problems": problems, "text": "\n".join(lines) + ("\n" if lines else "")}
    return payload


def format_run_replay_json(payload: object) -> str:
    """Canonical machine-readable encoding: sorted keys, no timestamps added."""
    import json as _json
    if not isinstance(payload, dict):
        raise ValueError("replay payload must be an object")
    return _json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def __getattr__(name):
    """Lazy W28 failure-origin, W29 retry-counter, and W45 decision-journal surfaces.

    Importing the engine never pulls those modules, so minimal fixtures that
    copy only the engine plus its `_wave_state_*` helpers keep importing.
    """
    if name in _ORIGIN_STORE_NAMES:
        import _wave_failure_origin_store as _origin_store
        return getattr(_origin_store, name)
    if name in _RETRY_COUNTER_NAMES:
        import _wave_retry_counters as _retry_counters
        return getattr(_retry_counters, name)
    if name in _DECISION_JOURNAL_NAMES:
        import wave_decision_journal as _decision_journal
        return getattr(_decision_journal, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
