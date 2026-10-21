"""Aggregate the shared GUI-FILE-003 stress measurements after all groups."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("wx")

from support.wx_file003_stress import EXECUTED, METRICS, ZERO_INVARIANTS


@pytest.mark.reporting
@pytest.mark.semantic
def test_zz_measured_invariants(capsys):
    if os.environ.get("PYTEST_XDIST_WORKER"):
        pytest.skip("GUI-FILE-003 aggregate requires one serial wx process")
    if not EXECUTED:
        pytest.skip("run the complete GUI-FILE-003 stress module set in one process")

    lines = ["", "GUI-FILE-003 executed stress counts:"]
    for name, (executed, required) in EXECUTED.items():
        lines.append(
            "  %s: %d/%d %s"
            % (name, executed, required, "PASS" if executed >= required else "FAIL")
        )
    lines.append("GUI-FILE-003 measured invariants:")
    for name in ZERO_INVARIANTS:
        lines.append("  %s: %d" % (name, METRICS[name]))
    for name in (
        "peak_local_mutation_concurrency",
        "peak_remote_mutation_concurrency",
        "lost_remote_mutations",
    ):
        lines.append("  %s: %d" % (name, METRICS[name]))
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
    missing = [name for name in required_groups if name not in EXECUTED]
    assert not missing, "stress groups did not run: %s" % missing
    for name in ZERO_INVARIANTS:
        assert METRICS[name] == 0, "%s = %d" % (name, METRICS[name])
    assert METRICS["peak_local_mutation_concurrency"] <= 1
    assert METRICS["peak_remote_mutation_concurrency"] <= 1
