from __future__ import annotations

import argparse
import atexit
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

from wave_state_engine import (
    ControllerLock, aggregate_validation_required, configure_temp_environment,
    current_target as engine_current_target, discover_unfinished_run,
    ensure_temp_layout, load_profile, no_progress_key, pending_targets as engine_pending_targets,
    program_run_root, repo_identity, repository_content_identity, resume_classification,
    semantic_finding_key, wave_location as engine_wave_location, wave_metadata,
    wave_targets_in_folder as engine_wave_targets_in_folder, legacy_program_roots,
)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

STATUS_RE = re.compile(r"WAVE_PHASE_STATUS:\s*([A-Z_]+)", re.I)
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
    prefixes = (f"{target}_", f"{target}-") if project == "HPC" else (f"WAVE_{target}_", f"{target}_")
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
        owner_state = str(finding.get("owner_state") or "").lower()
        if owner_state == "done":
            continue
        if owner and owner != current and owner not in owners:
            owners.append(owner)
    def key(owner: str) -> tuple[int, str]:
        m = re.search(r"(\d+)", owner)
        return (int(m.group(1)) if m else 10**9, owner)
    return sorted(owners, key=key)[0] if owners else None


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
                       canonical: str | None, findings_path: Path | None, no_progress: bool) -> str:
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

Read AGENTS.md, .agents/skills/wave-codex-core/SKILL.md, the target Wave, repository rules, and only the authority/evidence files needed for THIS phase. Preserve unrelated user changes. Never ask the user whether to continue. Never schedule another Wave. Return only the structured result required by the provided output schema.{finding_note}{deeper}

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
THIS IS A NON-TERMINAL REPAIR PHASE. Consume the current audit/validator/findings, resolve true ownership, and actually perform at least one concrete repository-owned repair/evidence-generation/routing action. For an aggregate validator can_close=false, enumerate failing IDs/reasons and repair the current/declared owner; do not stop after writing a status report. Run focused validation and refresh invalidated evidence. Finish READY_FOR_AUDIT when ready for a fresh audit. HUMAN_DEFERRED is allowed only for genuine unavailable authority.
"""
    if phase == "audit":
        return common + """
FRESH INDEPENDENT AUDIT. Do not edit product, tests, lifecycle, reports, or evidence. Re-read the frozen/current candidate and required proof. Run read-only validation where possible. Return PASS only if this target can proceed to close under its own contract; otherwise REOPEN/BLOCKED with concrete finding IDs and owners. Do not repair.
"""
    if phase == "close":
        return common + """
SERIAL CLOSEOUT phase. Close only after a fresh audit PASS. Run required closeout validator(s), verify candidate/final-SHA/evidence truth, then perform authorized lifecycle bookkeeping. If a validator is red or evidence is stale/missing, return REOPEN/BLOCKED with concrete findings; do not fake PASS. PASS means the target was actually closed and repository truth advanced.
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
               no_progress: bool, seq: int) -> dict[str, Any]:
    result_path = run_dir / f"{seq:04d}-{target}-{phase}-result.json"
    log_path = run_dir / f"{seq:04d}-{target}-{phase}.log"
    prompt_path = run_dir / f"{seq:04d}-{target}-{phase}.prompt.md"
    prompt = build_phase_prompt(repo, project, target, wave_path, phase, canonical, findings_path, no_progress)
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
    while True:
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
        print(f"[program] codex exec retry phase={phase} attempt={attempt} delay={delay}s", flush=True)
        time.sleep(delay)


def opencode_phase(repo: Path, target: str, phase: str, seq: int, run_dir: Path, program: str) -> dict[str, Any]:
    luna_family = program in {"wave-a-end-l", "wave-a-end-l-p"}
    script_name = "run-wave-l-phase.ps1" if luna_family else "run-wave-phase.ps1"
    script = repo / ".opencode" / "scripts" / script_name
    if not script.exists():
        family = "Luna-only" if luna_family else "mixed-model"
        raise RuntimeError(f"Missing {family} OpenCode phase runner: {script}")
    log_path = run_dir / f"{seq:04d}-{target}-{phase}-opencode.log"
    code, output = run_stream([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), phase, target
    ], repo, log_path=log_path)
    m = list(STATUS_RE.finditer(output))
    missing_status = code == 68 or "WAVE_L_PHASE_MISSING_STATUS" in output
    if missing_status:
        return {
            "status": "MISSING_STATUS",
            "summary": output[-3000:],
            "findings": ["OpenCode child exited without a terminal WAVE_PHASE_STATUS marker; orchestration recovery must rerun the same phase."],
            "changed_files": [],
            "next_action": "reconcile",
        }
    status = m[-1].group(1).upper() if m else ("FAIL" if code else "READY")
    if "HUMAN" in status or HUMAN_RE.search(output):
        status = "HUMAN_DEFERRED"
    mapping = {
        "READY": "READY", "READY_FOR_AUDIT": "READY_FOR_AUDIT", "PASS": "PASS",
        "REOPEN": "REOPEN", "BLOCKED": "BLOCKED", "FAIL": "FAIL", "HUMAN_DEFERRED": "HUMAN_DEFERRED"
    }
    status = mapping.get(status, "FAIL" if code else "READY")
    return {
        "status": status,
        "summary": output[-3000:],
        "findings": [output[-1600:]] if status in {"REOPEN", "BLOCKED", "FAIL", "HUMAN_DEFERRED"} else [],
        "changed_files": [],
        "next_action": "none",
    }


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
    router = repo / ".opencode" / "scripts" / "route-wave-findings.py"
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
    data = {
        "target": target,
        "phase": phase,
        "status": result.get("status"),
        "findings": sorted(str(x) for x in (result.get("findings") or [])),
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
    ap.add_argument("--program", choices=["wave-auto-end", "wave-auto-parallel", "wave-a-end-l", "wave-a-end-l-p"], default="wave-a-end-l-p")
    ap.add_argument("--model", help="Optional Codex model override; omit to use CLI/default config")
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--resume-run-id", help="Manual/debug override. Normal invocation auto-resumes.")
    ap.add_argument("--new-run", action="store_true", help="Explicitly ignore unfinished runs and start from repository truth")
    ap.add_argument("--max-iterations", type=int, default=0, help="0 = unlimited; intended only for diagnostics")
    args = ap.parse_args()
    if args.new_run and args.resume_run_id:
        raise SystemExit("--new-run and --resume-run-id are mutually exclusive")

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit(f"Not a Git repository root: {repo}")

    self_heal(repo)
    validate_orchestration(repo)
    profile = load_profile(repo)
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
        "terminal": False, "terminal_class": None, "fingerprints": {}, "owner_stack": [],
        "target_override": None, "findings_path": None, "seq": 0, "closed_owner_repair": False,
    }
    defaults.update(state)
    state = defaults
    state.update({
        "run_id": run_id, "backend": args.backend, "project": project, "terminal": False,
        "terminal_class": None, "resume_classification": classification,
        "repository_identity": identity["repo_root"], "branch": identity["branch"],
        "saved_head": state.get("current_head") or state.get("saved_head"), "current_head": identity["head"],
    })
    state.setdefault("fingerprints", {})
    state.setdefault("owner_stack", [])

    # Repository truth beats stale run routing. A CLOSED Wave remains lifecycle-CLOSED;
    # the controller may nevertheless run an explicit current-compliance repair transaction.
    override = state.get("target_override")
    if override:
        _, override_state = engine_wave_location(repo, profile, str(override))
        if override_state == "done" and not state.get("closed_owner_repair"):
            append_event(run_dir, {"event": "stale_closed_owner_route_discarded", "owner": override})
            state["target_override"] = None
            state["owner_stack"] = []
            classification = "RECONCILE_FORWARD"
    if classification in {"RECONCILE_FORWARD", "STALE_RUN", "NEW_RUN_FROM_REPO_TRUTH"}:
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

    phase = str(state.get("phase") or "reconcile")
    target_cache: str | None = state.get("current_wave") if state.get("target_override") else None
    stored_findings = state.get("findings_path")
    findings_path: Path | None = (repo / stored_findings) if isinstance(stored_findings, str) and stored_findings else None
    no_progress = False
    seq = int(state.get("seq", 0))
    controller_boot_fingerprint = controller_runtime_fingerprint(repo, profile)

    while True:
        lock.heartbeat()
        state["iteration"] = int(state.get("iteration",0)) + 1
        if args.max_iterations and state["iteration"] > args.max_iterations:
            raise RuntimeError("Diagnostic max-iterations reached; normal unattended runs should use 0/unlimited.")

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
                if failed_wave:
                    state.update({"terminal":False,"terminal_class":"PROGRAM_FINAL_VALIDATION_BLOCKED",
                                  "target_override":failed_wave,"closed_owner_repair":True,"current_wave":failed_wave,
                                  "phase":"repair","final_validation_path":str(final_path.relative_to(repo))})
                    findings_path = run_dir / f"{seq:04d}-{failed_wave}-final-validation-findings.json"
                    write_json(findings_path,{"blocked_wave":failed_wave,"canonical_source":failed_wave,"findings":[
                        {"finding_id":f"FINAL_VALIDATION::{failed_wave}","execution_owner":failed_wave,"owner_state":"done",
                         "classification":"repository-owned","human_only":False,"summary":r}
                        for r in final_reasons if r.startswith(failed_wave+":")
                    ]})
                    state["findings_path"] = str(findings_path.relative_to(repo)); target_cache=None; phase="repair"
                    save_state(run_dir,state); continue
                state.update({"terminal":True,"terminal_class":"PROGRAM_FINAL_VALIDATION_BLOCKED","current_wave":None,
                              "phase":"reconcile","final_validation_path":str(final_path.relative_to(repo))})
                save_state(run_dir,state); print("PROGRAM_FINAL_VALIDATION_BLOCKED")
                print(json.dumps({"can_close":False,"failure_reasons":all_reasons},ensure_ascii=False,indent=2))
                lock.release(); return 30
            state.update({"terminal":True,"terminal_class":"PROGRAM_COMPLETE","current_wave":None,"phase":"done",
                          "final_validation_path":str(final_path.relative_to(repo))})
            save_state(run_dir,state); append_event(run_dir,{"event":"program_complete","final_validation":str(final_path.relative_to(repo))})
            print("PROGRAM_COMPLETE"); lock.release(); return 0

        if target_cache != target:
            target_cache = target; phase = "reconcile"
            if not state.get("target_override"): findings_path = None
            no_progress = False

        _canonical_path, target_state = wave_location(repo, project, target)
        meta = wave_metadata(wave_path, profile)
        content_identity = implementation_identity(repo, profile)
        state.update({"current_wave":target,"wave_file":str(wave_path.relative_to(repo)),"wave_state":target_state,
                      "canonical_source_wave":canonical,"phase":phase,"target_cache":target_cache,
                      "content_identity":content_identity})
        save_state(run_dir,state)

        if phase == "close" and state.get("tested_content_identity") and state.get("tested_content_identity") != content_identity:
            append_event(run_dir,{"event":"evidence_stale_before_close","target":target,
                                  "tested_content_identity":state.get("tested_content_identity"),"current_content_identity":content_identity})
            phase="audit"; state["phase"]=phase; save_state(run_dir,state); continue

        seq += 1; state["seq"] = seq
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

        if args.backend == "codex":
            result = codex_exec(repo,run_dir,project,target,wave_path,phase,canonical,findings_path,args.model,no_progress,seq)
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
            result=opencode_phase(repo,target,phase,seq,run_dir,program)

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

        current_controller_fingerprint = controller_runtime_fingerprint(repo, profile)
        if current_controller_fingerprint != controller_boot_fingerprint:
            state.update({"phase":"reconcile","controller_restart_required":True,"last_phase_result":str(normalized.relative_to(repo))})
            save_state(run_dir,state)
            append_event(run_dir,{"event":"controller_restart_boundary","target":target,"phase":phase})
            lock.release()
            os.execv(sys.executable, [sys.executable, *sys.argv])

        status=str(result.get("status","")).upper()
        if status in {"MISSING_STATUS","ORCHESTRATION_RECOVERY_REQUIRED"}:
            append_event(run_dir,{"event":"orchestration_recovery","target":target,"phase":phase,"reason":result.get("summary")})
            state["phase"]=phase; state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
            save_state(run_dir,state); continue

        if status == "HUMAN_DEFERRED":
            if human_deferred_is_real(result):
                state.update({"terminal":True,"terminal_class":"PROGRAM_HUMAN_DEFERRED","phase":phase}); save_state(run_dir,state)
                print("PROGRAM_HUMAN_DEFERRED"); print(json.dumps(result,ensure_ascii=False,indent=2)); lock.release(); return 20
            result["status"]="BLOCKED"; status="BLOCKED"
            result.setdefault("findings",[]).append("Human deferral lacked a concrete external-authority dependency; keep as repository-owned repair.")

        semantic = result_fingerprint(target, phase, result)
        fp=no_progress_key(target,phase,semantic,content_identity)
        count=int(state["fingerprints"].get(fp,0))+1; state["fingerprints"][fp]=count
        no_progress=count>=2
        if count>=3:
            append_event(run_dir,{"event":"NO_PROGRESS_CYCLE","target":target,"phase":phase,"semantic_finding":semantic,
                                  "content_identity":content_identity,"count":count})
            # Do not execute the identical operation again. Reconcile routing/state first.
            if phase != "reconcile":
                phase="reconcile"; state["phase"]=phase; save_state(run_dir,state); continue
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
                elif owner_state == "done":
                    append_event(run_dir,{"event":"closed_owner_route_suppressed","target":target,"owner":owner})
                else:
                    stack=state.setdefault("owner_stack",[])
                    active_owners={str(frame.get("owner")) for frame in stack if isinstance(frame,dict)}
                    if owner == state.get("target_override") or owner in active_owners:
                        append_event(run_dir,{"event":"owner_route_cycle_guard","target":target,"owner":owner})
                    else:
                        stack.append({"blocked_target":target,"owner":owner,"findings_path":str(findings_path.relative_to(repo)) if findings_path else None,"blocked_phase":phase})
                        state["target_override"]=owner; state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
                        append_event(run_dir,{"event":"true_owner_route","from":target,"to":owner,"findings":state["findings_path"]})
                        phase="reconcile"; state["phase"]=phase; target_cache=None; save_state(run_dir,state); continue

        if phase == "plan" and status in {"READY","PASS"}: state["last_planned_wave"]=target
        if phase == "audit" and status == "PASS":
            state["tested_content_identity"] = implementation_identity(repo,profile)
            state["tested_wave"] = target
            state["audit_passed_at"] = utcnow()
            if state.get("target_override") == target and target_state == "done":
                frame=state.get("owner_stack",[]).pop() if state.get("owner_stack") else None
                append_event(run_dir,{"event":"historical_owner_revalidated","owner":target,"return_target":frame.get("blocked_target") if isinstance(frame,dict) else None})
                remaining=state.get("owner_stack",[])
                state["target_override"]=(frame.get("blocked_target") if isinstance(frame,dict) and remaining else None)
                if state.get("closed_owner_repair") and not state["target_override"]:
                    state["closed_owner_repair"] = False
                target_cache=None
                findings_path=(repo/frame["findings_path"]) if isinstance(frame,dict) and frame.get("findings_path") else None
                state["findings_path"]=str(findings_path.relative_to(repo)) if findings_path else None
                phase="reconcile"; state["phase"]=phase; save_state(run_dir,state); continue

        if phase == "close" and status == "PASS":
            controller_close_wave(repo,profile,project,target)
            _, closed_state=wave_location(repo,project,target)
            if closed_state != "done":
                raise RuntimeError(f"Close PASS for {target} did not produce canonical CLOSED/done lifecycle state")
            state["last_closed_wave"]=target
            state["closure_content_identity"]=implementation_identity(repo,profile)
            _, closure_sha=git(repo,"rev-parse","HEAD"); state["closure_commit_sha"]=closure_sha or None
            if state.get("target_override") == target:
                frame=state.get("owner_stack",[]).pop() if state.get("owner_stack") else None
                remaining=state.get("owner_stack",[])
                state["target_override"]=(frame.get("blocked_target") if isinstance(frame,dict) and remaining else None)
                findings_path=(repo/frame["findings_path"]) if isinstance(frame,dict) and frame.get("findings_path") else None
            else:
                findings_path=None
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
