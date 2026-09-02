from hpc_gui.wx_macos_audit import run_audit


def test_macos_audit_core_checks():
    results = {result.name: result for result in run_audit()}
    assert all(result.passed for result in results.values())
