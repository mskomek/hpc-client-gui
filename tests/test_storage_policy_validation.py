from hpc_gui.plugins.models import validate_storage_policy


def test_storage_policy_accepts_unknown_or_nonnegative_retention():
    assert validate_storage_policy({}) is None
    assert validate_storage_policy({"retention_days": None}) is None
    assert validate_storage_policy({"retention_days": 30, "documentation_url": "https://example.org"}) is None


def test_storage_policy_rejects_invalid_retention_and_source_url():
    assert validate_storage_policy({"retention_days": -1})
    assert validate_storage_policy({"retention_days": "30"})
    assert validate_storage_policy({"documentation_url": "http://example.org"})
