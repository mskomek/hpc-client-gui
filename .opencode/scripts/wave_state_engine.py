from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROFILE_REL = Path('.opencode/protocol/WAVE_PROJECT_PROFILE.json')
FRONTMATTER_RE = re.compile(r'\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)', re.S)
VALID_PHASES = {'reconcile','plan','run','repair','audit','close'}
TEMP_SUBDIRS = ('agent-runs','locks','worktrees','pytest','logs','probes','backups','scratch','legacy','os')


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8-sig')
    except FileNotFoundError:
        return ''


def _git(repo: Path, *args: str) -> tuple[int, str]:
    cp = subprocess.run(['git','-C',str(repo),*args], capture_output=True, text=True,
                        encoding='utf-8', errors='replace')
    return cp.returncode, (cp.stdout + cp.stderr).strip()


def _norm_rel(value: str) -> str:
    return value.replace('\\','/').strip('/')


def _is_under(rel: str, prefixes: Iterable[str]) -> bool:
    rel = _norm_rel(rel)
    for raw in prefixes:
        p = _norm_rel(str(raw))
        if rel == p or rel.startswith(p + '/'):
            return True
    return False


def load_profile(repo: Path) -> dict[str, Any]:
    path = repo / PROFILE_REL
    try:
        profile = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'Invalid Wave project profile: {path}: {exc}') from exc
    if not isinstance(profile, dict):
        raise RuntimeError(f'Invalid Wave project profile object: {path}')
    required = ['schema_version','project_id','wave','paths','scheduler','temp_root','global_state_owner']
    missing = [k for k in required if k not in profile]
    if missing:
        raise RuntimeError(f'Wave project profile missing keys: {missing}')
    if str(profile.get('temp_root')) != '.tmp':
        raise RuntimeError('Wave temp_root must be repository-root .tmp')
    if str(profile.get('global_state_owner')) != 'controller':
        raise RuntimeError('Wave global_state_owner must be controller')
    paths = profile.get('paths') or {}
    for key in ('pending','done','blocked','postponed'):
        if not paths.get(key):
            raise RuntimeError(f'Wave project profile paths.{key} is required')
    scheduler = profile.get('scheduler') or {}
    if scheduler.get('closed_wave_policy') != 'immutable':
        raise RuntimeError('closed_wave_policy must be immutable')
    return profile


def ensure_temp_layout(repo: Path, profile: dict[str, Any]) -> Path:
    root = repo / str(profile.get('temp_root','.tmp'))
    root.mkdir(parents=True, exist_ok=True)
    for name in TEMP_SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def configure_temp_environment(repo: Path, profile: dict[str, Any], run_id: str) -> Path:
    # A resumed controller process must never reuse the previous process' OS temp
    # directory. On Windows, stale pytest/child-process handles or inherited ACLs
    # can make an old basetemp undeletable and trap the controller in recovery.
    boot_id = f'{os.getpid()}-{time.time_ns()}'
    root = ensure_temp_layout(repo, profile) / 'os' / run_id / boot_id
    root.mkdir(parents=True, exist_ok=False)
    os.environ['TEMP'] = str(root)
    os.environ['TMP'] = str(root)
    os.environ['TMPDIR'] = str(root)
    return root


def program_run_root(repo: Path, profile: dict[str, Any], program: str) -> Path:
    return ensure_temp_layout(repo, profile) / 'agent-runs' / program


def legacy_program_roots(repo: Path, profile: dict[str, Any], program: str) -> list[Path]:
    out: list[Path] = []
    for raw in profile.get('legacy_run_roots', ['.agent-runs']):
        root = repo / str(raw) / program
        if root not in out:
            out.append(root)
    return out


def _simple_yaml_value(value: str) -> Any:
    v = value.strip()
    if not v:
        return ''
    if v.lower() in {'true','false'}:
        return v.lower() == 'true'
    if v.lower() in {'null','none','~'}:
        return None
    if (v.startswith('[') and v.endswith(']')) or (v.startswith('{') and v.endswith('}')):
        try:
            return json.loads(v.replace("'", '"'))
        except Exception:
            pass
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if re.fullmatch(r'-?\d+', v):
        try: return int(v)
        except ValueError: pass
    return v


def _parse_frontmatter(text: str) -> dict[str, Any]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, Any] = {}
    current_list: str | None = None
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if re.match(r'^\s+-\s+', line) and current_list:
            out.setdefault(current_list, []).append(_simple_yaml_value(re.sub(r'^\s+-\s+','',line)))
            continue
        if ':' not in line:
            continue
        key, value = line.split(':',1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if value == '':
            out[key] = []
            current_list = key
        else:
            out[key] = _simple_yaml_value(value)
            current_list = None
    return out


def _wave_match(path: Path, profile: dict[str, Any]) -> re.Match[str] | None:
    return re.match(str(profile['wave']['file_regex']), path.name, re.I)


def _format_wave_id(number: int, profile: dict[str, Any]) -> str:
    fmt = str(profile['wave'].get('id_format','{number}'))
    return fmt.format(number=number)


def wave_metadata(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    text = _read_text(path)
    fm = _parse_frontmatter(text)
    m = _wave_match(path, profile)
    if not m:
        raise RuntimeError(f'Wave file does not match profile pattern: {path.name}')
    num_raw = m.groupdict().get('number') or next((g for g in m.groups() if g and str(g).isdigit()), None)
    if num_raw is None:
        raise RuntimeError(f'Wave regex must expose numeric wave number: {path.name}')
    number = int(num_raw)
    inferred_id = _format_wave_id(number, profile)
    kind = str(fm.get('wave_kind') or 'execution')
    aggregate_owner = bool(fm.get('aggregate_close_owner', False))
    canonical_source = fm.get('canonical_source')
    owned = fm.get('owned_requirements') or fm.get('owned_requirement_patterns') or []
    if isinstance(owned, str):
        owned = [owned]
    deps = fm.get('completion_dependencies') or []
    if isinstance(deps, str): deps = [deps]
    return {
        **fm,
        'wave_id': str(fm.get('wave_id') or inferred_id),
        'wave_number': number,
        'wave_kind': kind,
        'canonical_source': canonical_source,
        'owned_requirements': list(owned),
        'aggregate_close_owner': aggregate_owner,
        'global_bookkeeping_owner': str(fm.get('global_bookkeeping_owner') or 'controller'),
        'completion_dependencies': list(deps),
        'evidence_policy': fm.get('evidence_policy') or 'wave-local',
        'audit_policy': fm.get('audit_policy') or 'fresh-independent',
    }


def wave_targets_in_folder(repo: Path, profile: dict[str, Any], state: str, *,
                           scheduled_only: bool = False) -> list[tuple[str, Path]]:
    rel = profile['paths'][state]
    folder = repo / str(rel)
    if not folder.is_dir():
        return []
    out: list[tuple[str, Path, int]] = []
    wave_cfg = profile.get('wave') or {}
    lower = int(wave_cfg.get('min', -10**18))
    upper = int(wave_cfg.get('max', 10**18))
    for p in folder.iterdir():
        if not p.is_file():
            continue
        m = _wave_match(p, profile)
        if not m:
            continue
        meta = wave_metadata(p, profile)
        number = int(meta['wave_number'])
        # Canonical/source-owner Waves may intentionally live beside scheduled
        # execution Waves. They remain addressable through wave_location(), but
        # profile bounds decide which Waves may enter the scheduling frontier.
        if scheduled_only and not (lower <= number <= upper):
            continue
        out.append((str(meta['wave_id']), p, number))
    out.sort(key=lambda x: (x[2], x[0]))
    return [(a,b) for a,b,_ in out]


def wave_location(repo: Path, profile: dict[str, Any], target: str) -> tuple[Path | None, str | None]:
    found: list[tuple[str,Path]] = []
    for state in ('done','pending','blocked','postponed'):
        for wid, path in wave_targets_in_folder(repo, profile, state):
            if str(wid).lower() == str(target).lower():
                found.append((state,path))
    if not found:
        return None, None
    # CLOSED/done is authoritative even if stale duplicate active files exist.
    for state,path in found:
        if state == 'done':
            return path, state
    # deterministic precedence for active states
    for preferred in ('pending','blocked','postponed'):
        for state,path in found:
            if state == preferred:
                return path,state
    return found[0][1], found[0][0]


def pending_targets(repo: Path, profile: dict[str, Any]) -> list[tuple[str, Path]]:
    # Scheduler enumeration is strictly bounded by profile.wave.min/max.
    # Explicit owner lookup remains unbounded through wave_location().
    done_ids = {wid.lower() for wid,_ in wave_targets_in_folder(repo, profile, 'done', scheduled_only=True)}
    result: list[tuple[str,Path]] = []
    for wid,path in wave_targets_in_folder(repo, profile, 'pending', scheduled_only=True):
        if wid.lower() in done_ids:
            continue
        result.append((wid,path))
    return result



def lifecycle_authority_ids(profile: dict[str, Any]) -> set[str]:
    scheduler = profile.get('scheduler') or {}
    wave = profile.get('wave') or {}
    ids = {str(x) for x in (scheduler.get('scheduled_wave_ids') or [])}
    if not ids and isinstance(wave.get('min'), int) and isinstance(wave.get('max'), int):
        ids.update(_format_wave_id(n, profile) for n in range(int(wave['min']), int(wave['max']) + 1))
    aggregate = profile.get('aggregate') or {}
    ids.update(str(x) for x in (aggregate.get('owner_wave_ids') or []))
    cmin, cmax = aggregate.get('canonical_min'), aggregate.get('canonical_max')
    if isinstance(cmin, int) and isinstance(cmax, int) and cmin <= cmax:
        ids.update(_format_wave_id(n, profile) for n in range(cmin, cmax + 1))
    return ids


def lifecycle_entries(repo: Path, profile: dict[str, Any]) -> dict[str, list[tuple[str, Path]]]:
    scope = {x.lower() for x in lifecycle_authority_ids(profile)}
    out: dict[str, list[tuple[str, Path]]] = {}
    for state in ('pending', 'done', 'blocked', 'postponed'):
        for wid, path in wave_targets_in_folder(repo, profile, state):
            if scope and wid.lower() not in scope:
                continue
            out.setdefault(wid, []).append((state, path))
    return out


def lifecycle_conflicts(repo: Path, profile: dict[str, Any]) -> dict[str, list[tuple[str, Path]]]:
    return {wid: entries for wid, entries in lifecycle_entries(repo, profile).items() if len(entries) > 1}


def _lifecycle_quarantine_root(repo: Path, profile: dict[str, Any]) -> Path:
    parents: list[Path] = []
    for state in ('pending', 'done', 'blocked', 'postponed'):
        raw = (profile.get('paths') or {}).get(state)
        if raw:
            parents.append((repo / str(raw)).resolve().parent)
    if not parents:
        return repo / '.tmp' / 'ac-lifecycle-quarantine'
    try:
        common = Path(os.path.commonpath([str(x) for x in parents]))
    except ValueError:
        common = repo
    try:
        common.relative_to(repo.resolve())
    except ValueError:
        common = repo
    return common / 'bak' / 'auto-quarantine'


def safe_repair_lifecycle(repo: Path, profile: dict[str, Any], *, apply: bool = False,
                          reason: str = 'preflight') -> dict[str, Any]:
    conflicts = lifecycle_conflicts(repo, profile)
    repair_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + f'-{os.getpid()}-{time.time_ns()}'
    repairs: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    quarantine_root = _lifecycle_quarantine_root(repo, profile) / repair_id

    for wid in sorted(conflicts):
        entries = conflicts[wid]
        done_entries = [(state, path) for state, path in entries if state == 'done']
        if (profile.get('scheduler') or {}).get('closed_wave_policy') == 'immutable' and len(done_entries) == 1:
            authoritative = done_entries[0][1]
            for state, path in entries:
                if state == 'done':
                    continue
                item = {
                    'wave_id': wid,
                    'authoritative_state': 'done',
                    'authoritative_path': authoritative.relative_to(repo).as_posix(),
                    'stale_state': state,
                    'stale_path': path.relative_to(repo).as_posix(),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'reason': 'immutable-done-authority',
                }
                if apply:
                    destination = quarantine_root / state / path.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        destination = destination.with_name(destination.stem + '-' + item['sha256'][:12] + destination.suffix)
                    path.replace(destination)
                    item['quarantine_path'] = destination.relative_to(repo).as_posix()
                repairs.append(item)
        else:
            unresolved.append({
                'wave_id': wid,
                'locations': [f'{state}:{path.relative_to(repo).as_posix()}' for state, path in entries],
                'reason': 'ambiguous-lifecycle-authority',
            })

    receipt_rel = None
    if apply and (repairs or unresolved):
        receipt_dir = ensure_temp_layout(repo, profile) / 'ac-lifecycle-repair'
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt = receipt_dir / f'{repair_id}.json'
        payload = {
            'schema_version': 1,
            'repair_id': repair_id,
            'reason': reason,
            'closed_wave_policy': (profile.get('scheduler') or {}).get('closed_wave_policy'),
            'repairs': repairs,
            'unresolved': unresolved,
        }
        tmp = receipt.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, receipt)
        receipt_rel = receipt.relative_to(repo).as_posix()

    remaining = lifecycle_conflicts(repo, profile) if apply else conflicts
    return {
        'status': 'AMBIGUOUS' if unresolved else ('REPAIRED' if repairs else 'PASS'),
        'repair_id': repair_id if repairs or unresolved else None,
        'repairs': repairs,
        'unresolved': unresolved,
        'remaining_conflicts': {
            wid: [f'{state}:{path.relative_to(repo).as_posix()}' for state, path in entries]
            for wid, entries in remaining.items()
        },
        'receipt': receipt_rel,
    }


def ensure_lifecycle_integrity(repo: Path, profile: dict[str, Any], *, apply_safe: bool = True,
                               reason: str = 'controller') -> dict[str, Any]:
    result = safe_repair_lifecycle(repo, profile, apply=apply_safe, reason=reason)
    if result['unresolved'] or result['remaining_conflicts']:
        raise RuntimeError('Ambiguous Wave lifecycle conflict: ' + json.dumps(result, ensure_ascii=False))
    return result


def current_target(repo: Path, profile: dict[str, Any]) -> tuple[str | None, Path | None]:
    candidates = pending_targets(repo, profile)
    if candidates:
        return candidates[0]
    # blocked/postponed remain lifecycle-visible but normal scheduler does not silently
    # reinterpret them as pending; caller may explicitly route/repair them.
    return None, None


def reconcile_active_wave_tracker(repo: Path, profile: dict[str, Any], *, reason: str) -> dict[str, str] | None:
    """Reconcile the configured active-Wave tracker from lifecycle truth atomically.

    Lifecycle directories remain the authority. The tracker is derived state only and
    must never become a second scheduler authority.
    """
    rel = (profile.get('paths') or {}).get('active_wave_tracker')
    if not rel:
        return None
    tracker = repo / str(rel)
    if not tracker.is_file():
        raise RuntimeError(f'Configured active Wave tracker is missing: {tracker}')
    target, wave_path = current_target(repo, profile)
    values = {
        'current_wave': target or 'complete',
        'status': 'PENDING' if target else 'COMPLETE',
        'wave_file': wave_path.relative_to(repo).as_posix() if wave_path else '',
        'reason': reason,
        'gate': f'Wave {target} is the next pending execution wave.' if target else 'No pending execution Wave remains.',
    }
    lines = tracker.read_text(encoding='utf-8-sig').splitlines()
    for key, value in values.items():
        for index, line in enumerate(lines):
            if line.startswith(f'{key}:'):
                lines[index] = f'{key}: {value}'
                break
        else:
            lines.append(f'{key}: {value}')
    payload = '\n'.join(lines) + '\n'
    tmp = tracker.with_name(f'.{tracker.name}.tmp-{os.getpid()}-{time.time_ns()}')
    try:
        tmp.write_text(payload, encoding='utf-8')
        os.replace(tmp, tracker)
    finally:
        tmp.unlink(missing_ok=True)
    return values


def waves_index_missing(repo: Path, profile: dict[str, Any]) -> list[tuple[str, Path]]:
    """Scheduled done Waves without a `Wave <id> COMPLETE` entry in the configured index.

    Scoped to the scheduled program (scheduled_wave_ids, else wave.min..max) exactly
    like validate-wave-orchestration; legacy done files are never back-filled.
    """
    rel = (profile.get('paths') or {}).get('waves_index')
    if not rel or not bool((profile.get('capabilities') or {}).get('waves_index')):
        return []
    scheduled = {str(x) for x in (profile.get('scheduler') or {}).get('scheduled_wave_ids') or []}
    wave = profile.get('wave') or {}
    if not scheduled and isinstance(wave.get('min'), int) and isinstance(wave.get('max'), int):
        scheduled = {_format_wave_id(n, profile) for n in range(wave['min'], wave['max'] + 1)}
    text = _read_text(repo / str(rel))
    return [(str(target), path) for target, path in wave_targets_in_folder(repo, profile, 'done')
            if str(target) in scheduled and not re.search(rf'\bWave {re.escape(str(target))} COMPLETE\b', text)]


def reconcile_waves_index(repo: Path, profile: dict[str, Any]) -> list[str]:
    """Append factual entries for done Waves the index is missing.

    Entries derive only from lifecycle truth (done file, its H1 title, the Git
    commit that archived it) and never claim audit/test results. The index is a
    derived log, never scheduler authority.
    """
    missing = waves_index_missing(repo, profile)
    if not missing:
        return []
    index = repo / str(profile['paths']['waves_index'])
    lines = []
    for target, path in missing:
        rel = path.relative_to(repo).as_posix()
        heading = re.search(r'(?m)^#\s+(.+)$', _read_text(path))
        title = re.sub(rf'^Wave\s+{re.escape(target)}\s*[—:-]\s*', '', heading.group(1).strip()) if heading else path.stem
        code, log = _git(repo, 'log', '--diff-filter=A', '--format=%as %H', '--', rel)
        first = log.splitlines()[-1].split() if code == 0 and log.strip() else []
        day = first[0] if first else time.strftime('%Y-%m-%d', time.gmtime())
        commit = f'`{first[1]}`' if len(first) > 1 else 'not yet committed'
        lines.append(f'{day} Wave {target} COMPLETE: {title}; archived to `{rel}`; archive commit {commit} '
                     f'(controller index reconciliation from lifecycle truth).')
    existing = _read_text(index)
    payload = existing.rstrip('\n') + ('\n\n' if existing.strip() else '') + '\n'.join(lines) + '\n'
    tmp = index.with_name(f'.{index.name}.tmp-{os.getpid()}-{time.time_ns()}')
    try:
        tmp.write_text(payload, encoding='utf-8')
        os.replace(tmp, index)
    finally:
        tmp.unlink(missing_ok=True)
    return [target for target, _ in missing]


def aggregate_validation_required(profile: dict[str, Any], meta: dict[str, Any], phase: str) -> bool:
    if str(phase).lower() != 'close':
        return False
    if not bool(meta.get('aggregate_close_owner')):
        return False
    caps = profile.get('capabilities') or {}
    if not bool(caps.get('canonical_source_closeout', False)):
        return False
    validator = (profile.get('aggregate') or {}).get('validator_script')
    return bool(validator)


def repo_identity(repo: Path) -> dict[str, str | None]:
    code, top = _git(repo,'rev-parse','--show-toplevel')
    root = str(Path(top).resolve()) if code == 0 and top else str(repo.resolve())
    _, branch = _git(repo,'branch','--show-current')
    _, head = _git(repo,'rev-parse','HEAD')
    return {'repo_root':root,'branch':branch or None,'head':head or None}


def repository_content_identity(repo: Path, ignored_prefixes: Iterable[str] = ()) -> str:
    ignored = list(ignored_prefixes) + ['.tmp']
    paths: set[str] = set()
    for args in [('--cached','--others','--exclude-standard'), ()]:
        cmd = ['ls-files','-z',*args] if args else ['ls-files','-z']
        code, raw = _git(repo,*cmd)
        if code == 0:
            paths.update(p for p in raw.split('\0') if p)
    # _git strips trailing NUL and may concatenate stderr; fallback to tracked list works.
    if not paths:
        code, raw = _git(repo,'ls-files')
        if code == 0:
            paths.update(raw.splitlines())
    h = hashlib.sha256()
    for rel in sorted(paths):
        rel = rel.strip()
        if not rel or _is_under(rel, ignored):
            continue
        p = repo / rel
        if not p.is_file():
            continue
        h.update(rel.replace('\\','/').encode('utf-8','surrogatepass')); h.update(b'\0')
        try:
            h.update(p.read_bytes())
        except OSError:
            h.update(b'<unreadable>')
        h.update(b'\0')
    return h.hexdigest()


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(_read_text(path))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def discover_unfinished_run(repo: Path, profile: dict[str, Any], program: str) -> tuple[Path | None, str | None]:
    candidates: list[tuple[float,Path,str]] = []
    canonical_root = program_run_root(repo, profile, program)
    roots = [(canonical_root,'canonical')] + [(p,'legacy') for p in legacy_program_roots(repo,profile,program)]
    seen: set[Path] = set()
    project = str(profile['project_id'])
    identity = repo_identity(repo)
    for root,kind in roots:
        if not root.is_dir():
            continue
        for state_path in root.glob('*/state.json'):
            if state_path in seen: continue
            seen.add(state_path)
            data = _read_state(state_path)
            if not data or data.get('terminal') is True:
                continue
            saved_project = str(data.get('project') or '')
            if saved_project and saved_project != project:
                continue
            saved_repo = str(data.get('repository_identity') or '')
            if saved_repo and os.path.normcase(saved_repo) != os.path.normcase(str(identity['repo_root'])):
                continue
            try: ts = state_path.stat().st_mtime
            except OSError: ts = 0.0
            candidates.append((ts,state_path,kind))
    if not candidates:
        return None,None
    candidates.sort(key=lambda x:x[0], reverse=True)
    _, path, kind = candidates[0]
    return path,kind


def resume_classification(repo: Path, profile: dict[str, Any], saved: dict[str, Any] | None,
                          source_kind: str | None) -> tuple[str,str | None,str]:
    truth_target, _ = current_target(repo, profile)
    if not saved:
        return 'NEW_RUN_FROM_REPO_TRUTH', truth_target, 'reconcile'
    if saved.get('terminal') is True:
        return 'NEW_RUN_FROM_REPO_TRUTH', truth_target, 'reconcile'
    project = str(profile['project_id'])
    if saved.get('project') and str(saved.get('project')) != project:
        return 'STALE_RUN', truth_target, 'reconcile'
    identity = repo_identity(repo)
    if saved.get('repository_identity') and os.path.normcase(str(saved.get('repository_identity'))) != os.path.normcase(str(identity['repo_root'])):
        return 'STALE_RUN', truth_target, 'reconcile'
    if saved.get('branch') and identity.get('branch') and str(saved.get('branch')) != str(identity.get('branch')):
        return 'STALE_RUN', truth_target, 'reconcile'
    saved_target = str(saved.get('current_wave') or '') or None
    saved_phase = str(saved.get('phase') or 'reconcile').lower()
    if saved_phase not in VALID_PHASES:
        saved_phase = 'reconcile'
    if saved_target:
        _, loc = wave_location(repo, profile, saved_target)
        if loc == 'done' and saved_target != truth_target:
            return 'RECONCILE_FORWARD', truth_target, 'reconcile'
        if loc is None:
            return 'STALE_RUN', truth_target, 'reconcile'
    if truth_target and saved_target and truth_target != saved_target:
        return 'RECONCILE_FORWARD', truth_target, 'reconcile'
    if source_kind == 'legacy':
        return 'IMPORT_LEGACY_RUN', truth_target or saved_target, saved_phase
    return 'RESUME', truth_target or saved_target, saved_phase


def semantic_finding_key(canonical_source: str | None, requirement_id: str | None,
                         validator_id: str | None, normalized_failure_code: str | None,
                         affected_component: str | None) -> str:
    payload = {
        'canonical_source': (canonical_source or '').strip().upper(),
        'requirement_id': (requirement_id or '').strip().upper(),
        'validator_id': (validator_id or '').strip().lower(),
        'failure_code': (normalized_failure_code or '').strip().lower(),
        'component': (affected_component or '').strip().lower(),
    }
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def no_progress_key(target: str, phase: str, semantic_finding: str, content_identity: str) -> str:
    # A repair -> audit loop is still the same no-progress finding.  Do not
    # let the phase transition reset the guard; the content identity already
    # distinguishes a real implementation/evidence change.
    raw = '|'.join([str(target),str(semantic_finding),str(content_identity)])
    return hashlib.sha256(raw.encode()).hexdigest()


def _process_start_marker(pid: int) -> str | None:
    if pid <= 0:
        return None
    if os.name != 'nt':
        p = Path('/proc') / str(pid) / 'stat'
        try:
            parts = p.read_text().split()
            return parts[21] if len(parts) > 21 else None
        except OSError:
            try:
                os.kill(pid,0); return 'alive-unknown-start'
            except OSError:
                return None
    # Windows: PowerShell creation time gives PID-reuse protection without extra deps.
    try:
        cp = subprocess.run(['powershell','-NoProfile','-Command',
                             f"$p=Get-Process -Id {pid} -ErrorAction Stop; $p.StartTime.ToUniversalTime().Ticks"],
                            capture_output=True,text=True,timeout=5)
        return cp.stdout.strip() if cp.returncode == 0 and cp.stdout.strip() else None
    except Exception:
        return None


def _lock_retryable(exc: OSError) -> bool:
    return isinstance(exc, PermissionError) or getattr(exc, 'winerror', None) in {5, 32, 33}


def live_controller_locks(repo: Path, profile: dict[str, Any]) -> list[str]:
    """Controller locks whose recorded process is still the same live process."""
    live = []
    for path in sorted((repo / str(profile.get('temp_root') or '.tmp') / 'locks').glob('*.lock')):
        data = _read_state(path) or {}
        start = _process_start_marker(int(data.get('pid') or 0))
        if start and start == str(data.get('process_start_time') or ''):
            live.append(f"{path.name} run_id={data.get('run_id')} pid={data.get('pid')}")
    return live


@dataclass
class ControllerLock:
    path: Path
    run_id: str
    payload: dict[str, Any]
    released: bool = False

    @classmethod
    def acquire(cls, repo: Path, profile: dict[str, Any], program: str, run_id: str) -> 'ControllerLock':
        root = ensure_temp_layout(repo, profile) / 'locks'
        path = root / f'{program}.lock'
        identity = repo_identity(repo)
        pid = os.getpid()
        start = _process_start_marker(pid) or f'pid-{pid}-unknown'
        payload = {
            'run_id':run_id,'pid':pid,'process_start_time':start,
            'repository_identity':identity['repo_root'],'branch':identity['branch'],
            'program':program,'heartbeat':time.time(),'created_at':time.time(),
        }
        tmp_path = path.with_suffix('.lock.tmp')
        for attempt in range(5):
            try:
                if tmp_path.exists():
                    try:
                        os.replace(tmp_path, root / f'{path.name}.stale-{os.getpid()}-{time.time_ns()}.tmp')
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        if not _lock_retryable(exc) or attempt == 4:
                            raise RuntimeError(f'Unable to quarantine stale temporary lock after bounded retries: {tmp_path}') from exc
                        time.sleep(0.05 * (attempt + 1))
                        continue
                fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY)
                with os.fdopen(fd,'w',encoding='utf-8') as fh:
                    json.dump(payload,fh,indent=2); fh.write('\n')
                return cls(path,run_id,payload)
            except FileExistsError:
                existing = _read_state(path) or {}
                ep = int(existing.get('pid') or 0)
                current_start = _process_start_marker(ep)
                expected_start = str(existing.get('process_start_time') or '')
                same_process = bool(current_start and expected_start and current_start == expected_start)
                same_repo = os.path.normcase(str(existing.get('repository_identity') or '')) == os.path.normcase(str(identity['repo_root']))
                same_program = str(existing.get('program') or program) == program
                if same_process and same_repo and same_program:
                    raise RuntimeError(f'Live Wave controller lock exists: {path} run_id={existing.get("run_id")} pid={ep}')
                # stale/PID-reused/foreign lock at the same repo path: safe takeover
                quarantine = root / f'{path.name}.stale-{os.getpid()}-{time.time_ns()}'
                try:
                    os.replace(path, quarantine)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    if not _lock_retryable(exc) or attempt == 4:
                        raise RuntimeError(
                            f'Unable to quarantine stale Wave controller lock after bounded retries: {path}'
                        ) from exc
                    time.sleep(0.05 * (attempt + 1))
        raise RuntimeError(f'Unable to acquire Wave controller lock after bounded retries: {path}')

    def heartbeat(self) -> None:
        if self.released: return
        self.payload['heartbeat'] = time.time()
        tmp = self.path.with_suffix('.lock.tmp')
        tmp.write_text(json.dumps(self.payload,indent=2)+'\n',encoding='utf-8')
        os.replace(tmp,self.path)

    def release(self) -> None:
        if self.released: return
        try:
            current = _read_state(self.path) or {}
            if str(current.get('run_id')) == self.run_id and int(current.get('pid') or -1) == os.getpid():
                self.path.unlink(missing_ok=True)
        finally:
            self.released = True
