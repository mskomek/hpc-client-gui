from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

for _stream in (sys.stdout, sys.stderr):
    try:
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from wave_state_engine import load_profile, wave_location, wave_metadata, wave_targets_in_folder

REQUIREMENT_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){1,}\b")
HUMAN_RE = re.compile(
    r"(?ix)\b(?:mfa|two[- ]factor|device\s+authorization|"
    r"401|403|unauthori[sz]ed|forbidden|not\s+logged\s+in|login\s+required|"
    r"interactive\s+(?:login|authorization)|api[_ -]?key\s+(?:missing|required|invalid)|"
    r"manual\s+acceptance|customer\s+acceptance|required\s+hardware|"
    r"authoritative\s+external\s+service)\b"
)

@dataclass
class Finding:
    finding_id: str
    source: str
    text: str
    execution_owner: str | None = None
    owner_state: str | None = None
    human_only: bool = False

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, UnicodeError):
        return ""

def read_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def owned_ids_from_wave(path: Path, profile: dict[str, Any]) -> set[str]:
    try:
        meta = wave_metadata(path, profile)
    except Exception:
        meta = {}
    owned = meta.get("owned_requirements") or []
    if isinstance(owned, str):
        owned = [owned]
    ids = {str(x).upper() for x in owned if str(x).strip()}
    if ids:
        return ids
    text = read_text(path)
    for marker in ("Canonical requirement IDs owned", "Owned stable requirement IDs"):
        if marker in text:
            tail = text.split(marker, 1)[1]
            tail = re.split(r"(?m)^##\s+", tail, maxsplit=1)[0]
            return {x.upper() for x in REQUIREMENT_RE.findall(tail)}
    return set()

def build_owner_index(repo: Path, profile: dict[str, Any]) -> dict[str, tuple[str, str]]:
    index: dict[str, tuple[str, str]] = {}
    precedence = {"done": 0, "pending": 1, "blocked": 2, "postponed": 3}
    for state in ("done", "pending", "blocked", "postponed"):
        for wave_id, path in wave_targets_in_folder(repo, profile, state, scheduled_only=False):
            for req in owned_ids_from_wave(path, profile):
                if req not in index or precedence[state] < precedence[index[req][1]]:
                    index[req] = (wave_id, state)
    return index

def collect_ids_from_obj(obj: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            ids.update(x.upper() for x in REQUIREMENT_RE.findall(str(k)))
            ids.update(collect_ids_from_obj(v))
    elif isinstance(obj, list):
        for item in obj:
            ids.update(collect_ids_from_obj(item))
    elif isinstance(obj, str):
        ids.update(x.upper() for x in REQUIREMENT_RE.findall(obj))
    return ids

def manifest_findings(path: Path) -> list[tuple[str, str, str]]:
    data = read_json(path)
    if not isinstance(data, dict):
        return []
    out: list[tuple[str, str, str]] = []
    for key in ("requirements", "blockers"):
        items = data.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            blob = json.dumps(item, ensure_ascii=False) if not isinstance(item, str) else item
            state = " ".join(str(item.get(k, "")) for k in ("disposition", "status", "result", "state")).upper() if isinstance(item, dict) else blob.upper()
            if any(t in state for t in ("FAIL", "BLOCK", "REOPEN", "MISSING", "NOT_RUN", "AWAITING")):
                ids = sorted(collect_ids_from_obj(item)) or ["UNSCOPED"]
                out.extend((rid, "manifest", blob[:1600]) for rid in ids)
    return out

def validator_findings(path: Path) -> list[tuple[str, str, str]]:
    data = read_json(path)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status") or data.get("result") or "").upper()
    if status in {"PASS", "OK", "GREEN", "CLOSED"}:
        return []
    blob = json.dumps(data, ensure_ascii=False)
    ids = sorted(collect_ids_from_obj(data)) or ["UNSCOPED"]
    return [(rid, "validator", blob[:1600]) for rid in ids]

def audit_findings(path: Path) -> list[tuple[str, str, str]]:
    text = read_text(path)
    upper = text.upper()
    if "WAVE_PHASE_STATUS: PASS" in upper or "AUDITOR DECISION:** `PASS`" in upper:
        return []
    out: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if any(t in line.upper() for t in ("REOPEN", "BLOCK", "FINDING", "MISSING", "STALE", "FAIL")):
            ids = [x.upper() for x in REQUIREMENT_RE.findall(line)]
            if ids:
                out.extend((rid, "audit", line.strip()[:1600]) for rid in ids)
    if not out and any(t in upper for t in ("REOPEN", "BLOCKED", "FAIL")):
        out.append(("UNSCOPED", "audit", "Audit is non-PASS; inspect report for unscoped finding."))
    return out

def dedupe(rows: Iterable[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set(); out=[]
    for row in rows:
        if row not in seen:
            seen.add(row); out.append(row)
    return out

def dependency_ids(repo: Path, profile: dict[str, Any], current_wave: str) -> list[str]:
    path, _ = wave_location(repo, profile, current_wave)
    if path is None:
        return []
    meta = wave_metadata(path, profile)
    deps = meta.get("completion_dependencies") or []
    if isinstance(deps, str):
        deps = [deps]
    return [str(x) for x in deps if str(x).strip()]

CHAIN_RE = re.compile(r"previous Wave (\d+) validator not PASS", re.I)


def aggregate_owner_of(repo: Path, profile: dict[str, Any], canonical: str) -> str | None:
    """The aggregate_close_owner Wave (any lifecycle state) for a canonical source.

    A profile map (aggregate.owner_by_canonical) wins: closed Waves written before
    frontmatter existed are immutable and cannot declare their canonical source.
    """
    mapped = ((profile.get("aggregate") or {}).get("owner_by_canonical") or {}).get(str(canonical))
    if mapped:
        return str(mapped)
    for state in ("done", "pending", "blocked", "postponed"):
        for wid, path in wave_targets_in_folder(repo, profile, state, scheduled_only=False):
            meta = wave_metadata(path, profile)
            if str(meta.get("canonical_source") or "").strip('"') == canonical and str(meta.get("aggregate_close_owner")).lower() == "true":
                return str(wid)
    return None


def infer_lifecycle_owner(repo: Path, profile: dict[str, Any], current_wave: str, finding_id: str, text: str) -> str | None:
    # Canonical chain gate: the defect lives in the previous canonical source's aggregate owner.
    chain = CHAIN_RE.search(text)
    if chain:
        owner = aggregate_owner_of(repo, profile, chain.group(1))
        if owner and owner != current_wave:
            return owner
    deps = dependency_ids(repo, profile, current_wave)
    low = text.lower()
    if any(word in low for word in ("dependency", "predecessor", "prerequisite")):
        mentioned = [dep for dep in deps if re.search(rf"\b{re.escape(dep)}\b", text, re.I)]
        if mentioned:
            return mentioned[0]
        if len(deps) == 1:
            return deps[0]
    candidates=[]
    for state in ("done", "pending", "blocked", "postponed"):
        candidates.extend(wid for wid, _ in wave_targets_in_folder(repo, profile, state, scheduled_only=False))
    for wid in sorted(set(candidates), key=len, reverse=True):
        if finding_id.upper().startswith(wid.upper() + "-"):
            return wid
    return None

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo", default="."); ap.add_argument("--wave", required=True)
    ap.add_argument("--manifest"); ap.add_argument("--validator-json"); ap.add_argument("--audit-report"); ap.add_argument("--phase-result"); ap.add_argument("--out")
    args=ap.parse_args(); repo=Path(args.repo).resolve(); profile=load_profile(repo)
    owner_index=build_owner_index(repo, profile); rows=[]
    if args.manifest: rows += manifest_findings(repo / args.manifest)
    if args.validator_json: rows += validator_findings(repo / args.validator_json)
    if args.audit_report: rows += audit_findings(repo / args.audit_report)
    if args.phase_result:
        phase=read_json(repo / args.phase_result)
        for finding in (phase or {}).get("findings", []) if isinstance(phase, dict) else []:
            blob=str(finding); ids=[x.upper() for x in REQUIREMENT_RE.findall(blob)]
            rows.extend((rid, "phase-result", blob[:1600]) for rid in (ids or ["UNSCOPED"]))
    findings=[]
    for rid, source, text in dedupe(rows):
        owner=None if CHAIN_RE.search(text) else owner_index.get(rid)
        inferred=infer_lifecycle_owner(repo, profile, args.wave, rid, text) if not owner else None
        if inferred:
            _, state=wave_location(repo, profile, inferred); owner=(inferred, state or "current_or_unresolved")
        findings.append(Finding(rid, source, text, owner[0] if owner else args.wave, owner[1] if owner else "current_or_unresolved", bool(HUMAN_RE.search(text))))
    result={"wave":args.wave,"finding_count":len(findings),"human_only":bool(findings) and all(f.human_only for f in findings),"findings":[asdict(f) for f in findings]}
    payload=json.dumps(result,ensure_ascii=False,indent=2)
    if args.out:
        out=repo / args.out; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(payload+"\n",encoding="utf-8")
    print(payload); return 0

if __name__ == "__main__":
    raise SystemExit(main())
