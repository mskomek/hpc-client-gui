from __future__ import annotations
import importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_dynamic_required_ids_follow_actual_execution_wave_spec():
    v=load(ROOT/'scripts/validate_wave_closeout.py','v1')
    for wid in ('W01','W15','W22','W61'):
        required=v._required_ids(wid)
        text=next(p for state in ('done','pending','blocked','postponed') for p in (ROOT/'waves'/state).glob(wid+'.md')).read_text(encoding='utf-8-sig')
        fm=v._simple_yaml(text); assert set(fm['owned_requirements']) <= required
    # W15 intentionally owns historical-planning IDs from W04; the validator must use the actual W15 spec, not infer W15-*.
    assert any(x.startswith('HPC-W04-') for x in v._required_ids('W15'))

def test_all_w01_w61_have_machine_frontmatter_and_exact_owned_rows():
    v=load(ROOT/'scripts/validate_wave_closeout.py','v2'); profile=v._load_profile(ROOT); files=v._canonical_wave_files(ROOT,profile)
    assert set(profile['scheduler']['scheduled_wave_ids']) <= set(files)
    for wid in profile['scheduler']['scheduled_wave_ids']:
        fm=v._simple_yaml(files[wid].read_text(encoding='utf-8-sig'))
        assert fm['wave_id']==wid; assert fm['canonical_source']==wid; assert fm['owned_requirements']; assert fm['aggregate_close_owner'] is False

def test_final_program_complete_has_profile_owned_fail_closed_sweep():
    c=(ROOT/'.opencode/scripts/run-wave-program.py').read_text(encoding='utf-8-sig'); p=json.loads((ROOT/'.opencode/protocol/WAVE_PROJECT_PROFILE.json').read_text(encoding='utf-8-sig'))
    assert 'def final_program_validation' in c; assert 'PROGRAM_FINAL_VALIDATION_BLOCKED' in c
    assert p['final_validation']['enabled'] is True; assert p['final_validation']['canonical_wave_ids']==p['scheduler']['scheduled_wave_ids']

def test_backend_parity_validator_passes():
    cp=subprocess.run([sys.executable,'.opencode/scripts/validate-agent-parity.py'],cwd=ROOT,text=True,capture_output=True)
    assert cp.returncode==0,cp.stdout+cp.stderr; assert 'AGENT_PARITY=PASS' in cp.stdout

def test_validator_self_test_rejects_namespace_sha_status_and_collect_only():
    cp=subprocess.run([sys.executable,'scripts/validate_wave_closeout.py','--self-test'],cwd=ROOT,text=True,capture_output=True)
    assert cp.returncode==0,cp.stdout+cp.stderr; data=json.loads(cp.stdout); assert data['self_test']=='pass'; assert data['passed']==data['total']
