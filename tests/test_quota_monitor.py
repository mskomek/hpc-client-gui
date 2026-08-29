from hpc_gui.services.quota_monitor import quota_gate


def test_quota_gate_never_works_without_command_or_when_disabled():
    assert quota_gate(None) == "not_configured"
    assert quota_gate({"command_template": ""}) == "not_configured"
    assert quota_gate({"enabled": False, "command_template": "quota", "backend_id": "x"}) == "disabled"


def test_quota_gate_requires_reviewed_backend_and_subject():
    source = {"enabled": True, "command_template": "quota {user}", "backend_id": "x"}
    assert quota_gate(source) == "incomplete/unsupported"
    assert quota_gate(source, backend_ids={"x"}, subject_available=False) == "incomplete/unsupported"


def test_quota_gate_requires_consent_and_connection():
    source = {"enabled": True, "consent": True, "command_template": "quota {user}", "backend_id": "x"}
    assert quota_gate(source, backend_ids={"x"}) == "ready_not_enabled"
    assert quota_gate(source, backend_ids={"x"}, connected=True) == "eligible"


def test_quota_gate_rejects_multiline_commands():
    source = {"enabled": True, "command_template": "quota\nrm", "backend_id": "x"}
    assert quota_gate(source, backend_ids={"x"}) == "invalid_configuration"
