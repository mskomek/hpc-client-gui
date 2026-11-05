'''Release verdict computation (W65 UNIT F, HPC-W65-EVID-021 and CLOSE-022).'''
from __future__ import annotations
VERDICT_GO = 'GO'
VERDICT_PARTIAL = 'PARTIAL'
VERDICT_BLOCKED_ENV = 'BLOCKED_ENV'
VERDICT_NO_GO = 'NO_GO'
VERDICTS = (VERDICT_GO, VERDICT_PARTIAL, VERDICT_BLOCKED_ENV, VERDICT_NO_GO)
REQUIRED_REPORT_KEYS = ('wave', 'source_sha', 'package_sha', 'verdict')
def compute_verdict(p0_done, p1_done, vm_ok, runtime_ok, critical_fail):
    if critical_fail:
        return VERDICT_NO_GO
    if not (p0_done and p1_done):
        return VERDICT_PARTIAL
    if not (vm_ok and runtime_ok):
        return VERDICT_BLOCKED_ENV
    return VERDICT_GO
def validate_report(report, p0_done, p1_done, vm_ok, runtime_ok, critical_fail):
    errors = []
    for key in REQUIRED_REPORT_KEYS:
        if not report.get(key):
            errors.append('report misses key: ' + key)
    verdict = report.get('verdict', '')
    if verdict not in VERDICTS:
        errors.append('unknown verdict: ' + str(verdict))
    elif verdict != compute_verdict(p0_done, p1_done, vm_ok, runtime_ok, critical_fail):
        errors.append('verdict inconsistent with inputs')
    return tuple(errors)