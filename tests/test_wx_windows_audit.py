from hpc_gui.wx_windows_audit import run_audit


def test_windows_audit_core_checks():
    results = {result.name: result for result in run_audit()}
    assert results["geometry matrix"].passed
    assert results["file URL payload"].passed
    assert results["terminal interrupt"].passed
    assert results["wx import"].passed
