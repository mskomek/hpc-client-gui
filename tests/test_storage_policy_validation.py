from hpc_gui.plugins.models import validate_storage_area, validate_storage_policy


def test_storage_policy_accepts_unknown_or_nonnegative_retention():
    assert validate_storage_policy({}) is None
    assert validate_storage_policy({"retention_days": None}) is None
    assert validate_storage_policy({"retention_days": 30, "documentation_url": "https://example.org"}) is None


def test_storage_policy_rejects_invalid_retention_and_source_url():
    assert validate_storage_policy({"retention_days": -1})
    assert validate_storage_policy({"retention_days": "30"})
    assert validate_storage_policy({"documentation_url": "http://example.org"})


def test_storage_area_accepts_known_shape_and_rejects_command_syntax():
    area = {
        "id": "scratch",
        "label": "Scratch",
        "kind": "scratch",
        "access_context": "login-node",
        "path_template": "/scratch/{user}",
        "policy": {"backup": None, "retention_days": None},
    }
    assert validate_storage_area(area) is None
    assert validate_storage_area({**area, "path_template": "/scratch/{user}; touch /tmp/pwned"})
    assert validate_storage_area({**area, "access_context": "login"})
