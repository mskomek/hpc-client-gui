"""Aggregate the shared GUI-FILE-003 stress measurements after all groups."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("wx")

from support import wx_file003_stress as legacy_stress
from support import wx_file003_stress_support as final_stress


@pytest.mark.reporting
@pytest.mark.semantic
def test_zz_measured_invariants(capsys):
    if os.environ.get("PYTEST_XDIST_WORKER"):
        pytest.skip("GUI-FILE-003 aggregate requires one serial wx process")
    if not legacy_stress.EXECUTED and not final_stress.EXECUTED:
        pytest.skip("run the complete GUI-FILE-003 stress module set in one process")

    executed = {**legacy_stress.EXECUTED, **final_stress.EXECUTED}
    lines = ["", "GUI-FILE-003 executed stress counts:"]
    for name, (count, required) in executed.items():
        lines.append(
            "  %s: %d/%d %s"
            % (name, count, required, "PASS" if count >= required else "FAIL")
        )
    lines.append("GUI-FILE-003 measured invariants:")
    for name in final_stress.ZERO_INVARIANTS:
        value = legacy_stress.METRICS[name] + final_stress.METRICS[name]
        lines.append("  %s: %d" % (name, value))
    for name in (
        "peak_local_mutation_concurrency",
        "peak_remote_mutation_concurrency",
        "lost_remote_mutations",
    ):
        value = max(legacy_stress.METRICS[name], final_stress.METRICS[name])
        lines.append("  %s: %d" % (name, value))
    with capsys.disabled():
        print("\n".join(lines))

    required_groups = (
        "right-click retarget",
        "local mutations",
        "remote mutations",
        "target switches",
        "navigate/completion races",
        "browser open/close",
        "blocked close-in-flight",
        "FILE transfer items",
        "unicode/space names",
    )
    missing = [name for name in required_groups if name not in executed]
    assert not missing, "stress groups did not run: %s" % missing
    for name in final_stress.ZERO_INVARIANTS:
        total = legacy_stress.METRICS[name] + final_stress.METRICS[name]
        assert total == 0, "%s = %d" % (name, total)
    assert max(legacy_stress.METRICS["peak_local_mutation_concurrency"],
               final_stress.METRICS["peak_local_mutation_concurrency"]) <= 1
    assert max(legacy_stress.METRICS["peak_remote_mutation_concurrency"],
               final_stress.METRICS["peak_remote_mutation_concurrency"]) <= 1
