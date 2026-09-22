from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

REQ_RE = re.compile(r"\b(?:HPC-)?W\d{2,3}-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
IMPI_WAVE_RE = re.compile(r"WAVE_(\d{3})_.*\.md$", re.I)
HPC_WAVE_RE = re.compile(r"^(W\d{2})\.md$", re.I)
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
    except FileNotFoundError:
        return ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def wave_key_from_path(path: Path) -> str | None:
    m = IMPI_WAVE_RE.search(path.name)
    if m:
        return m.group(1)
    m = HPC_WAVE_RE.search(path.name)
    if m:
        return m.group(1).upper()
    return None


def owned_ids_from_wave(text: str) -> set[str]:
    markers = ("Canonical requirement IDs owned", "Owned stable requirement IDs")
    for marker in markers:
        if marker in text:
            tail = text.split(marker, 1)[1]
            # Stop at next H2 so we don't accidentally claim references from later sections.
            tail = re.split(r"(?m)^##\s+", tail, maxsplit=1)[0]
            return set(REQ_RE.findall(tail))
    return set()


def build_owner_index(repo: Path) -> dict[str, tuple[str, str]]:
    index: dict[str, tuple[str, str]] = {}
    precedence = {"done": 0, "pending": 1, "blocked": 2, "postponed": 3}
    for state in ("done", "pending", "blocked", "postponed"):
        folder = repo / "waves" / state
        if not folder.is_dir():
            continue
        for path in folder.glob("*.md"):
            wave = wave_key_from_path(path)
            if not wave:
                continue
            for req in owned_ids_from_wave(read_text(path)):
                # CLOSED/done is authoritative; stale active duplicates cannot reopen it.
                if req not in index or precedence[state] < precedence[index[req][1]]:
                    index[req] = (wave, state)
    return index


def collect_ids_from_obj(obj: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            ids.update(REQ_RE.findall(str(k)))
            ids.update(collect_ids_from_obj(v))
    elif isinstance(obj, list):
        for item in obj:
            ids.update(collect_ids_from_obj(item))
    elif isinstance(obj, str):
        ids.update(REQ_RE.findall(obj))
    return ids


def manifest_findings(manifest_path: Path) -> list[tuple[str, str, str]]:
    data = read_json(manifest_path)
    if not isinstance(data, dict):
        return []
    out: list[tuple[str, str, str]] = []
    for key in ("requirements", "blockers"):
        items = data.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            blob = json.dumps(item, ensure_ascii=False) if not isinstance(item, str) else item
            upper = blob.upper()
            # Requirement IDs legitimately contain tokens such as BLOCK/HARD.
            # Only disposition/status/result fields can make a PASS record bad.
            if isinstance(item, dict):
                state = " ".join(
                    str(item.get(k, ""))
                    for k in ("disposition", "status", "result", "state")
                ).upper()
            else:
                state = upper
            is_bad = any(t in state for t in ("FAIL", "BLOCK", "REOPEN", "MISSING", "NOT_RUN", "AWAITING"))
            if key == "blockers":
                is_bad = True
            if not is_bad:
                continue
            ids = REQ_RE.findall(blob)
            if ids:
                for rid in ids:
                    out.append((rid, f"manifest:{key}", blob[:1600]))
            else:
                out.append(("UNSCOPED", f"manifest:{key}", blob[:1600]))
    return out


def validator_findings(path: Path) -> list[tuple[str, str, str]]:
    data = read_json(path)
    if not isinstance(data, dict):
        return []
    out: list[tuple[str, str, str]] = []
    reasons = data.get("failure_reasons", [])
    if not isinstance(reasons, list):
        reasons = [reasons]
    for reason in reasons:
        blob = json.dumps(reason, ensure_ascii=False) if not isinstance(reason, str) else reason
        ids = REQ_RE.findall(blob)
        if ids:
            out.extend((rid, "validator", blob[:1600]) for rid in ids)
        else:
            out.append(("UNSCOPED", "validator", blob[:1600]))
    # Some validators expose failing IDs outside failure_reasons.
    for rid in sorted(collect_ids_from_obj(data)):
        if not any(x[0] == rid for x in out):
            out.append((rid, "validator", "Referenced by validator output"))
    return out


def audit_findings(path: Path) -> list[tuple[str, str, str]]:
    text = read_text(path)
    if not text:
        return []
    upper = text.upper()
    if "WAVE_PHASE_STATUS: PASS" in upper or "AUDITOR DECISION:** `PASS`" in upper:
        return []
    out: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if any(t in line.upper() for t in ("REOPEN", "BLOCK", "FINDING", "MISSING", "STALE", "FAIL")):
            ids = REQ_RE.findall(line)
            if ids:
                out.extend((rid, "audit", line.strip()[:1600]) for rid in ids)
    if not out and any(t in upper for t in ("REOPEN", "BLOCKED", "FAIL")):
        out.append(("UNSCOPED", "audit", "Audit is non-PASS; inspect report for unscoped finding."))
    return out


def dedupe(rows: Iterable[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    out = []
    for row in rows:
        if row not in seen:
            seen.add(row)
            out.append(row)
    return out



def dependencies_for_wave(repo: Path, wave: str) -> list[str]:
    if not re.fullmatch(r"W\d{2}", wave, re.I):
        return []
    for state in ("pending", "done", "blocked", "postponed"):
        path = repo / "waves" / state / f"{wave.upper()}.md"
        text = read_text(path)
        if not text:
            continue
        m = re.search(r"(?mi)^-\s*\*\*Dependencies:\*\*\s*(.+)$", text)
        if not m:
            return []
        return list(dict.fromkeys(re.findall(r"\bW\d{2}\b", m.group(1).upper())))
    return []


def hpc_finding_owner(repo: Path, current_wave: str, finding_id: str, text: str) -> str | None:
    if not re.fullmatch(r"W\d{2}", current_wave, re.I):
        return None
    low = text.lower()
    # Dependency/predecessor findings belong to the predecessor even when the
    # finding ID was minted by the dependent Wave (for example W07-AUDIT-002).
    if any(word in low for word in ("dependency", "predecessor", "prerequisite")):
        deps = dependencies_for_wave(repo, current_wave)
        mentioned = [dep for dep in deps if re.search(rf"\b{re.escape(dep)}\b", text, re.I)]
        if mentioned:
            return mentioned[0]
        if len(deps) == 1:
            return deps[0]
    # Lifecycle finding IDs such as W06-AUDIT-002 belong to W06 even though
    # they are not product requirement IDs in the registry.
    m = re.match(r"^(W\d{2})-(?:AUDIT|CLOSE|REPAIR|PLAN|RUN)-", finding_id, re.I)
    if m:
        owner = m.group(1).upper()
        if any((repo / "waves" / state / f"{owner}.md").exists() for state in ("pending", "done", "blocked", "postponed")):
            return owner
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--wave", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--validator-json")
    ap.add_argument("--audit-report")
    ap.add_argument("--phase-result")
    ap.add_argument("--out")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    owner_index = build_owner_index(repo)
    rows: list[tuple[str, str, str]] = []
    if args.manifest:
        rows += manifest_findings(repo / args.manifest)
    if args.validator_json:
        rows += validator_findings(repo / args.validator_json)
    if args.audit_report:
        rows += audit_findings(repo / args.audit_report)
    if args.phase_result:
        phase = read_json(repo / args.phase_result)
        for finding in (phase or {}).get("findings", []) if isinstance(phase, dict) else []:
            blob = str(finding)
            ids = REQ_RE.findall(blob)
            rows.extend((rid, "phase-result", blob[:1600]) for rid in (ids or ["UNSCOPED"]))

    findings: list[Finding] = []
    for rid, source, text in dedupe(rows):
        owner = owner_index.get(rid)
        inferred = hpc_finding_owner(repo, args.wave, rid, text) if not owner else None
        if inferred:
            inferred_state = next((state for state in ("pending", "done", "blocked", "postponed")
                                   if (repo / "waves" / state / f"{inferred}.md").exists()), "current_or_unresolved")
            owner = (inferred, inferred_state)
        findings.append(
            Finding(
                finding_id=rid,
                source=source,
                text=text,
                execution_owner=owner[0] if owner else args.wave,
                owner_state=owner[1] if owner else "current_or_unresolved",
                human_only=bool(HUMAN_RE.search(text)),
            )
        )

    result = {
        "wave": args.wave,
        "finding_count": len(findings),
        "human_only": bool(findings) and all(f.human_only for f in findings),
        "findings": [asdict(f) for f in findings],
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
