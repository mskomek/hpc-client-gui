from __future__ import annotations
import argparse, getpass, json, os, re, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FULL_SHA = re.compile(r'^[0-9a-f]{40}$')
REQ_TOKEN = re.compile(r'\bHPC-[A-Z0-9-]+\b')
BAD_MARKER = re.compile(r'NOT IMPLEMENTED|GAP|UNKNOWN|IMPLICIT|TODO|FIXME|PARTIAL|NOT_TESTED|UNBOUNDED|MISSING|BROKEN|DEFERRED|NO_OP|STUB', re.I)
DISPOSITIONS = {'PASS','JUSTIFIED_NA','ALLOWED_DEFERRED','FAIL_BLOCKED'}


def _load_profile(root: Path | None=None) -> dict[str, Any]:
    root=root or ROOT
    return json.loads((root/'.opencode/protocol/WAVE_PROJECT_PROFILE.json').read_text(encoding='utf-8-sig'))

def _git(root: Path, *args: str) -> tuple[int,str]:
    cp=subprocess.run(['git','-C',str(root),*args],text=True,capture_output=True,encoding='utf-8',errors='replace',check=False)
    return cp.returncode,(cp.stdout+cp.stderr).strip()

def _simple_yaml(text: str) -> dict[str,Any]:
    m=re.match(r'\A\ufeff?---\r?\n(.*?)\r?\n---(?:\r?\n|$)',text,re.S)
    if not m:return {}
    out:dict[str,Any]={}; current=None
    for raw in m.group(1).splitlines():
        line=raw.rstrip()
        if not line.strip() or line.lstrip().startswith('#'):continue
        lm=re.match(r'^\s+-\s+(.*)$',line)
        if lm and current:
            v=lm.group(1).strip().strip('"\''); out.setdefault(current,[]).append(v); continue
        if ':' not in line:continue
        k,v=line.split(':',1); k=k.strip(); v=v.strip()
        if not v:out[k]=[]; current=k; continue
        current=None
        vl=v.lower()
        if vl in {'true','false'}:out[k]=(vl=='true')
        elif v=='[]':out[k]=[]
        else:out[k]=v.strip('"\'')
    return out

def _canonical_wave_files(root: Path, profile: dict[str,Any]) -> dict[str,Path]:
    rx=re.compile(profile['wave']['file_regex'],re.I); found:dict[str,Path]={}
    for state in ('done','pending','blocked','postponed'):
        folder=root/profile['paths'][state]
        if not folder.is_dir():continue
        for p in folder.iterdir():
            if not p.is_file():continue
            m=rx.match(p.name)
            if not m:continue
            number=int(m.groupdict().get('number') or next(x for x in m.groups() if str(x).isdigit()))
            part=m.groupdict().get('part')
            # Decimal split parts (W57.1) are Waves of their own, not their base number.
            wid=profile['wave']['id_format'].format(number=number)+(f'.{part}' if part else '')
            if wid not in found or state=='done':found[wid]=p
    return found

def _normalize_wave_id(wave: str|int, profile: dict[str,Any]) -> str:
    if isinstance(wave,int): return profile['wave']['id_format'].format(number=wave)
    s=str(wave).strip().upper()
    if re.fullmatch(r'\d+',s):return profile['wave']['id_format'].format(number=int(s))
    return s

def _required_ids(wave: str|int, root: Path|None=None) -> set[str]:
    root=root or ROOT; profile=_load_profile(root); wid=_normalize_wave_id(wave,profile)
    files=_canonical_wave_files(root,profile)
    if wid not in files:raise FileNotFoundError(f'canonical Wave not found: {wid}')
    text=files[wid].read_text(encoding='utf-8-sig'); fm=_simple_yaml(text)
    owned=fm.get('owned_requirements') or []
    if isinstance(owned,str):owned=[owned]
    if not owned:
        # legacy fallback only for migration diagnostics
        for title in ('Owned stable requirement IDs','Owned TODO-detail IDs'):
            m=re.search(rf'(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^##\s|\Z)',text)
            if m: owned += REQ_TOKEN.findall(m.group(1))
    shared=((profile.get('evidence') or {}).get('shared_requirement_ids') or [])
    return {str(x) for x in [*shared,*owned] if str(x).strip()}

def _manifest_path(root: Path, profile: dict[str,Any], wid: str) -> Path:
    template=(profile.get('evidence') or {}).get('manifest_template','artifacts/wave_{wave_id}/WAVE_{wave_id}_EVIDENCE_MANIFEST.json')
    return root/str(template).format(wave_id=wid,wave_number=int(re.sub(r'\D','',wid) or '0'))

def _real_commit(root: Path, sha: Any, label: str, reasons: list[str], nullable: bool=False) -> str|None:
    if sha is None and nullable:return None
    if not isinstance(sha,str) or not FULL_SHA.fullmatch(sha):
        reasons.append(f'{label} must be a full 40-hex Git commit SHA'); return None
    code,_=_git(root,'cat-file','-e',f'{sha}^{{commit}}')
    if code!=0: reasons.append(f'{label} does not resolve to a Git commit: {sha}'); return None
    code,out=_git(root,'rev-parse',sha)
    if code!=0 or out.splitlines()[0].strip()!=sha:
        reasons.append(f'{label} rev-parse verification failed: {sha}'); return None
    return sha

def _test_static(row: dict[str,Any], candidate: str|None, reasons: list[str]) -> None:
    ident=str(row.get('node') or row.get('command') or '').strip()
    cmd=str(row.get('command') or ident)
    if not ident: reasons.append('test record missing exact node/command identity')
    if '--collect-only' in cmd: reasons.append(f'collect-only cannot be PASS execution evidence: {ident or cmd}')
    if row.get('exit_code') != 0: reasons.append(f'test exit_code is not zero: {ident}')
    for key in ('failed','skipped','xfailed','xpassed'):
        if int(row.get(key,0) or 0)!=0: reasons.append(f'test has non-green {key}: {ident}')
    if int(row.get('passed',0) or 0)<1: reasons.append(f'test record has no executed PASS count: {ident}')
    if not row.get('requirement_ids'): reasons.append(f'test missing requirement_ids: {ident}')
    for key in ('environment','timestamp','evidence_path'):
        if not row.get(key): reasons.append(f'test missing {key}: {ident}')
    if candidate and row.get('candidate_sha')!=candidate: reasons.append(f'test candidate_sha mismatch: {ident}')

def _run_exact_pytest(root: Path, nodes: list[str], reasons: list[str]) -> None:
    nodes=list(dict.fromkeys(n for n in nodes if '::' in n and n.split('::',1)[0].endswith('.py')))
    if not nodes:return
    parent=root/'.tmp'/'validator-pytest'; parent.mkdir(parents=True,exist_ok=True)
    user=f"{os.environ.get('USERDOMAIN', '')}\\{getpass.getuser()}".lstrip('\\')
    subprocess.run(['icacls',str(parent),'/grant',f'{user}:(OI)(CI)F','/T'],cwd=root,capture_output=True,check=False)
    basetemp=Path(tempfile.mkdtemp(prefix='run-', dir=str(parent)))
    subprocess.run(['icacls',str(basetemp),'/grant',f'{user}:(OI)(CI)F','/T'],cwd=root,capture_output=True,check=False)
    env=dict(os.environ); env['PYTEST_ADDOPTS']='-p no:cacheprovider'
    cp=subprocess.run([sys.executable,'-m','pytest','-q',*nodes,'--basetemp',str(basetemp)],cwd=root,env=env,text=True,capture_output=True,encoding='utf-8',errors='replace',check=False)
    if cp.returncode!=0:
        output=cp.stdout+'\n'+cp.stderr
        cleanup_only = 'PytestWarning: (rm_rf)' in output and 'PermissionError' in output and 'FAILED' not in output
        if not cleanup_only:
            reasons.append('exact pytest evidence execution failed: '+(output[-2000:].strip() or f'exit={cp.returncode}'))

def validate(wave: str|int, root: Path|None=None, execute_tests: bool=True) -> dict[str,Any]:
    root=root or ROOT; profile=_load_profile(root); wid=_normalize_wave_id(wave,profile); reasons:list[str]=[]
    mp=_manifest_path(root,profile,wid)
    try: manifest=json.loads(mp.read_text(encoding='utf-8-sig'))
    except (OSError,json.JSONDecodeError) as exc:
        return {'can_close':False,'wave_id':wid,'manifest':mp.as_posix(),'failure_reasons':[f'missing/invalid evidence manifest: {exc}']}
    evidence=profile.get('evidence') or {}
    required_fields=evidence.get('required_manifest_fields') or []
    missing=[f for f in required_fields if f not in manifest]
    if missing: reasons.append('missing mandatory manifest fields: '+', '.join(missing))
    if manifest.get('spec_profile_id') != profile.get('project_id'): reasons.append('spec/profile identity mismatch')
    if str(manifest.get('wave_id') or '').upper()!=wid: reasons.append(f'wave identity mismatch: {manifest.get("wave_id")} != {wid}')
    accepted=set(evidence.get('accepted_statuses') or ['ACCEPTANCE_GREEN','CLOSED'])
    if manifest.get('status') not in accepted: reasons.append(f'non-closeable manifest status: {manifest.get("status")}')
    candidate=_real_commit(root,manifest.get('candidate_sha'),'candidate_sha',reasons)
    closure=_real_commit(root,manifest.get('closure_sha'),'closure_sha',reasons,nullable=True)
    try: required=_required_ids(wid,root)
    except OSError as exc:return {'can_close':False,'wave_id':wid,'failure_reasons':[str(exc)]}
    rows=manifest.get('requirements');
    if not isinstance(rows,list): reasons.append('requirements must be a list'); rows=[]
    ids=[str(r.get('requirement_id') or '') for r in rows if isinstance(r,dict)]
    if len(ids)!=len(set(ids)): reasons.append('duplicate requirement IDs in manifest')
    missing_ids=sorted(required-set(ids))
    if missing_ids: reasons.append('missing owned requirements: '+', '.join(missing_ids))
    foreign=sorted({x for x in ids if x.startswith('HPC-') and x not in required})
    if foreign: reasons.append('requirement namespace/spec mismatch: '+', '.join(foreign))
    exact_nodes=[]
    for r in rows:
        if not isinstance(r,dict): reasons.append('requirement row is not an object'); continue
        rid=str(r.get('requirement_id') or '')
        if r.get('disposition') not in DISPOSITIONS: reasons.append(f'invalid disposition: {rid}')
        if r.get('mandatory') and r.get('disposition')=='FAIL_BLOCKED': reasons.append(f'mandatory requirement blocked: {rid}')
        if r.get('disposition')=='PASS':
            if not r.get('implementation_owners'): reasons.append(f'PASS missing implementation owner: {rid}')
            if not r.get('test_nodes'): reasons.append(f'PASS missing exact executed test nodes: {rid}')
            if candidate and r.get('candidate_sha')!=candidate: reasons.append(f'requirement candidate_sha mismatch: {rid}')
            exact_nodes += [str(x) for x in (r.get('test_nodes') or [])]
            if any(BAD_MARKER.search(str(x)) for x in (r.get('evidence_refs') or [])): reasons.append(f'contradictory PASS marker: {rid}')
        if r.get('disposition')=='ALLOWED_DEFERRED' and not r.get('deferred_allowed'): reasons.append(f'illegal deferred disposition: {rid}')
    tests=manifest.get('tests') if isinstance(manifest.get('tests'),list) else []
    for t in tests:
        if isinstance(t,dict): _test_static(t,candidate,reasons); exact_nodes.append(str(t.get('node') or ''))
        else: reasons.append('test row is not an object')
    if execute_tests and not reasons:
        _run_exact_pytest(root,exact_nodes,reasons)
    for action in manifest.get('gui_actions',[]) if isinstance(manifest.get('gui_actions'),list) else []:
        if isinstance(action,dict) and action.get('status')=='FULL':
            for key in ('source_binding','runtime_test_node','observed_readback','candidate_sha'):
                if not action.get(key): reasons.append(f'GUI FULL missing {key}')
            if candidate and action.get('candidate_sha')!=candidate: reasons.append('GUI FULL candidate mismatch')
    for resource in manifest.get('resources',[]) if isinstance(manifest.get('resources'),list) else []:
        if not isinstance(resource,dict): continue
        for key in ('create_owner','start_owner','normal_stop_owner','failure_cleanup_owner','app_shutdown_owner'):
            if not resource.get(key) or str(resource.get(key)).strip().lower()=='implicit': reasons.append(f'resource lifecycle missing/implicit {key}')
    deps=manifest.get('dependency_validation')
    if not isinstance(deps,dict): reasons.append('dependency_validation must be an object')
    else:
        for dep in deps.get('dependencies',[]) or []:
            if not isinstance(dep,dict) or dep.get('can_close') is not True or not dep.get('validator_evidence') or not dep.get('candidate_sha'):
                reasons.append('stale/unbound dependency validation')
    blockers=manifest.get('blockers')
    if isinstance(blockers,list) and blockers: reasons.append(f'unresolved blockers: {len(blockers)}')
    scan=manifest.get('contradiction_scan')
    if isinstance(scan,dict) and scan.get('unresolved'): reasons.append('contradiction scan has unresolved findings')
    for art in manifest.get('artifacts',[]) if isinstance(manifest.get('artifacts'),list) else []:
        if isinstance(art,dict) and art.get('path') and not (root/str(art['path'])).exists(): reasons.append(f'missing artifact: {art["path"]}')
    if candidate and closure:
        cp=subprocess.run(['git','-C',str(root),'diff','--name-only',f'{candidate}..{closure}'],text=True,capture_output=True,encoding='utf-8',errors='replace',check=False)
        if cp.returncode!=0: reasons.append('candidate→closure git diff failed: '+(cp.stderr.strip() or f'exit={cp.returncode}'))
        else:
            allowed=[str(x).replace('\\','/') for x in evidence.get('allowed_closeout_only_paths',[])]
            bad=[p.strip().replace('\\','/') for p in cp.stdout.splitlines() if p.strip() and not any(p.strip().replace('\\','/').startswith(a) for a in allowed)]
            if bad: reasons.append('behavior-changing closure diff: '+', '.join(bad[:20]))
    return {'can_close':not reasons,'wave_id':wid,'candidate_sha':manifest.get('candidate_sha'),'closure_sha':manifest.get('closure_sha'),'required_count':len(required),'manifest_requirement_count':len(rows),'test_count':len(tests),'failure_reasons':sorted(set(reasons))}

def _self_test() -> dict[str,Any]:
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/'.opencode/protocol').mkdir(parents=True); (root/'waves/pending').mkdir(parents=True); (root/'artifacts/wave_W01').mkdir(parents=True); (root/'tests').mkdir()
        profile={'project_id':'HPC','wave':{'file_regex':r'^W(?P<number>\d{2})\.md$','id_format':'W{number:02d}'},'paths':{'pending':'waves/pending','done':'waves/done','blocked':'waves/blocked','postponed':'waves/postponed'},'evidence':{'manifest_template':'artifacts/wave_{wave_id}/WAVE_{wave_id}_EVIDENCE_MANIFEST.json','shared_requirement_ids':[],'accepted_statuses':['ACCEPTANCE_GREEN'],'required_manifest_fields':['spec_profile_id','protocol_revision','wave_id','wave_spec_revision','status','candidate_sha','closure_sha','dependency_validation','requirements','tests','gui_actions','resources','artifacts','review_passes','contradiction_scan','blockers','deferred_items','validator_result'],'allowed_closeout_only_paths':['artifacts/']}}
        (root/'.opencode/protocol/WAVE_PROJECT_PROFILE.json').write_text(json.dumps(profile))
        (root/'waves/pending/W01.md').write_text('---\nwave_id: "W01"\nowned_requirements:\n  - "HPC-W01-X-001"\n---\n')
        (root/'tests/test_ok.py').write_text('def test_ok():\n    assert True\n')
        subprocess.run(['git','init'],cwd=root,capture_output=True); subprocess.run(['git','config','user.email','t@example.invalid'],cwd=root); subprocess.run(['git','config','user.name','T'],cwd=root); subprocess.run(['git','add','.'],cwd=root); subprocess.run(['git','commit','-m','base'],cwd=root,capture_output=True)
        sha=subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,capture_output=True).stdout.strip()
        base={'spec_profile_id':'HPC','protocol_revision':1,'wave_id':'W01','wave_spec_revision':1,'status':'ACCEPTANCE_GREEN','candidate_sha':sha,'closure_sha':sha,'dependency_validation':{'dependencies':[]},'requirements':[{'requirement_id':'HPC-W01-X-001','mandatory':True,'disposition':'PASS','implementation_owners':['x:y'],'test_nodes':['tests/test_ok.py::test_ok'],'evidence_refs':['ok'],'candidate_sha':sha}],'tests':[{'node':'tests/test_ok.py::test_ok','command':'pytest tests/test_ok.py::test_ok','requirement_ids':['HPC-W01-X-001'],'exit_code':0,'passed':1,'failed':0,'skipped':0,'xfailed':0,'xpassed':0,'environment':'selftest','timestamp':'2026-09-22T00:00:00Z','evidence_path':'self','candidate_sha':sha}],'gui_actions':[],'resources':[],'artifacts':[],'review_passes':{},'contradiction_scan':{'unresolved':[]},'blockers':[],'deferred_items':[],'validator_result':{}}
        mp=root/'artifacts/wave_W01/WAVE_W01_EVIDENCE_MANIFEST.json'
        mp.write_text(json.dumps(base)); r=validate('W01',root,execute_tests=True); checks.append(('valid_executes',r['can_close']))
        bad=dict(base); bad['status']='REPAIR_REQUIRED'; mp.write_text(json.dumps(bad)); r=validate('W01',root,execute_tests=False); checks.append(('status_rejected',not r['can_close'] and any('status' in x for x in r['failure_reasons'])))
        bad=json.loads(json.dumps(base)); bad['candidate_sha']='0'*40; mp.write_text(json.dumps(bad)); r=validate('W01',root,execute_tests=False); checks.append(('sha_rejected',not r['can_close'] and any('Git commit' in x for x in r['failure_reasons'])))
        bad=json.loads(json.dumps(base)); bad['requirements'][0]['requirement_id']='HPC-W02-X-001'; mp.write_text(json.dumps(bad)); r=validate('W01',root,execute_tests=False); checks.append(('namespace_rejected',not r['can_close'] and any('mismatch' in x for x in r['failure_reasons'])))
        bad=json.loads(json.dumps(base)); bad['tests'][0]['command']='pytest --collect-only tests/test_ok.py::test_ok'; mp.write_text(json.dumps(bad)); r=validate('W01',root,execute_tests=False); checks.append(('collect_only_rejected',not r['can_close'] and any('collect-only' in x for x in r['failure_reasons'])))
    return {'self_test':'pass' if all(ok for _,ok in checks) else 'fail','passed':sum(ok for _,ok in checks),'total':len(checks),'checks':[{'name':n,'pass':ok} for n,ok in checks]}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--wave'); ap.add_argument('--self-test',action='store_true'); ap.add_argument('--no-execute-tests',action='store_true'); a=ap.parse_args()
    if a.self_test:
        data=_self_test(); print(json.dumps(data,indent=2)); return 0 if data['self_test']=='pass' else 1
    if not a.wave: ap.error('--wave is required')
    data=validate(a.wave,execute_tests=not a.no_execute_tests); print(json.dumps(data,indent=2)); return 0 if data['can_close'] else 1
if __name__=='__main__': raise SystemExit(main())
