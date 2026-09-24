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
    semantic_finding_key, wave_location as engine_wave_location, wave_metadata,
    wave_targets_in_folder as engine_wave_targets_in_folder, legacy_program_roots,
)
from phase_job import job_matches, mark_result as mark_phase_job_result, process_start_marker, read_job as read_phase_job, start_job as start_phase_job, wait_job as wait_phase_job


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
        "repair_hypothesis": {"type": "string"},
        "next_action": {
            "type": "string",
            "enum": ["plan", "run", "repair", "audit", "close", "reconcile", "next_wave", "none"],
        },
    },
    "required": ["status", "summary", "findings", "changed_files", "next_action"],
    "additionalProperties": False,
}




def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()




def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return ""




def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")




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




def run_stream(args: list[str], cwd: Path, stdin_text: str | None = None, log_path: Path | None = None) -> tuple[int, str]:
    exe = shutil.which(args[0]) or args[0]
    actual = [exe, *args[1:]]
    if os.name == "nt" and Path(exe).suffix.lower() in {".cmd", ".bat"}:
        cmdline = subprocess.list2cmdline(actual)
        actual = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmdline]
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
    )
    if stdin_text is not None and proc.stdin:
        proc.stdin.write(stdin_text)
        proc.stdin.close()
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
    finally:
        if log_fh:
            log_fh.close()
    return proc.wait(), "".join(lines)




def git(repo: Path, *args: str) -> tuple[int, str]:
    cp = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return cp.returncode, (cp.stdout + cp.stderr).strip()




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
    code, head = git(repo, "rev-parse", "HEAD")
    recorded_head = str(state.get("audit_candidate_sha", "")).strip()
    return code == 0 and bool(head) and recorded_head == head




def recover_allowlisted_audit_receipt(repo: Path, run_dir: Path, profile: dict[str, Any],
                                      target: str, content_identity: str) -> dict[str, Any] | None:
    """Recover a real PASS when only allowlisted closeout files changed.


    This is a restart/handoff recovery path, not a report parser: it consumes
    normalized audit receipts and requires the candidate-to-HEAD diff to be
    entirely profile-allowlisted.
    """
    manifest = read_json_file(repo / f"artifacts/wave_{target}/WAVE_{target}_EVIDENCE_MANIFEST.json")
    candidate = str((manifest or {}).get("candidate_sha", "")).strip()
    code, head = git(repo, "rev-parse", "HEAD")
    if not candidate or code != 0 or not head or candidate == head:
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
    cp = subprocess.run([sys.executable, str(path)], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(cp.stdout, end="")
    if cp.stderr:
        print(cp.stderr, file=sys.stderr, end="")
    if cp.returncode != 0:
        raise RuntimeError("validate-wave-orchestration.py failed")




def phase_schema(run_dir: Path) -> Path:
    p = run_dir / "phase-result.schema.json"
    if not p.exists():
        write_json(p, RESULT_SCHEMA)
    return p




def build_phase_prompt(repo: Path, project: str, target: str, wave_path: Path, phase: str,
                       canonical: str | None, findings_path: Path | None, no_progress: bool,
                       audit_receipt: dict[str, Any] | None = None,
                       content_identity: str = "unknown") -> str:
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
    )
    blob = (cp.stdout or "") + "\n" + (cp.stderr or "")
    if cp.returncode != 0:
        raise RuntimeError(f"codex exec --help failed with exit {cp.returncode}: {blob[-2000:]}")
    return blob




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




def codex_exec(repo: Path, run_dir: Path, project: str, target: str, wave_path: Path, phase: str,
               canonical: str | None, findings_path: Path | None, model: str | None,
               no_progress: bool, seq: int, state: dict[str, Any] | None = None) -> dict[str, Any]:
    result_path = run_dir / f"{seq:04d}-{target}-{phase}-result.json"
    log_path = run_dir / f"{seq:04d}-{target}-{phase}.log"
    prompt_path = run_dir / f"{seq:04d}-{target}-{phase}.prompt.md"
    prompt = build_phase_prompt(repo, project, target, wave_path, phase, canonical, findings_path, no_progress,
                                state if phase == "close" else None,
                                state.get("content_identity", "unknown") if state else "unknown")
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
    while attempt < AC_MAX_TRANSPORT_ATTEMPTS:
        attempt += 1
        append_event(run_dir, {"event": "codex_phase_start", "phase": phase, "target": target, "attempt": attempt})
        code, output = run_stream(args, repo, stdin_text=prompt, log_path=log_path)
        append_event(run_dir, {"event": "codex_phase_exit", "phase": phase, "target": target, "attempt": attempt, "exit": code})
        if code == 0 and result_path.exists():
            try:
                return json.loads(read_text(result_path))
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
# Mirrors the per-family bridge routing; the bridge's dispatch record is the
# effective truth and any divergence is surfaced, never silent.
LUNA_MODEL = {"audit": "openai/gpt-5.6-luna#high"}
LUNA_DEFAULT_MODEL = "openai/gpt-5.6-luna#medium"


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
    raw = read_text(repo / "opencode.jsonc") if (repo / "opencode.jsonc").is_file() else ""
    match = re.search(r"""(?m)["']model["']\s*:\s*["']([^"']+)["']""", raw)
    project_model = match.group(1).strip() if match else None
    if family == "luna-openai":
        requested = LUNA_MODEL.get(phase, LUNA_DEFAULT_MODEL)
    elif family == "hybrid":
        requested = LUNA_MODEL.get(phase, project_model)
    else:
        requested = project_model
    model, thinking = split_model_thinking(requested)
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
    for phase in ("doctor", "plan", "run", "audit", "close"):
        route = resolve_phase_route(repo, program, phase, backend, codex_model)
        print(f"[routing] {route['role']:<10} | agent={route['agent']} | model={route['model']} | thinking={route['thinking']}", flush=True)


def models_used_lines(history: list[dict[str, Any]]) -> list[str]:
    counts: dict[tuple[str, str, str, bool], int] = {}
    for item in history or []:
        key = (str(item.get("role")), str(item.get("model")), str(item.get("thinking")), bool(item.get("fallback")))
        counts[key] = counts.get(key, 0) + 1
    return [f"[models-used] {role}: {model} / thinking={thinking}: {n} dispatch{'es' if n != 1 else ''}{' (fallback)' if fb else ''}"
            for (role, model, thinking, fb), n in sorted(counts.items())]


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
        if job_matches(job, target=target, phase=phase, program=program):
            job_path = candidate
            logged = str(job.get("log_path") or "").strip()
            if logged:
                log_path = Path(logged)
            append_event(run_dir, {"event":"managed_phase_job_resume","target":target,"phase":phase,
                                   "job":str(job_path.relative_to(repo)),"pid":job.get("pid")})
        else:
            state.pop("active_phase_job", None)
            state.pop("active_phase_pid", None)
            active_rel = None

    requested = resolve_phase_route(repo, program, phase)
    dispatch_path = job_path.with_name(job_path.name.replace("-job.json", "-dispatch.json"))
    state["active_route"] = {**requested, "wave": target, "phase": phase, "dispatch_id": dispatch_path.name,
                             "started_at": (state.get("active_route") or {}).get("started_at") if active_rel else utcnow()}
    print(f"[dispatch] {target} {phase.upper()} {'reattached' if active_rel else 'started'} | {format_route(requested)}", flush=True)
    if not active_rel:
        exe = shutil.which("powershell") or "powershell"
        args = [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                phase, target, "-RepoRoot", str(repo), "-DispatchRecordPath", str(dispatch_path)]
        if controller_context_path is not None and controller_context_path.exists():
            args += ["-ControllerContextPath", str(controller_context_path)]
        append_event(run_dir, {"event": "phase_dispatch", "run_id": run_dir.name, "dispatch_id": dispatch_path.name,
                               "wave": target, "phase": phase, "role": requested["role"], "backend": requested["backend"],
                               "agent": requested["agent"], "requested_model": requested["model"],
                               "requested_thinking": requested["thinking"]})
        proc = start_phase_job(
            args=args, cwd=repo, log_path=log_path, job_path=job_path,
            metadata={"seq":seq,"target":target,"phase":phase,"program":program,
                      "backend":"opencode","controller_pid":os.getpid()},
        )
        state["active_phase_job"] = str(job_path.relative_to(repo))
        state["active_phase_pid"] = int(proc.pid)
        save_state(run_dir, state)
        append_event(run_dir, {"event":"managed_phase_job_start","target":target,"phase":phase,
                               "job":str(job_path.relative_to(repo)),"pid":proc.pid})

    code, output = wait_phase_job(job_path=job_path, log_path=log_path, proc=proc)
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
        machine = parse_machine_result(output, phase)
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
    payload = {
        "target": target,
        "phase": phase,
        "content_identity": content_identity,
        "findings_path": str(findings_path.relative_to(repo)) if findings_path and findings_path.exists() else None,
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
    raw = _strip_ansi(read_text(log_path)).strip()
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
    for line in models_used_lines(state.get("route_history") or []):
        print(line, flush=True)
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
    cp = subprocess.run([sys.executable, str(script), "--wave", canonical], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace")
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
    cp = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.stdout:
        print(cp.stdout)
    if cp.returncode != 0:
        raise RuntimeError(f"route-wave-findings.py failed: {cp.stderr}")
    return out_path




def human_deferred_is_real(result: dict[str, Any]) -> bool:
    findings = result.get("findings") or []
    if not findings:
        return False
    return all(HUMAN_RE.search(str(x)) for x in findings)




def result_fingerprint(target: str, phase: str, result: dict[str, Any]) -> str:
    raw_findings = [str(x) for x in (result.get("findings") or [])]
    finding_ids = sorted({m.group(0).upper() for text in raw_findings for m in FINDING_ID_RE.finditer(text)})
    if finding_ids:
        findings = finding_ids
    else:
        findings = sorted(
            re.sub(r"\b[0-9a-f]{40}\b", "<sha>", text, flags=re.I).strip()
            for text in raw_findings
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
                                text=True, encoding="utf-8", errors="replace", check=False)
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
        cp = subprocess.run(command, cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        results.append({"path": rel, "exit": cp.returncode, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-4000:]})
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
    ap.add_argument("--backend", choices=["codex", "opencode"], default="codex")
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
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit(f"Not a Git repository root: {repo}")


    self_heal(repo)
    profile = load_profile(repo)
    lifecycle_preflight = ensure_lifecycle_integrity(repo, profile, apply_safe=True, reason="controller-preflight")
    if lifecycle_preflight.get("repairs"):
        print(f"[lifecycle-self-heal] repaired={len(lifecycle_preflight['repairs'])} receipt={lifecycle_preflight.get('receipt')}", flush=True)
    validate_orchestration(repo)
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
    }
    defaults.update(state)
    state = defaults
    state.update({
        "run_id": run_id, "backend": args.backend, "project": project, "terminal": False,
        "terminal_class": None, "resume_classification": classification,
        "repository_identity": identity["repo_root"], "branch": identity["branch"],
        "saved_head": state.get("current_head") or state.get("saved_head"), "current_head": identity["head"],
        "controller_pid": os.getpid(), "controller_process_start_marker": process_start_marker(os.getpid()),
        "parallel_strategy": "serial_fallback" if program.endswith("-parallel") else None,
    })
    state.setdefault("fingerprints", {})
    state.setdefault("owner_stack", [])


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
    if program.endswith("-parallel"):
        append_event(run_dir, {"event": "parallel_serial_fallback", "reason": "no project-declared managed parallel task graph"})
    print_program_routing(repo, program, args.backend, args.model)
    save_state(run_dir, state)
    write_json(run_dir / "phase-result.schema.json", RESULT_SCHEMA)


    if args.preflight_only:
        target, wave_path, canonical = current_target(repo, project, state.get("target_override"), allow_closed_owner_repair=bool(state.get("closed_owner_repair")))
        print(json.dumps({"status":"READY","project":project,"current_wave":target,
                          "wave_file":str(wave_path) if wave_path else None,"canonical":canonical,
                          "run_id":run_id,"run_dir":str(run_dir.relative_to(repo)),
                          "resume_classification":classification}, indent=2))
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


        target, wave_path, canonical = current_target(repo, project, override, allow_closed_owner_repair=bool(state.get("closed_owner_repair")))
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


        active_job = {}
        active_rel = state.get("active_phase_job")
        if isinstance(active_rel, str) and active_rel.strip():
            active_job = read_phase_job(repo / active_rel)
        if job_matches(active_job, target=target, phase=phase, program=program):
            seq = int(active_job.get("seq") or state.get("seq") or seq)
            state["seq"] = seq
            append_event(run_dir,{"event":"managed_phase_job_attach","target":target,"phase":phase,
                                  "job":active_rel,"pid":active_job.get("pid")})
        else:
            if active_rel:
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


        aggregate_validator: Path | None = None
        if phase == "close" and str(result.get("status","")).upper() == "PASS" and aggregate_validation_required(profile,meta,phase):
            aggregate_validator = run_validator(repo, profile, canonical, run_dir, seq)
            can_close, reasons = validator_can_close(aggregate_validator)
            append_event(run_dir,{"event":"aggregate_validator_gate","target":target,"canonical":canonical,"can_close":can_close,"reasons":reasons})
            if not can_close:
                result={"status":"BLOCKED","summary":"Controller aggregate validator rejected source closeout",
                        "findings":reasons or ["aggregate validator can_close=false"],"changed_files":[],"next_action":"repair"}


        if phase == "close" and str(result.get("status","")).upper() == "PASS":
            post_identity=implementation_identity(repo,profile)
            if state.get("tested_content_identity") and post_identity != state.get("tested_content_identity"):
                result={"status":"BLOCKED","summary":"Implementation content changed after the fresh audit",
                        "findings":["tested_content_identity no longer matches current implementation content"],
                        "changed_files":result.get("changed_files",[]),"next_action":"audit"}


        append_event(run_dir,{"event":"phase_result","target":target,"phase":phase,"result":result})
        normalized=run_dir/f"{seq:04d}-{target}-{phase}-normalized.json"
        normalized.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if phase == "audit" and str(result.get("status", "")).upper() == "PASS":
            audit_report = persist_fresh_audit_report(repo, project, target, result, normalized)
            if audit_report is not None:
                state["audit_report_path"] = str(audit_report.relative_to(repo))
                append_event(run_dir,{"event":"audit_report_persisted","target":target,
                                      "path":state["audit_report_path"],
                                      "normalized":str(normalized.relative_to(repo))})
                save_state(run_dir,state)
        print_phase_result_summary(target, phase, result, normalized, repo)
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
            append_event(run_dir,{"event":"NO_PROGRESS_BYPASS_FOR_LIFECYCLE_COMMIT",
                                  "target":target,"phase":phase,"status":status,
                                  "progress_epoch":int(state.get("progress_epoch",0))})
            save_state(run_dir,state)
        else:
            semantic = result_fingerprint(target, phase, result)
            fp=progress_no_progress_key(target,phase,semantic,content_identity,int(state.get("progress_epoch",0)))
            count=int(state["fingerprints"].get(fp,0))+1; state["fingerprints"][fp]=count
            no_progress=count>=2
            if count>=2:
                append_event(run_dir,{"event":"NO_PROGRESS_CYCLE","target":target,"phase":phase,"semantic_finding":semantic,
                                      "content_identity":content_identity,"count":count,
                                      "progress_epoch":int(state.get("progress_epoch",0))})
                no_progress = True
                state["last_no_progress"] = {"target":target,"phase":phase,"semantic_finding":semantic,
                                             "content_identity":content_identity,"count":count}
            if count >= AC_MAX_IDENTICAL_RECOVERY:
                state.update({"terminal":True,"terminal_class":"PROGRAM_TECHNICAL_STALLED","phase":"stalled",
                              "stall_reason":"identical_no_progress_cycle","current_wave":target})
                save_state(run_dir,state)
                append_event(run_dir,{"event":"PROGRAM_TECHNICAL_STALLED","target":target,"phase":phase,
                                      "semantic_finding":semantic,"content_identity":content_identity,"count":count})
                print("PROGRAM_TECHNICAL_STALLED"); print_terminal_summary(state, run_dir); lock.release(); return 30
            save_state(run_dir,state)


        next_phase=choose_after(phase,result)
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
                        phase="repair" if owner_state == "done" else "reconcile"
                        state["phase"]=phase; target_cache=None; save_state(run_dir,state); continue


        if phase == "plan" and status in {"READY","PASS"}: state["last_planned_wave"]=target
        if phase == "audit" and status == "PASS":
            state["tested_content_identity"] = implementation_identity(repo,profile)
            state["tested_wave"] = target
            state["audit_passed_at"] = utcnow()
            state["audit_status"] = "PASS"
            state["audit_result_path"] = str(normalized.relative_to(repo))
            code, head = git(repo, "rev-parse", "HEAD")
            state["audit_candidate_sha"] = head if code == 0 else None
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
            state["closure_content_identity"]=implementation_identity(repo,profile)
            _, closure_sha=git(repo,"rev-parse","HEAD"); state["closure_commit_sha"]=closure_sha or None
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
