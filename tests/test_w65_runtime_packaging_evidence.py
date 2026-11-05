"""W65 UNIT F tests: live-run descriptors, package lifecycle, release verdict (RUNTIME-018, PACK-020, EVID-021, CLOSE-022)."""
from hpc_gui.openfoam_v2312 import runtime
from hpc_gui.openfoam_v2312 import packaging
from hpc_gui.openfoam_v2312 import evidence
from hpc_gui.openfoam_v2312 import ability_matrix
DIGEST = 'b' * 64
def good_spec():
    return runtime.LiveRunSpec(case_path='cases/cavity', solver='simpleFoam', argv=(' -parallel',), ranks=2)
def good_result():
    return runtime.LiveRunResult(case_path='cases/cavity', solver='simpleFoam', executed=True, exit_code=0, stdout_tail='End', stderr_tail='', binary_hash=DIGEST)
def test_spec_valid_passes():
    assert runtime.validate_spec(good_spec()) == ()
def test_spec_unknown_solver_rejected():
    bad = runtime.LiveRunSpec(case_path='cases/cavity', solver='noSuchFoam')
    assert runtime.validate_spec(bad)
def test_spec_empty_case_rejected():
    assert runtime.validate_spec(runtime.LiveRunSpec(solver='simpleFoam'))
def test_spec_zero_ranks_rejected():
    bad = runtime.LiveRunSpec(case_path='cases/cavity', solver='simpleFoam', ranks=0)
    assert runtime.validate_spec(bad)
def test_spec_newline_argv_rejected():
    bad = runtime.LiveRunSpec(case_path='cases/cavity', solver='simpleFoam', argv=('ok', 'bad' + chr(10) + 'x'))
    assert runtime.validate_spec(bad)
def test_spec_round_trip():
    assert runtime.LiveRunSpec.from_dict(good_spec().to_dict()) == good_spec()
def test_result_not_executed_is_blocked_env():
    res = runtime.LiveRunResult(case_path='cases/cavity', solver='simpleFoam')
    assert runtime.summarize_result(res) == runtime.STATUS_BLOCKED_ENV
    assert not runtime.is_proven(res)
def test_result_executed_without_hash_unproven():
    res = runtime.LiveRunResult(case_path='cases/cavity', solver='simpleFoam', executed=True, exit_code=0)
    assert runtime.validate_result(res)
    assert runtime.summarize_result(res) == runtime.STATUS_UNPROVEN
    assert not runtime.is_proven(res)
def test_result_executed_ok_proven():
    res = good_result()
    assert runtime.validate_result(res) == ()
    assert runtime.summarize_result(res) == runtime.STATUS_EXECUTED_OK
    assert runtime.is_proven(res)
def test_result_failed_not_proven():
    res = runtime.LiveRunResult(case_path='cases/cavity', solver='simpleFoam', executed=True, exit_code=3, binary_hash=DIGEST)
    assert runtime.summarize_result(res) == runtime.STATUS_EXECUTED_FAIL
    assert not runtime.is_proven(res)
def test_result_bad_hash_rejected():
    res = runtime.LiveRunResult(case_path='cases/cavity', solver='simpleFoam', executed=True, exit_code=0, binary_hash='zz')
    assert runtime.validate_result(res)
def test_result_round_trip():
    assert runtime.LiveRunResult.from_dict(good_result().to_dict()) == good_result()
def test_package_valid_passes():
    pkg = packaging.PackageIdentity(name='openfoam-case-studio', version='0.3.0', sha256=DIGEST, channel='test')
    assert packaging.validate_identity(pkg) == ()
def test_package_bad_sha_rejected():
    pkg = packaging.PackageIdentity(name='n', version='v', sha256='zz')
    assert packaging.validate_identity(pkg)
def test_package_unknown_channel_rejected():
    pkg = packaging.PackageIdentity(name='n', version='v', sha256=DIGEST, channel='nightly')
    assert packaging.validate_identity(pkg)
def test_package_round_trip():
    pkg = packaging.PackageIdentity(name='n', version='v', sha256=DIGEST)
    assert packaging.PackageIdentity.from_dict(pkg.to_dict()) == pkg
def test_lifecycle_install_twice_rejected():
    assert packaging.validate_transition(('installed',), 'installed')
def test_lifecycle_upgrade_before_install_rejected():
    assert packaging.validate_transition((), 'upgraded')
def test_lifecycle_rollback_before_upgrade_rejected():
    assert packaging.validate_transition(('installed',), 'rolled_back')
def test_lifecycle_uninstall_before_install_rejected():
    assert packaging.validate_transition((), 'uninstalled')
def test_lifecycle_dirty_source_refuses():
    assert packaging.validate_transition((), 'installed', dirty_source=True)
def test_lifecycle_unknown_action_rejected():
    assert packaging.validate_transition(('installed',), 'explode')
def test_lifecycle_full_sequence_complete():
    hist = ('installed', 'upgraded', 'rolled_back', 'uninstalled')
    assert packaging.validate_transition((), 'installed') == ()
    assert packaging.validate_transition(('installed',), 'upgraded') == ()
    assert packaging.validate_transition(('installed', 'upgraded'), 'rolled_back') == ()
    assert packaging.validate_transition(('installed',), 'uninstalled') == ()
    assert packaging.summarize_lifecycle(hist) == packaging.STATUS_COMPLETE
def test_lifecycle_partial_short_sequence():
    assert packaging.summarize_lifecycle(('installed', 'upgraded')) == packaging.STATUS_PARTIAL
def test_verdict_critical_is_no_go():
    assert evidence.compute_verdict(True, True, True, True, True) == evidence.VERDICT_NO_GO
def test_verdict_missing_p1_is_partial():
    assert evidence.compute_verdict(True, False, False, False, False) == evidence.VERDICT_PARTIAL
def test_verdict_missing_vm_is_blocked_env():
    assert evidence.compute_verdict(True, True, False, True, False) == evidence.VERDICT_BLOCKED_ENV
def test_verdict_missing_runtime_is_blocked_env():
    assert evidence.compute_verdict(True, True, True, False, False) == evidence.VERDICT_BLOCKED_ENV
def test_verdict_all_green_is_go():
    assert evidence.compute_verdict(True, True, True, True, False) == evidence.VERDICT_GO
def test_report_missing_keys_rejected():
    rep = {'wave': 'W65', 'source_sha': 'abc', 'package_sha': '', 'verdict': 'GO'}
    assert evidence.validate_report(rep, True, True, True, True, False)
def test_report_inconsistent_verdict_rejected():
    rep = {'wave': 'W65', 'source_sha': 'abc', 'package_sha': DIGEST, 'verdict': 'GO'}
    assert evidence.validate_report(rep, True, True, False, True, False)
def test_report_consistent_passes():
    rep = {'wave': 'W65', 'source_sha': 'abc', 'package_sha': DIGEST, 'verdict': 'BLOCKED_ENV'}
    assert evidence.validate_report(rep, True, True, False, True, False) == ()
def test_matrix_no_done_and_close_blocked():
    rows = ability_matrix.build_matrix()
    ability_matrix.validate_matrix(rows)
    by_id = {}
    for row in rows:
        by_id[row.feature_id] = row
        assert row.status != ability_matrix.STATUS_DONE
    assert by_id['HPC-W65-VM-017'].status == ability_matrix.STATUS_BLOCKED
    assert by_id['HPC-W65-RUNTIME-018'].status == ability_matrix.STATUS_BLOCKED
    assert by_id['HPC-W65-CLOSE-022'].status == ability_matrix.STATUS_BLOCKED
    assert by_id['HPC-W65-PACK-020'].status == ability_matrix.STATUS_PARTIAL