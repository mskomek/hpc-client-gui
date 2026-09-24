from __future__ import annotations
import json, os, subprocess, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / '.opencode' / 'scripts'))
from wave_state_engine import *

HPC_PROFILE={
 'schema_version':1,'project_id':'HPC','wave':{'file_regex':r'^W(?P<number>\d{2})\.md$','id_format':'W{number:02d}','min':1,'max':61},
 'paths':{'pending':'waves/pending','done':'waves/done','blocked':'waves/blocked','postponed':'waves/postponed','active_wave_tracker':None,'waves_index':None},
 'capabilities':{'active_wave_tracker':False,'waves_index':False,'canonical_source_closeout':False},
 'scheduler':{'authority':'wave_directories','auto_resume':True,'closed_wave_policy':'immutable'},
 'aggregate':{'validator_script':None},'temp_root':'.tmp','legacy_run_roots':['.agent-runs'],'global_state_owner':'controller',
 'evidence':{'identity':'content','allowed_closeout_only_paths':['docs/wave-reports/','artifacts/','.tmp/','waves/']}}
IMPI_PROFILE={
 'schema_version':1,'project_id':'IMPI','wave':{'file_regex':r'^WAVE_(?P<number>\d+)_.*\.md$','id_format':'{number}','min':440,'max':498},
 'paths':{'pending':'waves/pending','done':'waves/done','blocked':'waves/blocked','postponed':'waves/postponed','active_wave_tracker':'ACTIVE_WAVE.md','waves_index':'WAVES.md'},
 'capabilities':{'active_wave_tracker':True,'waves_index':True,'canonical_source_closeout':True},
 'scheduler':{'authority':'wave_directories','auto_resume':True,'closed_wave_policy':'immutable'},
 'aggregate':{'validator_script':'tools/validate_wave_aggregate.py'},'temp_root':'.tmp','legacy_run_roots':['.agent-runs'],'global_state_owner':'controller',
 'evidence':{'identity':'content','allowed_closeout_only_paths':['docs/wave-reports/','artifacts/','.tmp/','waves/','ACTIVE_WAVE.md','WAVES.md']}}

def sh(repo,*args):
    subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)

def init_repo(profile):
    td=tempfile.TemporaryDirectory(); root=Path(td.name)
    for d in ['waves/pending','waves/done','waves/blocked','waves/postponed','.opencode/protocol']:(root/d).mkdir(parents=True,exist_ok=True)
    (root/'.opencode/protocol/WAVE_PROJECT_PROFILE.json').write_text(json.dumps(profile),encoding='utf-8')
    sh(root,'init'); sh(root,'config','user.email','fixture@example.invalid'); sh(root,'config','user.name','Fixture')
    (root/'README.md').write_text('fixture\n'); sh(root,'add','.'); sh(root,'commit','-m','init')
    return td,root

def wave(root,state,name,meta=''):
    p=root/'waves'/state/name
    body=(f'---\n{meta}\n---\n' if meta else '')+f'# {name}\n'
    p.write_text(body,encoding='utf-8'); return p

class EngineTests(unittest.TestCase):
    def test_inv001_tmp_layout(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup)
        p=load_profile(r); root=ensure_temp_layout(r,p)
        self.assertEqual(root,r/'.tmp')
        for n in TEMP_SUBDIRS:self.assertTrue((root/n).is_dir())
        self.assertEqual(program_run_root(r,p,'wave-a-end-l-p'),r/'.tmp/agent-runs/wave-a-end-l-p')

    def test_inv004_closed_excluded_and_w10_next(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup)
        p=load_profile(r)
        wave(r,'done','W07.md'); wave(r,'done','W08.md'); wave(r,'pending','W09.md'); wave(r,'pending','W10.md')
        self.assertEqual(current_target(r,p)[0],'W09')
        (r/'waves/pending/W09.md').replace(r/'waves/done/W09.md')
        self.assertEqual(current_target(r,p)[0],'W10')
        # stale duplicate pending cannot reactivate done
        wave(r,'pending','W09.md')
        self.assertEqual(current_target(r,p)[0],'W10')
        self.assertEqual(wave_location(r,p,'W09')[1],'done')

    def test_inv018_hpc_missing_optional_trackers(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup)
        p=load_profile(r); wave(r,'pending','W09.md')
        self.assertFalse((r/'ACTIVE_WAVE.md').exists()); self.assertFalse((r/'WAVES.md').exists())
        self.assertEqual(current_target(r,p)[0],'W09')
        self.assertFalse(aggregate_validation_required(p,wave_metadata(r/'waves/pending/W09.md',p),'close'))

    def test_inv005_008_009_467_468_aggregate_policy(self):
        td,r=init_repo(IMPI_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        w467=wave(r,'pending','WAVE_467_RUNTIME_LIBRARY_PORTABILITY_SCALE.md',
            "wave_id: '467'\nwave_kind: execution\ncanonical_source: W432\naggregate_close_owner: false\nowned_requirements: [\"W432-RUN-*\",\"W432-LIB-*\",\"W432-RES-*\",\"W432-SCALE-*\"]")
        w468=wave(r,'pending','WAVE_468_GOLDEN_TESTS_EVIDENCE_REVIEWS_EXIT.md',
            "wave_id: '468'\nwave_kind: aggregate_exit\ncanonical_source: W432\naggregate_close_owner: true")
        self.assertFalse(aggregate_validation_required(p,wave_metadata(w467,p),'close'))
        self.assertTrue(aggregate_validation_required(p,wave_metadata(w468,p),'close'))

    def test_impi_scheduler_excludes_auxiliary_source_wave_but_lookup_keeps_it(self):
        td,r=init_repo(IMPI_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        owner=wave(r,'pending','WAVE_426_PRODUCT_CAPABILITY_AUDIT.md')
        frontier=wave(r,'pending','WAVE_467_RUNTIME_LIBRARY_PORTABILITY_SCALE.md')
        self.assertEqual(current_target(r,p),('467',frontier))
        self.assertEqual(wave_location(r,p,'426'),(owner,'pending'))
        self.assertEqual([wid for wid,_ in pending_targets(r,p)],['467'])

    def test_resume_auxiliary_426_reconciles_forward_to_execution_frontier_467(self):
        td,r=init_repo(IMPI_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        wave(r,'pending','WAVE_426_PRODUCT_CAPABILITY_AUDIT.md')
        wave(r,'pending','WAVE_467_RUNTIME_LIBRARY_PORTABILITY_SCALE.md')
        ident=repo_identity(r)
        saved={'project':'IMPI','repository_identity':ident['repo_root'],'branch':ident['branch'],
               'current_wave':'426','phase':'repair','terminal':False}
        c,t,ph=resume_classification(r,p,saved,'canonical')
        self.assertEqual((c,t,ph),('RECONCILE_FORWARD','467','reconcile'))

    def test_resumed_run_gets_fresh_os_temp_boot_directory(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        first=configure_temp_environment(r,p,'same-run')
        second=configure_temp_environment(r,p,'same-run')
        self.assertNotEqual(first,second)
        self.assertEqual(first.parent, r/'.tmp/os/same-run')
        self.assertEqual(second.parent, r/'.tmp/os/same-run')
        self.assertEqual(Path(os.environ['TEMP']),second)

    def test_inv002_003_resume_forward_over_stale_saved_state(self):
        td,r=init_repo(IMPI_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        wave(r,'done','WAVE_467_RUNTIME_LIBRARY_PORTABILITY_SCALE.md'); wave(r,'pending','WAVE_468_GOLDEN_TESTS_EVIDENCE_REVIEWS_EXIT.md')
        ident=repo_identity(r)
        saved={'project':'IMPI','repository_identity':ident['repo_root'],'branch':ident['branch'],'current_wave':'467','phase':'repair','terminal':False}
        c,t,ph=resume_classification(r,p,saved,'canonical')
        self.assertEqual((c,t,ph),('RECONCILE_FORWARD','468','reconcile'))

    def test_legacy_run_import_then_new_writes_canonical(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        wave(r,'pending','W09.md')
        legacy=r/'.agent-runs/wave-a-end-l-p/old'; legacy.mkdir(parents=True)
        ident=repo_identity(r)
        (legacy/'state.json').write_text(json.dumps({'project':'HPC','repository_identity':ident['repo_root'],'branch':ident['branch'],'current_wave':'W09','phase':'audit','terminal':False}))
        path,kind=discover_unfinished_run(r,p,'wave-a-end-l-p')
        self.assertEqual((path,kind),(legacy/'state.json','legacy'))
        c,t,ph=resume_classification(r,p,json.loads(path.read_text()),kind)
        self.assertEqual((c,t,ph),('IMPORT_LEGACY_RUN','W09','audit'))
        self.assertTrue(str(program_run_root(r,p,'wave-a-end-l-p')).endswith(str(Path('.tmp') / 'agent-runs' / 'wave-a-end-l-p')))

    def test_lock_live_and_stale_takeover(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        lock=ControllerLock.acquire(r,p,'wave-a-end-l-p','one'); self.addCleanup(lock.release)
        with self.assertRaises(RuntimeError):ControllerLock.acquire(r,p,'wave-a-end-l-p','two')
        lock.release()
        path=r/'.tmp/locks/wave-a-end-l-p.lock'; path.write_text(json.dumps({'run_id':'stale','pid':99999999,'process_start_time':'x','repository_identity':repo_identity(r)['repo_root'],'program':'wave-a-end-l-p'}))
        l2=ControllerLock.acquire(r,p,'wave-a-end-l-p','two'); l2.release()

    def test_inv015_no_progress_depends_on_content_identity(self):
        a=no_progress_key('467','audit','finding','treeA'); b=no_progress_key('467','audit','finding','treeB')
        self.assertNotEqual(a,b); self.assertEqual(a,no_progress_key('467','audit','finding','treeA'))

    def test_inv016_content_identity_ignores_closeout_only_paths(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        (r/'src').mkdir(); (r/'src/a.py').write_text('x=1\n'); sh(r,'add','.'); sh(r,'commit','-m','src')
        i1=repository_content_identity(r,p['evidence']['allowed_closeout_only_paths'])
        (r/'docs/wave-reports').mkdir(parents=True); (r/'docs/wave-reports/x.md').write_text('report\n')
        i2=repository_content_identity(r,p['evidence']['allowed_closeout_only_paths']); self.assertEqual(i1,i2)
        (r/'src/a.py').write_text('x=2\n'); i3=repository_content_identity(r,p['evidence']['allowed_closeout_only_paths']); self.assertNotEqual(i1,i3)

    def test_metadata_backward_compatibility(self):
        td,r=init_repo(HPC_PROFILE); self.addCleanup(td.cleanup); p=load_profile(r)
        w=wave(r,'pending','W09.md'); m=wave_metadata(w,p)
        self.assertEqual(m['wave_id'],'W09'); self.assertEqual(m['wave_kind'],'execution'); self.assertFalse(m['aggregate_close_owner'])

if __name__=='__main__':unittest.main()
