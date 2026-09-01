from __future__ import annotations

from hpc_gui.services.cluster_self_test import ClusterSelfTestResult, SelfTestItem, SelfTestSection
from hpc_gui.ui.dialogs.cluster_self_test_dialog import format_self_test_result


def test_self_test_copy_format_contains_no_connection_identity():
    result = ClusterSelfTestResult(
        "PASS", (SelfTestSection("Connection", (SelfTestItem("ssh", "PASS", "authenticated"),)),)
    )
    copied = format_self_test_result(result)
    assert "cluster.example" not in copied
    assert "alice" not in copied
    assert "ssh: PASS" in copied
