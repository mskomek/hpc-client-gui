from __future__ import annotations

from hpc_gui.services.cluster_self_test import NOT_CONFIGURED, NOT_TESTED, PASS, WARNING
from hpc_gui.services.provider_capabilities import DECLARED, NOT_DECLARED, build_provider_capability_view


def _items(view):
    return {item.id: item for item in view.capabilities}


def test_rich_provider_keeps_declared_and_observed_separate():
    view = build_provider_capability_view(
        {
            "name": "Example",
            "scheduler": "slurm",
            "access": {"auth_methods": ["key"]},
            "storage": [{"id": "home"}],
            "quota_sources": [{"id": "quota"}],
            "requirements": {"project": {}, "account": {}},
        },
        {"auth": PASS, "scheduler": WARNING},
        project="p",
    )
    items = _items(view)
    assert items["auth"].declared == DECLARED and items["auth"].observed == PASS
    assert items["scheduler"].observed == WARNING
    assert items["quota"].declared == DECLARED
    assert items["account"].observed == NOT_CONFIGURED


def test_generic_profile_and_declared_or_observed_only_capabilities():
    generic = _items(build_provider_capability_view())
    assert all(item.declared == NOT_DECLARED for item in generic.values())
    assert generic["scheduler"].observed == NOT_CONFIGURED

    view = _items(build_provider_capability_view({"scheduler": "slurm"}, {"storage": PASS}))
    assert view["scheduler"].declared == DECLARED
    assert view["storage"].declared == NOT_DECLARED and view["storage"].observed == PASS
    assert view["quota"].observed == NOT_TESTED
