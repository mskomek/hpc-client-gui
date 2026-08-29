from hpc_gui.config.storage import resolve_provider_overrides


def test_provider_override_missing_key_inherits():
    assert resolve_provider_overrides({"backend_id": "quota-v1", "enabled": True}, {"enabled": False}) == {
        "backend_id": "quota-v1",
        "enabled": False,
    }


def test_provider_override_blank_or_null_persists_clear():
    assert resolve_provider_overrides({"command_template": "quota {user}"}, {"command_template": ""}) == {
        "command_template": None,
    }
    assert resolve_provider_overrides({"command_template": "quota {user}"}, {"command_template": None}) == {
        "command_template": None,
    }


def test_provider_override_sets_values_without_truthiness_loss():
    assert resolve_provider_overrides({}, {"enabled": False, "timeout_seconds": 0}) == {
        "enabled": False,
        "timeout_seconds": 0,
    }
