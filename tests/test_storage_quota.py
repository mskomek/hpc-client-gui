import pytest

from hpc_gui.services.storage_quota import QuotaResult, StorageArea


def test_missing_limits_stay_unknown_not_zero():
    result = QuotaResult(
        area_id="home", quota_pool_id="pool", scope="user", source_status="unknown"
    )
    assert result.used_bytes is None
    assert result.hard_limit_bytes is None


def test_shared_pool_is_preserved():
    area = StorageArea(
        id="scratch", label="Scratch", kind="scratch", path_template="/scratch/{user}",
        quota_scope="user", quota_pool_id="shared", provider_id="reviewed.provider",
        provider_options={},
    )
    assert area.quota_pool_id == "shared"


def test_negative_and_bool_quota_values_rejected():
    with pytest.raises(ValueError):
        QuotaResult("home", "pool", "user", used_bytes=-1)
    with pytest.raises(ValueError):
        QuotaResult("home", "pool", "user", used_bytes=True)
