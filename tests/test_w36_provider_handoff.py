"""Provider registration chain handoff contract."""

from __future__ import annotations

import pytest
from hpc_gui.plugins import providers as prov

@pytest.mark.unit
def test_handoff_provider_chain_unchanged():
    """PM-078: provider registration still uses the W02 capability contract."""
    assert prov.describe_registration_chain() == (
        "plugin",
        "provider registration",
        "capability declaration",
        "generic service",
        "wx UI",
    )
    assert prov.PROVIDER_REQUIREMENT == "HPC-W08-PROV-001"
