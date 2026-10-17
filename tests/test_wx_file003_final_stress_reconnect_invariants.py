"""GUI-FILE-003 final stress and invariant campaign.

Every stress group drives real wx events through the production view handlers
and records the measured invariants in ``METRICS``.  The last test in the file
prints the whole scoreboard and asserts the mandatory zeros, so a regression
shows up as a measured number rather than as a missing assertion.
"""

from __future__ import annotations

pytest_plugins = ('support.test_wx_file003_final_stress_shared',)
from support.test_wx_file003_final_stress_shared import (
    EXECUTED,
    METRICS,
    ZERO_INVARIANTS,
    _AccountingFiles,
    _Lifecycle,
    os,
    pytest,
    threading,
    time,
)

pytestmark = [pytest.mark.wx]

@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
def test_reconnect_session_snapshot_repeated(wx_app, tmp_path):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    class SessionFiles(_AccountingFiles):
        def __init__(self, label, block=None):
            super().__init__()
            self.label = label
            self.block = block

        def upload(self, source, destination):
            if self.block is not None:
                self.started.append("start:" + destination)
                self.block.wait(3)
            self._run(self.label, destination)

    rounds = 20
    for index in range(rounds):
        release = threading.Event()
        first = SessionFiles("S1", block=release)
        second = SessionFiles("S2")
        state = {"session": {"files": first}}
        controller_one = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "a.txt", "/one-%d.txt" % index)],
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not first.started:
            time.sleep(0.005)
        assert first.started, "first operation never started"

        state["session"] = {"files": second}  # reconnect mid-flight
        release.set()
        assert controller_one.engine.wait(5)

        controller_two = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "b.txt", "/two-%d.txt" % index)],
        )
        assert controller_two.engine.wait(5)

        # The in-flight operation must stay on its own snapshot, and the new
        # session must only ever see the operation started after the reconnect.
        if ("/one-%d.txt" % index) in second.started:
            METRICS["mixed_session_transfer_operations"] += 1
        if first.methods != ["S1"] or second.methods != ["S2"]:
            METRICS["mixed_session_transfer_operations"] += 1
        if ("/two-%d.txt" % index) in first.started:
            METRICS["mixed_session_transfer_operations"] += 1

    EXECUTED["reconnect session snapshots"] = (rounds, rounds)
    assert METRICS["mixed_session_transfer_operations"] == 0

@pytest.mark.reporting
@pytest.mark.semantic
def test_zz_measured_invariants(capsys):
    # METRICS/EXECUTED are per process. Under xdist the groups are spread over
    # workers: the zero invariants still hold for this worker's share, but group
    # completeness is only checkable when the module runs in one process.
    distributed = bool(os.environ.get("PYTEST_XDIST_WORKER"))
    if not EXECUTED and not distributed:
        pytest.skip("aggregate of the GUI-FILE-003 stress groups; run the whole module")
    lines = ["", "GUI-FILE-003 executed stress counts:"]
    for name, (executed, required) in EXECUTED.items():
        lines.append("  %s: %d/%d %s" % (name, executed, required, "PASS" if executed >= required else "FAIL"))
    lines.append("GUI-FILE-003 measured invariants:")
    for name in ZERO_INVARIANTS:
        lines.append("  %s: %d" % (name, METRICS[name]))
    for name in ("peak_local_mutation_concurrency", "peak_remote_mutation_concurrency", "lost_remote_mutations"):
        lines.append("  %s: %d" % (name, METRICS[name]))
    report = "\n".join(lines)
    with capsys.disabled():
        print(report)

    missing = [name for name in (
        "right-click retarget",
        "local mutations",
        "remote mutations",
        "target switches",
        "navigate/completion races",
        "browser open/close",
        "blocked close-in-flight",
        "FILE transfer items",
        "unicode/space names",
    ) if name not in EXECUTED]
    if not distributed:
        assert not missing, "stress groups did not run: %s" % missing
    for name in ZERO_INVARIANTS:
        assert METRICS[name] == 0, "%s = %d" % (name, METRICS[name])
    assert METRICS["peak_local_mutation_concurrency"] <= 1
    assert METRICS["peak_remote_mutation_concurrency"] <= 1
