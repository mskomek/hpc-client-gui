from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
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


def subprocess_no_window_kwargs() -> dict[str, Any]:
    """Keep non-interactive runtime children from flashing consoles on Windows."""
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= int(getattr(subprocess, 'STARTF_USESHOWWINDOW', 1))
        startupinfo.wShowWindow = int(getattr(subprocess, 'SW_HIDE', 0))
        return {'creationflags': int(getattr(subprocess, 'CREATE_NO_WINDOW', 0)), 'startupinfo': startupinfo}
    return {}


def _git(repo: Path, *args: str) -> tuple[int, str]:
    executable = shutil.which('git')
    if executable is None:
        return 127, 'git-executable-unavailable'
    try:
        cp = subprocess.run([executable,'-C',str(repo),*args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', **subprocess_no_window_kwargs())
    except FileNotFoundError:
        return 127, 'git-executable-unavailable'
    except OSError as exc:
        return 126, f'git-exec-error:{exc}'
    return cp.returncode, (cp.stdout + cp.stderr).strip()


def git_capability(repo: Path) -> dict[str, Any]:
    """Read-only Git capability/status. Git is optional for Agent Core."""
    repo = Path(repo).resolve()
    code, top = _git(repo, 'rev-parse', '--show-toplevel')
    if code == 127:
        return {'status': 'unavailable', 'git_available': False, 'is_repository': False,
                'has_head': False, 'repo_root': str(repo), 'branch': None, 'head': None}
    if code != 0 or not top.strip():
        return {'status': 'not_repository', 'git_available': True, 'is_repository': False,
                'has_head': False, 'repo_root': str(repo), 'branch': None, 'head': None}
    top_path = str(Path(top.strip()).resolve())
    # Git discovery walks parent directories. A project nested inside another
    # repository is still a non-Git Agent Core project unless its own project
    # root is the Git top-level. Do not borrow VCS authority from an ancestor.
    if os.path.normcase(os.path.abspath(top_path)) != os.path.normcase(os.path.abspath(str(repo))):
        return {'status': 'not_repository', 'git_available': True, 'is_repository': False,
                'has_head': False, 'repo_root': str(repo), 'branch': None, 'head': None,
                'detected_parent_repository': top_path}
    _, branch = _git(repo, 'branch', '--show-current')
    hcode, head = _git(repo, 'rev-parse', 'HEAD')
    head_value = head.strip().splitlines()[0] if hcode == 0 and head.strip() else None
    return {'status': 'repository' if head_value else 'unborn_repository', 'git_available': True,
            'is_repository': True, 'has_head': bool(head_value), 'repo_root': top_path,
            'branch': branch.strip() or None, 'head': head_value}


def _norm_rel(value: str) -> str:
    return value.replace('\\','/').strip('/')


def _is_under(rel: str, prefixes: Iterable[str]) -> bool:
    rel = _norm_rel(rel)
    for raw in prefixes:
        p = _norm_rel(str(raw))
        if rel == p or rel.startswith(p + '/'):
            return True
    return False


def surface_key(value: str) -> str:
    """Portable collision identity for a repo-relative path or write surface.

    Separator, '.'/empty-segment, '..' (lexical) and trailing-separator
    normalization plus case folding: `src/Auth/` and `src/auth` are the same
    path on the default Windows/macOS filesystems, so they are one ownership
    identity everywhere. Display/original paths are kept by callers.
    """
    parts: list[str] = []
    for seg in str(value or '').replace('\\', '/').strip().split('/'):
        seg = seg.strip()
        if seg in ('', '.'):
            continue
        if seg == '..' and parts and parts[-1] != '..':
            parts.pop()
            continue
        parts.append(seg)
    return '/'.join(parts).casefold()


def surface_contains(surface: str, path: str) -> bool:
    """True when `path` is `surface` or below it (portable identity)."""
    s, p = surface_key(surface), surface_key(path)
    return bool(s) and (p == s or p.startswith(s + '/'))


def surfaces_overlap(a: str, b: str) -> bool:
    return surface_contains(a, b) or surface_contains(b, a)


# Agent Core authority files a Wave worker must never change in a parallel
# candidate (lifecycle directories/trackers come from the profile).
AGENT_CORE_OWNED_SURFACES = ('.tmp', '.opencode/scripts', '.opencode/protocol', '.agents/skills', '.agents/protocol')


def controller_owned_surfaces(profile: dict[str, Any]) -> list[str]:
    """Controller-owned paths: lifecycle directories, tracker/index, Agent Core runtime.

    Only the Python controller changes these (e.g. controller_close_wave()
    moves pending -> done). A parallel candidate touching any of them is
    rejected at authoring, candidate, integrated-tree and promotion gates.
    """
    paths = profile.get('paths') or {}
    out = [str(paths[k]) for k in ('pending', 'done', 'blocked', 'postponed', 'active_wave_tracker', 'waves_index')
           if paths.get(k)]
    return [*out, *AGENT_CORE_OWNED_SURFACES]


def reserved_surface_hits(paths: Iterable[str], profile_or_reserved: Any) -> list[str]:
    """`path=>reserved` for every path equal to, inside, or containing a reserved surface."""
    reserved = (controller_owned_surfaces(profile_or_reserved) if isinstance(profile_or_reserved, dict)
                else [str(r) for r in profile_or_reserved or []])
    return [f'{p}=>{r}' for p in paths if str(p).strip() for r in reserved if surfaces_overlap(str(p), r)]


def in_scheduler_scope(wave_id: str, profile: dict[str, Any]) -> bool:
    """The one scheduler-scope predicate (discovery, frontier, group barrier).

    `wave.min..max` bounds the numeric group; `scheduler.scheduled_wave_ids`,
    when present, additionally restricts it: an exact Wave ID (`W101a`) or a
    base ID (`W101`) covering every channel of that group.
    """
    try:
        number, _channel = parse_wave_id(str(wave_id))
    except ValueError:
        return False
    wave_cfg = profile.get('wave') or {}
    try:
        lower = int(wave_cfg.get('min', -10**18))
        upper = int(wave_cfg.get('max', 10**18))
    except (TypeError, ValueError):
        lower, upper = -10**18, 10**18
    if not (lower <= number <= upper):
        return False
    scheduled = [str(x).strip().lower() for x in (profile.get('scheduler') or {}).get('scheduled_wave_ids') or [] if str(x).strip()]
    if not scheduled:
        return True
    if str(wave_id).strip().lower() in scheduled:
        return True
    for entry in scheduled:
        try:
            e_num, e_ch = parse_wave_id(entry)
        except ValueError:
            continue
        if e_num == number and e_ch == '':
            return True
    return False


MANAGED_JOB_LEASE_DEFAULTS ={"max_phase_runtime_seconds": 21600, "max_no_meaningful_progress_seconds": 5400}


def managed_job_lease(profile: dict[str, Any]) -> dict[str, int]:
    """Controller lease for every managed phase worker (profile `controller` block).

    A live worker past `max_phase_runtime_seconds` since start, or past
    `max_no_meaningful_progress_seconds` since its last meaningful progress
    (never heartbeats/log bytes), is terminated by the controller. 0 disables
    one limit; absent keys use the defaults.
    """
    cfg = profile.get('controller') or {}
    out: dict[str, int] = {}
    for key, default in MANAGED_JOB_LEASE_DEFAULTS.items():
        raw = cfg.get(key, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f'controller.{key} must be an integer >= 0, got {raw!r}')
        if value < 0:
            raise ValueError(f'controller.{key} must be an integer >= 0, got {raw!r}')
        out[key] = value
    return out


PROGRESS_CONTRACT_VERSIONS = (1, 2)
PROGRESS_CONTRACT_DEFAULT_VERSION = 2
PROGRESS_CONTRACT_DEFAULT_ENABLED = True
PROGRESS_PROFILE_KEYS = ('enabled', 'contract_version')


def normalize_progress_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Single deterministic resolution of the project profile `progress` stanza.

    This is the only place in Agent Core that decides effective structured
    progress behaviour. The controller, the validators and materialization all
    call it; no worker or validator re-derives a default of its own.

    Structured progress is default ON: a missing `progress` object, `progress: {}`
    and a partially declared stanza all resolve to `enabled` + contract v2 with
    `source='default'`. Absent is the canonical default, never a legacy fallback.
    A stanza that actually declares `enabled` or `contract_version` resolves with
    `source='explicit'`, which is what makes a deliberate legacy choice visible in
    status output instead of an accidental missing-field fallback.

    Malformed and contradictory declarations raise ValueError naming the exact
    offending key, so validation and pre-dispatch resolution fail with one
    actionable reason rather than a generic schema error.
    """
    stanza = profile.get('progress')
    if stanza is None:
        stanza = {}
    if not isinstance(stanza, dict):
        raise ValueError(f'progress must be a JSON object with keys {list(PROGRESS_PROFILE_KEYS)}, '
                         f'got {type(stanza).__name__}')
    unknown = sorted(key for key in stanza if key not in PROGRESS_PROFILE_KEYS)
    if unknown:
        raise ValueError(f'progress has unknown key(s) {unknown}; supported keys are {list(PROGRESS_PROFILE_KEYS)} '
                         '(a misspelled key would otherwise resolve as an accidental missing-field default)')

    source = 'explicit' if any(key in stanza for key in PROGRESS_PROFILE_KEYS) else 'default'

    enabled = stanza.get('enabled', PROGRESS_CONTRACT_DEFAULT_ENABLED)
    if not isinstance(enabled, bool):
        raise ValueError(f'progress.enabled must be a JSON boolean, got {stanza["enabled"]!r}')

    raw = stanza.get('contract_version', PROGRESS_CONTRACT_DEFAULT_VERSION)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw not in PROGRESS_CONTRACT_VERSIONS:
        raise ValueError(f'progress.contract_version must be the integer 1 or 2, got {raw!r}')

    if not enabled and raw >= 2:
        raise ValueError(
            f'progress.enabled=false is contradictory with progress.contract_version={raw}: contract v2 makes the '
            'structured PLAN block mandatory, so it cannot be disabled. Declare deliberate legacy as '
            'progress {"enabled": false, "contract_version": 1}.')
    return {'enabled': enabled, 'contract_version': raw, 'source': source}


def progress_contract_version(profile: dict[str, Any]) -> int:
    """Deterministic worker progress contract from project config, never from output.

    1 = legacy: structured PLAN TODO optional, controller default plan fallback.
    2 = structured PLAN TODO mandatory; missing/malformed/invalid -> recovery.
    The effective default is v2 with progress enabled, so a project that does not
    declare `progress` is on v2. Only an explicit, validated `progress` stanza
    selects v1. See `normalize_progress_profile` for the single resolver.
    """
    return int(normalize_progress_profile(profile)['contract_version'])


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
    unfilled = [k for k in ('project_id',) if str(profile.get(k) or '').startswith('REPLACE_WITH')]
    wave = profile.get('wave') or {}
    unfilled += [f'wave.{k}' for k in ('min', 'max') if k in wave and (isinstance(wave[k], bool) or not isinstance(wave[k], int))]
    if unfilled:
        raise RuntimeError('Wave project profile is not configured: set ' + ', '.join(unfilled)
                           + ' (wave.min/max = the integer range of this project\'s scheduled Waves, e.g. 1 and 1 for W01; '
                           'see templates/new-project/AC_PROJECT_INSTALL_CHECKLIST.md)')
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


def program_progress_root(repo: Path, profile: dict[str, Any], program: str) -> Path:
    """Program-scoped progress root: state that must outlive any single run.

    Run directories are disposable; a Wave's identical-retry budget is not. An
    operator restart creates a new run id with a fresh ``state.json``, so any
    per-run counter silently returns to zero and the same blocker can be
    re-attempted an unlimited number of times across restarts. Durable progress
    accounting therefore lives beside the runs, keyed per project, not inside one.
    """
    return ensure_temp_layout(repo, profile) / 'agent-progress' / program


def progress_ledger_path(repo: Path, profile: dict[str, Any], program: str) -> Path:
    return program_progress_root(repo, profile, program) / 'no-progress-ledger.json'


# Bounded so a long-lived program cannot grow the ledger without limit. Oldest
# entries are evicted first; the ledger is an accounting guard, not an archive.
LEDGER_MAX_ENTRIES = 500


def load_progress_ledger(repo: Path, profile: dict[str, Any], program: str) -> dict[str, Any]:
    """Durable cross-run identical-retry counters.

    Fail-open on damage: an unreadable or malformed ledger yields an empty one so
    a corrupt guard can never wedge the program. The consequence is a reset
    budget, which is exactly today's behaviour, not a new failure mode.
    """
    path = progress_ledger_path(repo, profile, program)
    try:
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    entries = raw.get('entries')
    if not isinstance(entries, dict):
        return {}
    # Drop rows the reader can no longer trust; a malformed row is not a counter.
    return {k: v for k, v in entries.items() if isinstance(v, dict)}


def save_progress_ledger(repo: Path, profile: dict[str, Any], program: str,
                         entries: dict[str, Any]) -> None:
    path = progress_ledger_path(repo, profile, program)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Evict least-recently-seen so the ledger stays bounded.
        if len(entries) > LEDGER_MAX_ENTRIES:
            ordered = sorted(entries.items(),
                             key=lambda kv: str((kv[1] or {}).get('last_seen_run') or ''))
            entries = dict(ordered[-LEDGER_MAX_ENTRIES:])
        payload = {
            'schema_version': 1,
            'updated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
            'entries': entries,
        }
        tmp = path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        os.replace(tmp, path)
    except OSError:
        # Never fail a program because its progress guard could not be persisted.
        pass


def record_progress_attempt(repo: Path, profile: dict[str, Any], program: str,
                            key: str, run_id: str, limit: int) -> int:
    """Increment the durable counter for `key` and return the new count.

    This is the cross-run authority: the returned count includes attempts made by
    previous runs, so restarting the program cannot buy a fresh identical-retry
    budget for a blocker that has not changed.
    """
    entries = load_progress_ledger(repo, profile, program)
    row = entries.get(key)
    if not isinstance(row, dict):
        row = {'count': 0}
    count = int(row.get('count', 0) or 0) + 1
    row['count'] = count
    row['last_seen_run'] = str(run_id)
    row.setdefault('first_seen_run', str(run_id))
    row['limit'] = int(limit)
    # Keep the (bounded) set of runs that contributed, so a stall spanning
    # several restarts names them instead of looking like one run's doing.
    seen = row.get('seen_runs')
    seen = list(seen) if isinstance(seen, list) else []
    if str(run_id) not in seen:
        seen.append(str(run_id))
    row['seen_runs'] = seen[-LEDGER_MAX_ENTRIES:]
    entries[key] = row
    save_progress_ledger(repo, profile, program, entries)
    return count


def clear_progress_entry(repo: Path, profile: dict[str, Any], program: str, key: str) -> None:
    """Retire a ledger entry once the Wave genuinely moved past that blocker.

    Called only on a forward lifecycle commit or a real content/epoch change, so
    the durable budget bounds repeats of the *same* blocker and never penalises
    progress.
    """
    entries = load_progress_ledger(repo, profile, program)
    if key in entries:
        entries.pop(key, None)
        save_progress_ledger(repo, profile, program, entries)


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


# Canonical Wave identity helpers. A Wave identity is `<number><channel>`
# with an optional profile `W` prefix (e.g. `W101a`, `101a`, `W100`).
# `101` is the numeric scheduling group; `a` is the parallel channel;
# `W101a` is the unique Wave identity. `W101a != W101b` and they must never
# collapse to `W101`. All parsing/sorting must go through these helpers.
WAVE_ID_RE = re.compile(r'\AW(?P<number>\d+)(?P<channel>[a-z]?)\Z', re.I)
WAVE_ID_BARE_RE = re.compile(r'\A(?P<number>\d+)(?P<channel>[a-z]?)\Z', re.I)


def parse_wave_id(wave_id: str) -> tuple[int, str]:
    """Parse a Wave identity into (number, channel). Channel is '' when absent."""
    text = str(wave_id or '').strip()
    m = WAVE_ID_RE.match(text) or WAVE_ID_BARE_RE.match(text)
    if not m:
        raise ValueError(f'Invalid Wave identity: {wave_id!r}')
    return int(m.group('number')), (m.group('channel') or '').lower()


def wave_number_of(wave_id: str) -> int:
    """Numeric scheduling group for a Wave identity (e.g. W101a -> 101)."""
    number, _ = parse_wave_id(wave_id)
    return number


def wave_channel_of(wave_id: str) -> str:
    """Parallel channel letter for a Wave identity (e.g. W101a -> 'a', W100 -> '')."""
    _, channel = parse_wave_id(wave_id)
    return channel


def wave_group_of(wave_id: str) -> int:
    """Scheduling group number; alias for wave_number_of."""
    return wave_number_of(wave_id)


def wave_sort_key(wave_id: str) -> tuple[int, str]:
    """Deterministic ordering: (number, channel). W101a < W101b < W102a."""
    number, channel = parse_wave_id(wave_id)
    return (number, channel)


def wave_id_equal(left: str, right: str) -> bool:
    """Channel-sensitive identity comparison (case-insensitive)."""
    try:
        return wave_sort_key(left) == wave_sort_key(right) and str(left).strip().lower() == str(right).strip().lower()
    except ValueError:
        return str(left).strip().lower() == str(right).strip().lower()


def wave_title_of(path: Path) -> str:
    """First H1 title text with any canonical Wave-ID prefix removed.

    The follower renders ``<wave_id> · <wave_title>`` itself, so storing a
    heading such as ``W101a · TITLE`` verbatim would produce a duplicated
    operator label.  Normalize both ``Wave W101a — TITLE`` and
    ``W101a · TITLE`` forms deterministically at the parser boundary.
    """
    if not path.is_file():
        return path.stem
    text = _read_text(path)
    heading = re.search(r'(?m)^#\s+(.+)$', text)
    if not heading:
        return path.stem
    title = heading.group(1).strip()
    title = re.sub(r'\AWave\s+W?\d+[A-Za-z]?\s*(?:[·—:\-–]|\|)\s*', '', title, flags=re.I)
    title = re.sub(r'\AW?\d+[A-Za-z]?\s*(?:[·—:\-–]|\|)\s*', '', title, flags=re.I)
    return title or path.stem


def group_members(targets: Iterable[tuple[str, Path]], number: int) -> list[tuple[str, Path]]:
    """All Waves in `targets` belonging to numeric scheduling group `number`."""
    out = [(wid, path) for wid, path in targets if wave_number_of(str(wid)) == int(number)]
    out.sort(key=lambda item: wave_sort_key(str(item[0])))
    return out


def parallel_config(profile: dict[str, Any]) -> dict[str, Any]:
    """Effective parallel configuration with safe defaults.

    Reads the `parallel` block (preferred) with `scheduler.max_concurrency`
    as backward-compatible fallback. The controller enforces every field;
    the template declares them and validators check them.
    """
    parallel = profile.get("parallel") or {}
    scheduler = profile.get("scheduler") or {}
    try:
        max_c = parallel.get("max_concurrency", scheduler.get("max_concurrency", 2))
        max_c = int(max_c)
    except (TypeError, ValueError):
        max_c = 2
    return {
        "mode": str(parallel.get("mode") or "managed"),
        "max_concurrency": min(max(max_c, 1), 8),
        "isolation": str(parallel.get("isolation") or "git_worktree"),
        "dirty_tree_policy": str(parallel.get("dirty_tree_policy") or "serial_fallback"),
        "integration_order": str(parallel.get("integration_order") or "channel"),
        "group_barrier": str(parallel.get("group_barrier") or "lifecycle_done"),
        "integration_validators": list(parallel.get("integration_validators") or []),
        "focused_tests": list(parallel.get("focused_tests") or []),
    }


def check_parallel_group_invariants(entries: dict[str, dict[str, Any]]) -> list[str]:
    """Shared authoring invariants for one numeric parallel group.

    `entries[wave_id]` must carry normalized keys: number, channel,
    channel_group, write_surface (list), completion_dependencies (list),
    exclusive_resources (list), owned_requirements (list). Both the
    controller pre-dispatch gate and the standalone authoring validator call
    this helper so the two implementations cannot drift.
    """
    errors: list[str] = []
    ids = sorted(entries.keys(), key=lambda w: wave_sort_key(str(w)))
    if len(ids) < 2:
        return errors
    try:
        group_number = wave_number_of(str(ids[0]))
    except ValueError:
        return [f"group-identity-invalid:{ids[0]}"]
    channels: dict[str, str] = {}
    for wid in ids:
        info = entries.get(wid) or {}
        ch = str(info.get("channel") or "").lower()
        if not ch:
            errors.append(f"missing-required-parallel-metadata:{wid}:channel")
        elif ch in channels:
            errors.append(f"duplicate-channel:{ch}:{channels[ch]}:{wid}")
        else:
            channels[ch] = str(wid)
        if not list(info.get("write_surface") or []):
            errors.append(f"missing-required-parallel-metadata:{wid}:write_surface")
        if info.get("channel_group") is None:
            errors.append(f"missing-required-parallel-metadata:{wid}:channel_group")
        else:
            try:
                if int(str(info.get("channel_group"))) != int(info.get("number", group_number)):
                    errors.append(f"channel-group-mismatch:{wid}")
            except (TypeError, ValueError):
                errors.append(f"channel-group-mismatch:{wid}")
        if not list(info.get("owned_requirements") or []):
            errors.append(f"missing-required-parallel-metadata:{wid}:owned_requirements")
    member_set = set(ids)
    member_lower = {str(w).lower() for w in ids}
    for wid in ids:
        for dep in list((entries.get(wid) or {}).get("completion_dependencies") or []):
            if str(dep) in member_set or str(dep).lower() in member_lower:
                errors.append(f"sibling-dependency:{wid}:{dep}")
            try:
                if int(wave_number_of(str(dep))) > int(group_number):
                    errors.append(f"forward-dependency:{wid}:{dep}")
            except ValueError:
                pass
    surfaces = {wid: [_norm_rel(x) for x in list((entries.get(wid) or {}).get("write_surface") or [])] for wid in ids}
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            for a in surfaces.get(left, []):
                for b in surfaces.get(right, []):
                    # Portable identity: case-only/`.`/separator variants collide.
                    if surfaces_overlap(a, b):
                        if surface_key(a) == surface_key(b):
                            errors.append(f"write-surface-overlap:{left}:{right}:{a}")
                        else:
                            errors.append(f"parent-child-write-surface-overlap:{left}:{right}:{a}:{b}")
    seen_res: dict[str, str] = {}
    for wid in ids:
        for res in list((entries.get(wid) or {}).get("exclusive_resources") or []):
            key = str(res).strip()
            if not key:
                continue
            if key in seen_res:
                errors.append(f"exclusive-resource-collision:{key}:{seen_res[key]}:{wid}")
            else:
                seen_res[key] = str(wid)
    seen_req: dict[str, str] = {}
    for wid in ids:
        owned = list((entries.get(wid) or {}).get("owned_requirements") or [])
        for req in owned:
            key = str(req).strip().upper()
            if not key:
                continue
            if key in seen_req:
                errors.append(f"duplicate-requirement-ownership:{key}:{seen_req[key]}:{wid}")
            else:
                seen_req[key] = str(wid)
    return errors


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
    # Parallel channel letter (e.g. 101a/101b) is part of the identity when the profile regex captures it.
    inferred_id = _format_wave_id(number, profile) + (m.groupdict().get('channel') or '').lower()
    kind = str(fm.get('wave_kind') or 'execution')
    aggregate_owner = bool(fm.get('aggregate_close_owner', False))
    canonical_source = fm.get('canonical_source')
    owned = fm.get('owned_requirements') or fm.get('owned_requirement_patterns') or []
    if isinstance(owned, str):
        owned = [owned]
    deps = fm.get('completion_dependencies') or []
    if isinstance(deps, str): deps = [deps]
    channel = str(m.groupdict().get('channel') or '').lower()
    return {
        **fm,
        'wave_id': str(fm.get('wave_id') or inferred_id),
        'wave_number': number,
        'wave_channel': channel,
        'wave_group': number,
        'wave_title': wave_title_of(path),
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
    out: list[tuple[str, Path, tuple[int, str]]] = []
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
        if scheduled_only and not (lower <= number <= upper and in_scheduler_scope(str(meta['wave_id']), profile)):
            continue
        try:
            key = wave_sort_key(str(meta['wave_id']))
        except ValueError:
            key = (number, str(meta['wave_id']))
        out.append((str(meta['wave_id']), p, key))
    out.sort(key=lambda x: x[2])
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


def _wave_in_authority_scope(wave_id: str, scope_lower: set[str], profile: dict[str, Any]) -> bool:
    """Channel-aware scope check. Explicit channel IDs require exact match;
    numeric-range scopes accept any channel of a covered number."""
    text = str(wave_id).lower()
    if text in scope_lower:
        return True
    try:
        number, _ = parse_wave_id(str(wave_id))
    except ValueError:
        return False
    scheduler = profile.get('scheduler') or {}
    wave = profile.get('wave') or {}
    # Range-derived scope: any channel whose number is in [min,max] is covered.
    if not scheduler.get('scheduled_wave_ids'):
        wmin, wmax = wave.get('min'), wave.get('max')
        if isinstance(wmin, int) and isinstance(wmax, int) and int(wmin) <= number <= int(wmax):
            return True
    # Explicit scope may list a base ID (W101) covering its channels (W101a).
    for entry in scope_lower:
        try:
            entry_number, entry_channel = parse_wave_id(entry)
        except ValueError:
            continue
        if entry_number == number and entry_channel == '':
            return True
    return False


def lifecycle_entries(repo: Path, profile: dict[str, Any]) -> dict[str, list[tuple[str, Path]]]:
    scope = {x.lower() for x in lifecycle_authority_ids(profile)}
    out: dict[str, list[tuple[str, Path]]] = {}
    for state in ('pending', 'done', 'blocked', 'postponed'):
        for wid, path in wave_targets_in_folder(repo, profile, state):
            if scope and not _wave_in_authority_scope(wid, scope, profile):
                continue
            out.setdefault(wid, []).append((state, path))
    return out


def lifecycle_conflicts(repo: Path, profile: dict[str, Any]) -> dict[str, list[tuple[str, Path]]]:
    return {wid: entries for wid, entries in lifecycle_entries(repo, profile).items() if len(entries) > 1}


def _lexical_abspath(path: Path) -> Path:
    """Absolute path without resolving symlinks/junctions.

    Agent Core intentionally permits a project-local .tmp junction that points
    at a physical sibling temp store. Lifecycle paths must stay in the logical
    repository namespace so repo-relative receipts remain serializable.
    """
    return Path(os.path.abspath(os.fspath(path)))


def _repo_relative_posix(path: Path, repo: Path) -> str:
    """Return a repo-relative path across logical/physical alias namespaces.

    Prefer the lexical namespace used by the caller. If one side has already
    crossed a symlink/junction boundary, compare the resolved physical paths as
    a bounded fallback. Paths genuinely outside the repository still fail.
    """
    logical_path = _lexical_abspath(path)
    logical_repo = _lexical_abspath(repo)
    try:
        return logical_path.relative_to(logical_repo).as_posix()
    except ValueError:
        physical_path = logical_path.resolve()
        physical_repo = logical_repo.resolve()
        try:
            return physical_path.relative_to(physical_repo).as_posix()
        except ValueError as exc:
            raise ValueError(f'Path is outside repository: {path}') from exc


def _lifecycle_quarantine_root(repo: Path, profile: dict[str, Any]) -> Path:
    repo_root = _lexical_abspath(repo)
    parents: list[Path] = []
    for state in ('pending', 'done', 'blocked', 'postponed'):
        raw = (profile.get('paths') or {}).get(state)
        if raw:
            parents.append(_lexical_abspath(repo / str(raw)).parent)
    if not parents:
        return repo_root / '.tmp' / 'ac-lifecycle-quarantine'
    try:
        common = Path(os.path.commonpath([str(x) for x in parents]))
    except ValueError:
        common = repo_root
    try:
        common.relative_to(repo_root)
    except ValueError:
        common = repo_root
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
                    'authoritative_path': _repo_relative_posix(authoritative, repo),
                    'stale_state': state,
                    'stale_path': _repo_relative_posix(path, repo),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'reason': 'immutable-done-authority',
                }
                if apply:
                    destination = quarantine_root / state / path.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        destination = destination.with_name(destination.stem + '-' + item['sha256'][:12] + destination.suffix)
                    path.replace(destination)
                    item['quarantine_path'] = _repo_relative_posix(destination, repo)
                repairs.append(item)
        else:
            unresolved.append({
                'wave_id': wid,
                'locations': [f'{state}:{_repo_relative_posix(path, repo)}' for state, path in entries],
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
        receipt_rel = _repo_relative_posix(receipt, repo)

    remaining = lifecycle_conflicts(repo, profile) if apply else conflicts
    return {
        'status': 'AMBIGUOUS' if unresolved else ('REPAIRED' if repairs else 'PASS'),
        'repair_id': repair_id if repairs or unresolved else None,
        'repairs': repairs,
        'unresolved': unresolved,
        'remaining_conflicts': {
            wid: [f'{state}:{_repo_relative_posix(path, repo)}' for state, path in entries]
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
    wave = profile.get('wave') or {}
    if not (profile.get('scheduler') or {}).get('scheduled_wave_ids') and not (
            isinstance(wave.get('min'), int) and isinstance(wave.get('max'), int)):
        return []
    text = _read_text(repo / str(rel))
    # Same scope predicate as the scheduler: W101 covers W101a/W101b.
    return [(str(target), path) for target, path in wave_targets_in_folder(repo, profile, 'done')
            if in_scheduler_scope(str(target), profile) and not re.search(rf'\bWave {re.escape(str(target))} COMPLETE\b', text)]


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
    cap = git_capability(repo)
    return {'repo_root': str(cap.get('repo_root') or Path(repo).resolve()),
            'branch': cap.get('branch'), 'head': cap.get('head')}


def repository_content_identity(repo: Path, ignored_prefixes: Iterable[str] = ()) -> str:
    """Stable content identity with or without Git.

    Git repositories preserve tracked/untracked + mode semantics. Without Git,
    hash project files directly while excluding controller/transient metadata.
    """
    repo = Path(repo).resolve()
    ignored = list(ignored_prefixes) + ['.tmp']
    cap = git_capability(repo)
    paths: set[str] = set(); modes: dict[str, str] = {}
    if cap.get('is_repository'):
        for args in [('--cached','--others','--exclude-standard'), ()]:
            cmd = ['ls-files','-z',*args] if args else ['ls-files','-z']
            code, raw = _git(repo,*cmd)
            if code == 0: paths.update(p for p in raw.split('\0') if p)
        if not paths:
            code, raw = _git(repo,'ls-files')
            if code == 0: paths.update(raw.splitlines())
        code, raw = _git(repo,'ls-files','-s','-z')
        if code == 0:
            for rec in raw.split('\0'):
                meta, _, path = rec.partition('\t')
                if path and meta.split(' ')[0] != '100644': modes[path] = meta.split(' ')[0]
    else:
        volatile_dirs={'.git','.tmp','.agent-runs','.legacy-backup','__pycache__','.pytest_cache','.venv','venv','build','dist'}
        volatile_suffixes={'.pyc','.pyo'}
        for root, dirs, files in os.walk(repo, topdown=True, followlinks=False):
            rootp=Path(root); relroot='' if rootp==repo else rootp.relative_to(repo).as_posix(); kept=[]
            for name in dirs:
                rel=f'{relroot}/{name}'.strip('/')
                if name in volatile_dirs or _is_under(rel, ignored): continue
                child=rootp/name
                if child.is_symlink(): paths.add(rel)
                else: kept.append(name)
            dirs[:]=kept
            for name in files:
                rel=f'{relroot}/{name}'.strip('/')
                if rel and not _is_under(rel, ignored) and Path(name).suffix.lower() not in volatile_suffixes: paths.add(rel)
    h=hashlib.sha256()
    for rel in sorted(paths):
        if not rel or _is_under(rel,ignored): continue
        p=repo/rel; link=p.is_symlink()
        if not link and not p.is_file(): continue
        h.update(rel.replace('\\','/').encode('utf-8','surrogatepass')); h.update(b'\0')
        if rel in modes: h.update(f'<mode:{modes[rel]}>'.encode()); h.update(b'\0')
        elif os.name!='nt' and not link:
            try:
                if p.stat().st_mode & 0o111: h.update(b'<fs-exec>\0')
            except OSError: pass
        try: h.update(b'<symlink>'+os.readlink(p).encode('utf-8','surrogatepass') if link else p.read_bytes())
        except OSError: h.update(b'<unreadable>')
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


def process_start_marker(pid: int | None) -> str | None:
    """The one process liveness/identity primitive (controller lock + managed jobs).

    Returns the kernel start marker of a *running* process, or None when it
    is gone. A zombie (`Z`) or dead (`X`) POSIX process is gone: it no longer
    executes, it only waits to be reaped. Windows: creation time in .NET
    ticks of a STILL_ACTIVE process. Marker values are unchanged from earlier
    releases (POSIX stat field 22), so recorded identities stay valid.
    """
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if os.name == 'nt':
        # Kernel creation time gives PID-reuse protection. Spawning PowerShell here
        # timed out under load and made live controllers look dead (lock takeover risk).
        return _windows_start_ticks(pid)
    if Path('/proc/self/stat').exists():
        try:
            stat = (Path('/proc') / str(pid) / 'stat').read_text(encoding='utf-8', errors='replace')
        except OSError:
            return None
        fields = stat.rsplit(')', 1)[-1].split()  # comm may contain spaces/parens
        if not fields or fields[0] in ('Z', 'X'):
            return None
        return fields[19] if len(fields) > 19 else None
    try:  # no procfs (e.g. macOS): existence only
        os.kill(pid, 0)
    except OSError:
        return None
    return 'alive-unknown-start'


_process_start_marker = process_start_marker  # controller-lock call sites


def _windows_start_ticks(pid: int) -> str | None:
    """Process creation time as .NET UTC ticks (same value PowerShell StartTime...Ticks gave)."""
    import ctypes
    from ctypes import wintypes
    try:
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    except (OSError, AttributeError):
        return None
    if not h:
        return None
    try:
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:  # STILL_ACTIVE
            return None
        c, e, kt, ut = (wintypes.FILETIME() for _ in range(4))
        if not k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
            return None
        return str(((c.dwHighDateTime << 32) | c.dwLowDateTime) + 504911232000000000)  # FILETIME -> .NET ticks
    finally:
        k.CloseHandle(h)


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
