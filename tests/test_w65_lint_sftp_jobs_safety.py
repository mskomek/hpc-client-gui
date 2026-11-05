"""W65 UNIT E tests: linter packs, SFTP descriptors, job drafts, safe save (HPC-W65-LINT-013, SFTP-014, JOBS-015, SAFE-016)."""
from hpc_gui.openfoam_v2312 import linter
from hpc_gui.openfoam_v2312 import sftp
from hpc_gui.openfoam_v2312 import jobs
from hpc_gui.openfoam_v2312 import safety
from hpc_gui.openfoam_v2312 import ability_matrix
DIGEST = 'a' * 64
def test_lint_registry_has_ten_documented_rules():
    assert len(linter.list_rules()) == 10
    assert len(set(linter.list_rules())) == 10
def test_lint_valid_rule_passes():
    rule = linter.LintRule(rule_id='OF-MESH-001', family=linter.FAMILY_MESH, severity=linter.SEVERITY_WARNING, level=linter.LEVEL_STATIC, title='mesh check')
    assert linter.validate_rule(rule) == ()
def test_lint_unknown_family_rejected():
    rule = linter.LintRule(rule_id='OF-X-001', family='OF-X', title='x')
    assert linter.validate_rule(rule)
def test_lint_prefix_mismatch_rejected():
    rule = linter.LintRule(rule_id='OF-MESH-001', family=linter.FAMILY_BC, title='x')
    assert linter.validate_rule(rule)
def test_lint_valid_finding_passes():
    finding = linter.LintFinding(rule_id='OF-SEC-001', severity=linter.SEVERITY_ERROR, certainty=linter.CERTAINTY_HIGH, path='system/controlDict', line=3, column=0, message='blocked directive')
    assert linter.validate_finding(finding) == ()
def test_lint_unknown_rule_finding_rejected():
    finding = linter.LintFinding(rule_id='OF-X-999', path='p', line=1, message='m')
    assert linter.validate_finding(finding)
def test_lint_zero_line_rejected():
    finding = linter.LintFinding(rule_id='OF-DICT-001', path='p', line=0, message='m')
    assert linter.validate_finding(finding)
def test_lint_rule_round_trip():
    rule = linter.LintRule(rule_id='OF-PAR-001', family=linter.FAMILY_PAR, severity=linter.SEVERITY_INFO, level=linter.LEVEL_STATIC, title='parallel')
    assert linter.LintRule.from_dict(rule.to_dict()) == rule
def test_sftp_valid_file_passes():
    item = sftp.RemoteFile(path='case/0/U', digest=DIGEST, size=128)
    assert sftp.validate_remote_file(item) == ()
def test_sftp_missing_digest_rejected():
    item = sftp.RemoteFile(path='case/0/U', digest='', size=128)
    assert sftp.validate_remote_file(item)
def test_sftp_bad_digest_rejected():
    item = sftp.RemoteFile(path='case/0/U', digest='zz', size=128)
    assert sftp.validate_remote_file(item)
def test_sftp_escape_rejected():
    item = sftp.RemoteFile(path='case/../evil', digest=DIGEST, size=1)
    assert sftp.validate_remote_file(item)
def test_sftp_backslash_rejected():
    item = sftp.RemoteFile(path='case' + chr(92) + 'U', digest=DIGEST, size=1)
    assert sftp.validate_remote_file(item)
def test_sftp_failure_without_detail_rejected():
    item = sftp.StageResult(path='case/0/U', phase=sftp.PHASE_COMMIT, ok=False, detail='')
    assert sftp.validate_stage(item)
def test_sftp_summarize_partial_and_complete():
    good = sftp.StageResult(path='a', phase=sftp.PHASE_STAGE, ok=True, detail='ok')
    bad = sftp.StageResult(path='b', phase=sftp.PHASE_COMMIT, ok=False, detail='rename failed')
    assert sftp.summarize((good, good)) == sftp.STATUS_COMPLETE
    assert sftp.summarize((good, bad)) == sftp.STATUS_PARTIAL
    assert sftp.summarize(()) == sftp.STATUS_EMPTY
def test_sftp_round_trip():
    item = sftp.RemoteFile(path='case/constant/polyMesh', digest=DIGEST, size=10)
    assert sftp.RemoteFile.from_dict(item.to_dict()) == item
def test_jobs_valid_draft_passes():
    draft = jobs.JobDraft(case_path='cases/cavity', solver='simpleFoam', module='apps/openfoam/v2312-2025', ranks=4, walltime_min=60)
    assert jobs.validate_draft(draft) == ()
def test_jobs_unknown_solver_rejected():
    draft = jobs.JobDraft(case_path='cases/cavity', solver='noSuchFoam', module='m', ranks=1, walltime_min=10)
    assert jobs.validate_draft(draft)
def test_jobs_zero_ranks_rejected():
    draft = jobs.JobDraft(case_path='cases/cavity', solver='simpleFoam', module='m', ranks=0, walltime_min=10)
    assert jobs.validate_draft(draft)
def test_jobs_auto_submit_rejected():
    draft = jobs.JobDraft(case_path='cases/cavity', solver='simpleFoam', module='m', ranks=1, walltime_min=10, submit=True)
    assert jobs.validate_draft(draft)
def test_jobs_empty_module_rejected():
    draft = jobs.JobDraft(case_path='cases/cavity', solver='simpleFoam', module='', ranks=1, walltime_min=10)
    assert jobs.validate_draft(draft)
def test_jobs_round_trip():
    draft = jobs.JobDraft(case_path='cases/cavity', solver='icoFoam', module='m', ranks=2, walltime_min=30)
    assert jobs.JobDraft.from_dict(draft.to_dict()) == draft
def test_save_valid_passes():
    policy = safety.SavePolicy()
    assert safety.validate_save('cases/cavity/system/controlDict', policy) == ()
def test_save_overwrite_refused():
    policy = safety.SavePolicy()
    assert safety.validate_save('cases/cavity/0/U', policy, exists=True)
def test_save_symlink_needs_opt_in():
    policy = safety.SavePolicy()
    assert safety.validate_save('cases/cavity/link', policy, is_symlink=True)
    opt_in = safety.SavePolicy(allow_symlink=True)
    assert safety.validate_save('cases/cavity/link', opt_in, is_symlink=True) == ()
def test_save_traversal_rejected():
    policy = safety.SavePolicy()
    assert safety.validate_save('cases/../evil', policy)
def test_directive_codestream_refused():
    assert safety.validate_directive('#codeStream code here')
    assert safety.validate_directive('plain dictionary text') == ()
def test_argv_injection_rejected():
    assert safety.validate_argv(['simpleFoam', '-case;c'])
    assert safety.validate_argv(['simpleFoam', '-case', 'cavity']) == ()
def test_untrusted_scripts_flagged():
    assert safety.is_untrusted_script('Allrun')
    assert safety.is_untrusted_script('Allclean')
    assert not safety.is_untrusted_script('controlDict')
def test_matrix_marks_unit_e_partial():
    rows = ability_matrix.build_matrix()
    ability_matrix.validate_matrix(rows)
    by_id = {row.feature_id: row for row in rows}
    for feature_id in ('HPC-W65-LINT-013', 'HPC-W65-SFTP-014', 'HPC-W65-JOBS-015', 'HPC-W65-SAFE-016'):
        assert by_id[feature_id].status == ability_matrix.STATUS_PARTIAL
        assert by_id[feature_id].unit_evidence == 'tests/test_w65_lint_sftp_jobs_safety.py'
    for feature_id in ('HPC-W65-VM-017', 'HPC-W65-RUNTIME-018', 'HPC-W65-CLOSE-022'):
        assert by_id[feature_id].status == ability_matrix.STATUS_BLOCKED
    assert ability_matrix.STATUS_DONE not in {row.status for row in rows}
