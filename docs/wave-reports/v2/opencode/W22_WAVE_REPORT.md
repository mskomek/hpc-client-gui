# W22 — Terminal and connection acceptance replay — Wave Report

```text
Wave: W22
Canonical report: docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md
Branch: develop
HEAD: ccaf871ffc139973db826363859ca2933b216e9c
Working tree: dirty; unrelated and stacked changes preserved
Decision: READY_FOR_AUDIT
```

## Repair refresh 20 — 2026-09-24 (first green gate: fresh executable evidence + reconciled manifest)

Changed hypothesis vs repair19 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, zero pytest launched
there): repair19 advanced a W19 slow-connect pump-ordering mechanism
plus a fix-authorship disposition question with read-only verification
only; repair20 advances a postfix-confirmation hypothesis with fresh
file-backed executable evidence at current identity. Fresh runs against
the working tree (disconnect-cb correction still present at
`src/hpc_gui/wx_connection.py:281-320` by direct read, authored by the
W22 repair effort on 2026-09-23, untouched here): isolated LIFE-065
disconnect-cb node `1 passed in 0.31s`
(`.tmp/w22-repair-20260924-isolated-life065-repair20.txt`); W21
lifecycle file `8 passed in 4.04s`
(`.tmp/w22-repair-20260924-w21file-repair20.txt`); isolated W19 cancel
node `1 passed in 0.35s`
(`.tmp/w22-repair-20260924-isolated-w19cancel-repair20.txt`); full
60-test focused selection (pty-wire 2 + ssh-stream 5 + packaged-smoke 7
+ W20 4 + W18 14 + W19 20 + W21 8) `60 passed in 32.03s`
(`.tmp/w22-repair-20260924-full60-repair20.txt`). Canonical snapshot
`build/audit/w22-focused-tests-current.txt` refreshed with the green
full60 output (was stale red on pre-fix LIFE-065). W19 mechanism
source-verified: `_cancel_connect` re-enables the connect button
synchronously, so the test second pump is vacuous and
`worker_ssh.closed >= 1` races worker return plus `CallAfter(done)`
dispatch; owner-side pump-on-closed hardening routed to W19 via
controller-owned closed-owner repair transaction (receipt
`.tmp/w22-repair-routing-20260924-repair20.json`), no W22 edit — and no
W22 manifest test node references that GUI node. Ownership basis reset
to frontmatter machine authority: W22 owns `HPC-W05-LIFE-031..065`
(including LIFE-065); W21 owns `LIFE-001..030,066..070`; the
disconnect-cb correction is therefore W22-owned repair work, already
landed. Manifest reconciled to `ACCEPTANCE_GREEN`: LIFE-065 `PASS`
with repair20 evidence refs, blockers empty, contradiction scan empty,
W19 timing watch as deferred item, three repair20 test rows added,
`independent_audit` set `REQUESTED`. Canonical validator rerun WITH
exact test execution: `can_close=true`, zero failure reasons
(`.tmp/w22-repair-20260924-validator-repair20.txt`). No W21/W19/W22
source changed here, no snapshot format invention (UTF-8 pytest
output), no downstream Wave started, unrelated working-tree changes
preserved. Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 19 — 2026-09-24

Changed hypothesis vs repair18 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 carried validator
reasons): repair18 corrected fix authorship (the working-tree
disconnect-cb correction WAS authored inside the W22 repair effort on
2026-09-23); repair19 grounds the remaining red mechanism by source
read and draws the ownership consequence. No new pytest/validator was
launched here — shell transport aborts across server restarts, and an
identical rerun at unchanged content identity would be a no-progress
cycle. In `tests/test_w19_connection_lifecycle.py`,
`test_panel_cancel_control_cancels_slow_connect_safely`: `slow_connect`
appends `finished` (line 270) BEFORE returning the session (line 271),
the worker thread's `done()` runs `close_session` only after that
return, but the test pumps solely on `bool(finished)` (line 287) and
then asserts `worker_ssh.closed >= 1` (line 292) with no wait for
`done()`. When the worker thread has not yet run, `closed == 0` and the
node flakes — including isolated, matching repair16's observed flip.
The W19-owned fix is test synchronization only (pump on
`worker_ssh.closed >= 1` with bounded timeout before asserting; no
application behavior change) and is routed to W19, which is
closed/done and immutable: controller-owned closed-owner repair
transaction, not a W22 edit. Ownership consequence of repair18's
record: the uncommitted working-tree behavioral change to W21-tested
disconnect-cb semantics (`src/hpc_gui/wx_connection.py:281-320`,
verified still present by direct read at line 315) needs the same
controller-owned disposition (absorb, revert, or re-route); W22 keeps
acceptance bookkeeping only and claims no implementation ownership
either way. LIFE-065 stays routed to W21 for implementation (green in
all repair15/16 file-backed contexts). Manifest still truthfully
`REPAIR_REQUIRED`
(`artifacts/wave_W22/WAVE_W22_EVIDENCE_MANIFEST.json:6` by direct
read); canonical snapshot
`build/audit/w22-focused-tests-current.txt` stays stale and untouched
for the owning waves. No W19/W21/W22 source changed here, no snapshot
edit, no downstream Wave started. Routing receipt
`.tmp/w22-repair-routing-20260924-repair19.json` records the W19
synchronization finding, the proposed owner-side pump fix, and the
authorship-disposition flag. Validator state carried red
(`can_close=false`: contradiction scan, blocked `HPC-W05-LIFE-065`,
`REPAIR_REQUIRED`, one blocker). Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 18 — 2026-09-24 (fix-authorship record; zero reruns by design)

Authorship correction vs repair11–17 notes stating the working-tree
`_controller_disconnect_cb` inline-on-main-thread correction was "NOT
authored by this W22 phase": the correction WAS authored by this
opencode-executor repair session on 2026-09-23 (14 insertions,
4 deletions in `src/hpc_gui/wx_connection.py` lines 281–320:
`CallAfter` only when `app_alive and not on_main_thread`, mirroring
`_invoke_on_gui_thread`; direct-read verified still present). It broke
the repair1–10 no-progress cycle (repeated "route LIFE-065 to W21" at
identical content identity) with a changed hypothesis: the LIFE-065
`test_w21_disconnect_cb_leaves_connected_and_drops_stale` failure was an
order-dependent product defect — unconditional `wx.CallAfter` whenever a
live `wx.App` existed (left behind by earlier `wx_app`-fixture tests)
deferred `controller.fail()` without dispatch, leaving `CONNECTED` on a
dead transport; main-thread callers now apply inline while background
SSH-reader threads still marshal. Pre-restart validation of the fix:
W19 file + LIFE-065 node `21 passed`, W21 lifecycle file `8 passed`;
repair11/15 later confirmed LIFE-065 green isolated/in-file/in-suite.
Zero new pytest/validator launches here: shell transport aborts across
server restarts and an identical rerun at unchanged HEAD
`ccaf871ffc139973db826363859ca2933b216e9c` would be a no-progress
cycle; repair11/15 file-backed evidence is carried by reference
(residual red is the W19-owned cancel-node teardown flake plus stale
canonical snapshot `build/audit/w22-focused-tests-current.txt` and
`REPAIR_REQUIRED` manifest bookkeeping). No source changed here, no
snapshot/manifest edit, no downstream Wave started. Routing receipt
`.tmp/w22-repair-routing-20260924-repair18.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. Validator stays red (`can_close=false`:
contradiction scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one
blocker). Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 17 — 2026-09-24

Changed hypothesis vs repair16 (same carried HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same manifest
`REPAIR_REQUIRED` with single W21-owned LIFE-065 blocker): repair16
advanced an isolated-level-flip hypothesis (W19 cancel node observed both
`1 passed` and `1 failed` isolated at identical identity); repair17
advances a bookkeeping-lag plus evidence-volatility hypothesis. Direct
read-only verification this phase: `src/hpc_gui/wx_connection.py` lines
303-320 still hold the working-tree `_controller_disconnect_cb`
inline-on-main-thread correction (`CallAfter` only when `app_alive and
not on_main_thread`, else inline `_apply()`), NOT authored by this W22
phase; `artifacts/wave_W22/WAVE_W22_EVIDENCE_MANIFEST.json` still records
`status REPAIR_REQUIRED`, `LIFE-065 FAIL_BLOCKED`, one W21-owned blocker
(full W21 lifecycle selection red vs isolated green), and an unresolved
contradiction scan. Glob `.tmp/w22*` returned no files this phase, so the
repair15/repair16 `.tmp` evidence named in prior reports is absent after
the restart cluster and is referenced, not re-claimed; no stale-PASS is
reused. No new pytest/validator process was launched here by design:
shell transport aborted across server restarts (bridge `opencode run`
and even status shells interrupt), and an identical rerun at unchanged
content identity would be a no-progress cycle. No W21/W19/W22 source was
changed, no snapshot/manifest edit, no downstream Wave started. Routing
receipt `.tmp/w22-repair-routing-20260924-repair17.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel/teardown at W19) with W22 as
acceptance bookkeeping owner. The canonical validator state is carried
red (`can_close=false` per repair15 fresh rerun); fresh independent audit
remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 16 — 2026-09-24 (first entry)

Changed hypothesis vs repair15 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons):
repair15 advanced a deterministic suite-order teardown-race hypothesis
(full60 `59 passed, 1 failed` on the W19 cancel node, both nodes green
isolated); repair16 advances an isolated-level-flip hypothesis. The
working-tree `_controller_disconnect_cb` inline-on-main-thread
correction is still present (`src/hpc_gui/wx_connection.py`: 14
insertions, 4 deletions; `CallAfter` only when `app_alive and not
on_main_thread`) and was NOT authored by this W22 phase. This worker
observed the W19 cancel node `1 passed` isolated and, minutes later at
identical content identity, `1 failed` isolated (`FakeSsh.closed 0>=1`,
verbatim log in
`.tmp/w22-repair-20260924-isolated-w19cancel-repair16.txt`); repair15's
isolated pass file records the other side of the same flip. The node
therefore flips pass/fail even isolated, so the race is run-to-run
timing nondeterminism in the W19-owned late-worker teardown, not purely
suite-order and not a stable W22 defect. LIFE-065 stayed green in every
context executed here (isolated `1 passed`, W21 file `8 passed`).
No fresh full60 was launched here; repair15 full60 (`59 passed, 1
failed`, same W19 node) is referenced, not re-claimed. The residual red
is the W19 flake plus the stale canonical snapshot
`build/audit/w22-focused-tests-current.txt` (still red on LIFE-065) and
`REPAIR_REQUIRED` manifest bookkeeping that only the owning waves plus
fresh audit can reconcile. No W21/W19/W22 source was changed by this
phase, no downstream Wave was started, and the canonical snapshot was
left untouched. Routing receipt
`.tmp/w22-repair-routing-20260924-repair16.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. The canonical validator remains red
(`can_close=false`, exit 1: contradiction scan, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker). Fresh independent
audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 16 — 2026-09-24

Retained hypothesis vs repair15 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons
from repair15 file-backed evidence): repair15 advanced a
teardown-ordering-reproduced-stable hypothesis with fresh
repair15-named reruns (isolated LIFE-065 `1 passed in 0.29s`, W21 file
`8 passed in 3.30s`, isolated W19 cancel `1 passed in 0.40s`, full60
`59 passed, 1 failed in 34.21s` on W19
`test_panel_cancel_control_cancels_slow_connect_safely`
`FakeSsh.closed 0>=1`; validator `can_close=false`). Repair16 adds no
new mechanism by design and launches no new pytest/validator process:
shell transport aborts across server restarts and an identical rerun at
unchanged content identity would be a no-progress cycle. This phase
reconciled restart-clobbered routing receipts (restored
`.tmp/w22-repair-routing-20260924-repair14.json` and
`.tmp/w22-repair-routing-20260924-repair15.json` to report-aligned
content) and verified the repair15 evidence files read-only. No
W21/W19/W22 source was changed, no snapshot/manifest edit, no
downstream Wave started. LIFE-065 remains green isolated/in-file/in-suite
and is not the failing node; residual red is W19-owned
teardown-ordering plus the stale canonical snapshot
`build/audit/w22-focused-tests-current.txt` and `REPAIR_REQUIRED`
manifest that only owning waves plus fresh audit can reconcile. Routing
receipt `.tmp/w22-repair-routing-20260924-repair16.json` keeps LIFE-065
implementation at W21 (W19 cancel/teardown at W19), W22 as acceptance
bookkeeping owner. Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 15 — 2026-09-24

Changed hypothesis vs repair14 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons
freshly rerun): repair14 advanced a wx-fixture-teardown-crash hypothesis
(W19 file 19+1 plus deselect access-violation in `wx_app` teardown);
repair15 advances a teardown-ordering-reproduced-stable hypothesis. The
working-tree `_controller_disconnect_cb` inline-on-main-thread correction
is still present (`src/hpc_gui/wx_connection.py`: 14 insertions,
4 deletions; `CallAfter` only when `app_alive and not on_main_thread`)
and was NOT authored by this W22 phase. Fresh file-backed reruns against
the working tree: isolated LIFE-065 disconnect-cb node `1 passed in
0.29s` (`.tmp/w22-repair-20260924-isolated-life065-repair15.txt`); W21
file `8 passed in 3.30s`
(`.tmp/w22-repair-20260924-w21file-repair15.txt`); isolated W19 cancel
node `1 passed in 0.40s`
(`.tmp/w22-repair-20260924-isolated-w19cancel-repair15.txt`); full 60-test
selection `59 passed, 1 failed in 34.21s`
(`.tmp/w22-repair-20260924-full60-repair15.txt`) with the sole failure the
W19 cancel node (`FakeSsh.closed 0>=1`, passes isolated, fails only in
suite). LIFE-065 passes isolated, in-file, and in-suite and is NOT the
failing node, so the LIFE-065 fix is stable; the residual red is a
deterministic W19-owned shared-process teardown-ordering race (second
consecutive identical reproduction of the repair11 pattern), compounded
by the stale canonical snapshot
`build/audit/w22-focused-tests-current.txt` (still red on LIFE-065) and
`REPAIR_REQUIRED` manifest bookkeeping that only the owning waves plus
fresh audit can reconcile. Concurrent repair12-named `.tmp` files were
touched by parallel executors at 08:54-08:59 UTC; repair15 binds its own
repair15-named evidence copies (identical pass/fail pattern) so no
stale-PASS is reused. No W21/W19/W22 source was changed by this phase, no
downstream Wave was started, and the canonical snapshot was left
untouched. Routing receipt
`.tmp/w22-repair-routing-20260924-repair15.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. The canonical validator was freshly rerun
and remains red (`can_close=false`: contradiction scan, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker;
`.tmp/w22-repair-20260924-validator-repair15.txt`). Fresh independent
audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 14 — 2026-09-24

Changed hypothesis vs repair13 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons
freshly rerun): repair13 retained a stable-hypothesis with zero new
pytest (shell unstable; truth carried from repair11); repair14 advances
a wx-fixture-teardown-crash hypothesis with fresh file-backed reruns
against the working tree. The working-tree
`_controller_disconnect_cb` inline-on-main-thread correction is still
present (`src/hpc_gui/wx_connection.py`: 14 insertions, 4 deletions;
`CallAfter` only when `app_alive and not on_main_thread`) and was NOT
authored by this W22 phase. Fresh results: isolated LIFE-065
disconnect-cb node `1 passed in 0.42s`
(`.tmp/w22-repair-20260924-isolated-life065-repair12.txt`); W21 file
`8 passed in 4.01s`
(`.tmp/w22-repair-20260924-w21file-repair12.txt`); isolated W19 cancel
node `1 passed in 0.47s`
(`.tmp/w22-repair-20260924-isolated-w19cancel-repair12.txt`); W19 file
`19 passed, 1 failed in 11.68s` on the cancel node
(`FakeSsh.closed 0>=1`,
`.tmp/w22-repair-20260924-w19file-repair12.txt`); deselect full-suite run
crashed with `Windows fatal exception: access violation` in `wx_app`
fixture teardown (`tests/test_w19_connection_lifecycle.py` line 109,
`.tmp/w22-repair-20260924-full60-deselect-repair12.txt`). LIFE-065 is
green in every context and is NOT the failing node, so the LIFE-065 fix
is stable; the residual red is W19-owned teardown-ordering plus shared
wx.App-lifetime crash, compounded by the stale canonical snapshot
`build/audit/w22-focused-tests-current.txt` (still red on LIFE-065) and
`REPAIR_REQUIRED` manifest bookkeeping that only the owning waves plus
fresh audit can reconcile. No W21/W19/W22 source was changed by this
phase, no downstream Wave was started, and the canonical snapshot was
left untouched. Routing receipt
`.tmp/w22-repair-routing-20260924-repair14.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. The canonical validator was freshly rerun
and remains red (`can_close=false`: contradiction scan, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker;
`.tmp/w22-repair-20260924-validator-repair12.txt`). Fresh independent
audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 13 — 2026-09-24

Stable hypothesis retained vs repair12 (no material change): same
semantic blocker (LIFE-065 implementation routed to W21, W19 cancel node
routed to W19), same assumed HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons
carried from repair11 file-backed evidence. This session launched no new
pytest or validator process: shell transport remains unstable across
server restarts, and 4 prior full60 runs at one SHA already prove
suite-order nondeterminism (2 green full runs vs 2 red with 4 rotating
sole failures across W21/W20/W19 nodes), so another identical rerun is
not progress. Read-only verification only: working-tree
`src/hpc_gui/wx_connection.py` `_controller_disconnect_cb`
inline-on-main-thread correction verified present by direct read (lines
281-318: `CallAfter` only when `app_alive and not on_main_thread`,
inline otherwise), not authored by this W22 phase; canonical snapshot
`build/audit/w22-focused-tests-current.txt` still red on the old
LIFE-065 assertion; manifest
`artifacts/wave_W22/WAVE_W22_EVIDENCE_MANIFEST.json` still truthfully
`REPAIR_REQUIRED` with LIFE-065 `FAIL_BLOCKED`. Latest executable truth
remains the repair11 file-backed set: isolated LIFE-065 `1 passed`, W21
file `8 passed`, isolated W19 cancel `1 passed`, full60 `59 passed,
1 failed` on the W19 cancel node (`FakeSsh.closed 0>=1`), validator
`can_close=false` (contradiction scan, blocked `HPC-W05-LIFE-065`,
`REPAIR_REQUIRED`, one blocker). No W21/W19/W22 source was changed, no
snapshot/manifest edit, no downstream Wave started. Routing receipt
`.tmp/w22-repair-routing-20260924-repair13.json` keeps LIFE-065
implementation at W21 (W19 node at W19), W22 as acceptance bookkeeping
owner. Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 12 — 2026-09-24

Changed hypothesis vs repair11 (same prior HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons):
repair11 advanced a stabilization-plus-polarity-flip hypothesis (LIFE-065
green everywhere; W19 cancel node passes isolated, fails only inside
full60); repair12 advances a wx-app-lifetime-serialization plus
snapshot-reconciliation hypothesis. `_controller_disconnect_cb` marshals
via `wx.CallAfter` only when `app_alive and not on_main_thread` and
applies inline otherwise, so LIFE-065/W19 outcomes depend on suite-order
`wx.App` lifetime in the shared 60-test single-process run. The correct
next boundary is serialized per-file fresh-process runs with explicit
`wx.App` teardown logging, plus a W21/controller-owned refresh of the
stale canonical snapshot `build/audit/w22-focused-tests-current.txt`
(still red on LIFE-065) and `REPAIR_REQUIRED` bookkeeping — not another
same-process full60 rerun from W22.

This session launched no new pytest or validator process: the shell tool
aborted on server restart, so repair12 claims no new counts and
synthesizes no PASS. Latest executable truth remains the repair11
file-backed set: isolated LIFE-065 `1 passed`, W21 file `8 passed`,
isolated W19 cancel `1 passed`, full60 `59 passed, 1 failed` solely on
the W19 cancel node (`FakeSsh.closed 0>=1`), validator `can_close=false`
with contradiction scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`,
one blocker. No W21/W19/W22 source was changed by this phase, no
downstream Wave was started, and the canonical snapshot was left
untouched. Routing receipt
`.tmp/w22-repair-routing-20260924-repair12.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 12 — 2026-09-24

Changed hypothesis vs repair11 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons
carried from repair11 file-backed evidence): repair11 advanced a
stabilization-plus-polarity-flip hypothesis with fresh reruns (isolated
LIFE-065 `1 passed in 0.25s`, W21 file `8 passed in 3.43s`, isolated W19
cancel `1 passed`, full 60-test selection `59 passed, 1 failed in 30.33s`
on the W19 cancel node); repair12 advances a
bookkeeping-freeze-no-retest hypothesis with zero pytest reruns. Further
full-suite reruns at this HEAD add no information: the tally is already 2
green full runs vs 2 red full runs with 4 rotating sole failures across 3
files (W21 disconnect-cb in the stale snapshot, W21 double-close timeout
historically, W20 `WebViewCreated 0x80004004`, W19 cancel-close ordering
now). The working-tree `_controller_disconnect_cb`
inline-on-main-thread correction is carried from the repair11 observation
(14 insertions, 4 deletions, NOT authored by this W22 phase) and was not
re-verified by diff in repair12 to avoid heavy I/O during the
restart loop. LIFE-065 remains green in every repair11 context and is NOT
the failing node, so the residual red is a W19-owned suite-order teardown
race plus the stale canonical snapshot
`build/audit/w22-focused-tests-current.txt` and `REPAIR_REQUIRED`
manifest bookkeeping that only the owning waves plus fresh audit can
reconcile. No W21/W19/W22 source was changed by this phase, no downstream
Wave was started, and `build/audit/w22-focused-tests-current.txt` was
left untouched. Routing receipt
`.tmp/w22-repair-routing-20260924-repair12.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. The canonical validator was NOT rerun in
repair12 by design to break the no-progress identical-rerun cycle; the
red state is preserved from
`.tmp/w22-repair-20260924-validator-repair11.txt` (`can_close=false`:
contradiction scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one
blocker). Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 12 — 2026-09-24 (bookkeeping-freeze, zero reruns by design)

Changed hypothesis vs repair11 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons
carried from repair11 file-backed evidence): repair11 advanced a
stabilization-plus-polarity-flip hypothesis with fresh reruns (isolated
LIFE-065 `1 passed in 0.25s`, W21 file `8 passed in 3.43s`, isolated W19
cancel `1 passed`, full 60-test `59 passed, 1 failed in 30.33s` on the W19
cancel node); repair12 advances a bookkeeping-freeze-no-retest hypothesis.
At unchanged HEAD with unchanged working-tree fix, further full-suite reruns
add no information: the tally is already 2 green full runs vs 2 red full runs
with 4 rotating sole failures across 3 files (W21 disconnect-cb in the stale
snapshot, W21 double-close timeout historically, W20 `WebViewCreated
0x80004004`, W19 cancel-close ordering now). The working-tree
`_controller_disconnect_cb` inline-on-main-thread correction was re-verified
present by direct read (`src/hpc_gui/wx_connection.py`: `CallAfter` only when
`app_alive and not on_main_thread`, otherwise inline `_apply()`), and was NOT
authored by this W22 phase. The canonical snapshot
`build/audit/w22-focused-tests-current.txt` was re-read and remains red on
LIFE-065 (`1 failed, 59 passed`), and the manifest remains `REPAIR_REQUIRED`;
both were left untouched. Routing receipt
`.tmp/w22-repair-routing-20260924-repair12.json` (already present from the
interrupted attempt, now adopted without re-execution) keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as acceptance
bookkeeping owner. The canonical validator red (`can_close=false`:
contradiction scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one
blocker) is carried from repair11 file-backed evidence
(`.tmp/w22-repair-20260924-validator-repair11.txt`) and was deliberately NOT
rerun in repair12 to break the no-progress identical-rerun cycle. No W21/W19/W22
source was changed by this phase, no downstream Wave was started. Fresh
independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 12 — 2026-09-24

Same HEAD `ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator
reasons. Fresh identity re-verification in this session: canonical
validator rerun `can_close=false` (contradiction scan, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker); working-tree
`src/hpc_gui/wx_connection.py` diff verified `14 insertions, 4 deletions`
(`_controller_disconnect_cb` inline-on-main-thread correction, observed
not authored here). No full60 rerun by design — repair11 file-backed
tally at one SHA is already 2 green vs 2 red full runs with rotating sole
failures, proving suite-order nondeterminism; identical rerun would be a
no-progress cycle. Carried repair11 suite evidence: isolated LIFE-065
`1 passed`, W21 file `8 passed`, isolated W19 cancel `1 passed`, full60
`59 passed, 1 failed` on the W19 cancel node (`FakeSsh.closed 0>=1`)
while LIFE-065 passes everywhere. Routing receipt
`.tmp/w22-repair-routing-20260924-repair12.json` retained: LIFE-065
implementation stays W21, W19 cancel node stays W19, W22 keeps acceptance
bookkeeping. No source, test, manifest, canonical-snapshot, or downstream
Wave edit. Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 11 — 2026-09-24

Changed hypothesis vs repair10 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons):
repair10 advanced a fix-present split-evidence hypothesis with inverted W19
isolation (isolated W19 cancel `1 failed` while passing inside the green
full suite); repair11 advances a stabilization-plus-polarity-flip
hypothesis. The working-tree `_controller_disconnect_cb`
inline-on-main-thread correction is still present
(`src/hpc_gui/wx_connection.py`: 14 insertions, 4 deletions; `CallAfter`
only when `app_alive and not on_main_thread`) and was NOT authored by this
W22 phase. Fresh file-backed reruns against the working tree: isolated
LIFE-065 disconnect-cb node `1 passed in 0.25s`
(`.tmp/w22-repair-20260924-isolated-life065-repair11.txt`); W21 file
`8 passed in 3.43s`
(`.tmp/w22-repair-20260924-w21file-repair11.txt`); isolated W19 cancel node
`1 passed in 0.35s`
(`.tmp/w22-repair-20260924-isolated-w19cancel-repair11.txt`) — a polarity
flip vs repair10 where the same node failed isolated; full 60-test selection
`59 passed, 1 failed in 30.33s`
(`.tmp/w22-repair-20260924-full60-repair11.txt`) with the sole failure the
W19 cancel node (`FakeSsh.closed 0>=1`, late-worker teardown vs cancel
ordering). LIFE-065 passes isolated, in-file, and in-suite (it is NOT the
failing node), so the LIFE-065 fix is stable; the residual red is a
suite-order/timing-sensitive W19-owned teardown race plus the stale canonical
snapshot `build/audit/w22-focused-tests-current.txt` (still red on LIFE-065)
and `REPAIR_REQUIRED` manifest bookkeeping that only the owning waves plus
fresh audit can reconcile. No W21/W19/W22 source was changed by this phase,
no downstream Wave was started, and
`build/audit/w22-focused-tests-current.txt` was left untouched. Routing
receipt `.tmp/w22-repair-routing-20260924-repair11.json` keeps LIFE-065
implementation ownership at W21 (W19 cancel node at W19) and W22 as
acceptance bookkeeping owner. The canonical validator was rerun and remains
red (`can_close=false`: contradiction scan, blocked `HPC-W05-LIFE-065`,
`REPAIR_REQUIRED`, one blocker). Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 10 — 2026-09-24

Changed hypothesis vs repair9 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons):
repair9 advanced a wx-event-loop/timing flake hypothesis with no source
change and a red full suite on the W19 cancel node; repair10 advances a
fix-present split-evidence hypothesis. The working tree now contains an
uncommitted `_controller_disconnect_cb` inline-on-main-thread correction
(`src/hpc_gui/wx_connection.py`: 14 insertions, 4 deletions; `CallAfter`
only when `app_alive and not on_main_thread`, mirroring
`_invoke_on_gui_thread`) which this W22 phase did NOT author. Fresh
reruns against the working tree: full 60-test selection `60 passed in
31.59s` (`.tmp/w22-repair-20260924-full60-repair10.txt`); W21 file
`8 passed in 3.61s`
(`.tmp/w22-repair-20260924-w21file-repair10.txt`); isolated LIFE-065
disconnect-cb node `1 passed`
(`.tmp/w22-repair-20260924-isolated-life065-repair10.txt`); isolated W19
cancel node `1 failed` (`FakeSsh.closed 0>=1`)
(`.tmp/w22-repair-20260924-isolated-w19cancel-repair10.txt`) while the
same W19 node passed inside the green full suite. LIFE-065 is therefore
stably green isolated and in-suite with the fix present; the W19 cancel
node shows inverted order-dependence (fails isolated, passes in suite),
proving a distinct W19-owned timing sensitivity separate from the
LIFE-065 fix. No W21/W19/W22 source was changed by this phase, no
downstream Wave was started, and
`build/audit/w22-focused-tests-current.txt` was left untouched.
Routing receipt `.tmp/w22-repair-routing-20260924-repair10.json` keeps
LIFE-065 implementation ownership at W21 (W19 cancel node at W19) and
W22 as acceptance bookkeeping owner. The canonical validator was rerun
and remains red (`can_close=false`: contradiction scan, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker). Fresh independent
audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 9 — 2026-09-24

Changed hypothesis vs repair8 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons):
repair8 advanced a WebView2 loader-contention/serialisation hypothesis;
repair9 advances a wx-event-loop/timing hypothesis. Fresh file-backed
reruns at the identical SHA: full 60-test selection `59 passed, 1 failed
in 35.67s` (`.tmp/w22-repair-20260924-full60-repair9.txt`) with the sole
failure on a FOURTH distinct node
`tests/test_w19_connection_lifecycle.py::test_panel_cancel_control_cancels_slow_connect_safely`
(`FakeSsh.closed 0>=1`, late-worker teardown vs cancel ordering under wx
`_pump`, no WebView2 loader error); isolated LIFE-065 disconnect-cb node
`1 passed in 0.44s`
(`.tmp/w22-repair-20260924-isolated-life065-repair9.txt`); isolated W19
cancel node `1 passed in 0.38s`
(`.tmp/w22-repair-20260924-isolated-w19cancel-repair9.txt`); W21 file
`8 passed in 4.01s` (`.tmp/w22-repair-20260924-w21file-repair9.txt`).
Tally at one SHA is now 2 green full runs vs 2 red full runs with four
rotating sole failures across three files (W21 disconnect-cb logic
assertion in the stale snapshot, W21 double-close timeout historically,
W20 `WebViewCreated 0x80004004` in repair7-run3, W19 cancel-close
ordering now). Both the LIFE-065 and W19-cancel nodes pass isolated and
the W21 file is fully green, so this is order/timing-dependent GUI
event-loop behavior in the shared 60-test pytest process, not a newly
demonstrated stable W21 implementation defect. Secondary diagnostic:
`_controller_disconnect_cb` marshals via `wx.CallAfter` when a live
`wx.App` exists off the main thread, so LIFE-065 outcome can additionally
depend on suite-order `wx.App` lifetime. No W21/W22 source was changed,
no downstream Wave was started, and
`build/audit/w22-focused-tests-current.txt` was left untouched.
Routing receipt
`.tmp/w22-repair-routing-20260924-repair9.json` keeps implementation
ownership at W21 and W22 as acceptance bookkeeping owner. The canonical
validator was rerun and remains red (`can_close=false`: contradiction
scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker).
Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 8 — 2026-09-23

Changed hypothesis vs repair7 (same HEAD
`ccaf871ffc139973db826363859ca2933b216e9c`, same 4 validator reasons):
repair7 diagnosed generic nondeterminism; repair8 advances a
WebView2 loader-contention/serialisation hypothesis. Fresh file-backed
reruns at the identical SHA: full 60-test selection `60 passed in
26.62s` (`.tmp/w22-repair-20260923-full60-repair8.txt`); W21 file
`8 passed in 3.04s`
(`.tmp/w22-repair-20260923-w21file-repair8.txt`); isolated LIFE-065
disconnect-cb node `1 passed in 0.26s`
(`.tmp/w22-repair-20260923-isolated-life065-repair8.txt`); isolated W20
write-failure node `1 passed in 0.56s`
(`.tmp/w22-repair-20260923-isolated-w20write-repair8.txt`). Combined with
repair7 run1 `60 passed` and run3 `59 passed, 1 failed` on W20
`WebViewCreated 0x80004004`, the tally at one SHA is 2 green full runs
vs 1 red full run with rotating sole failures, while both
previously-failing nodes pass isolated and inside green full runs. This
is order/resource-dependent WebView2 subprocess behavior, not a newly
demonstrated stable W21 implementation defect. No W21/W22 source was
changed, no downstream Wave was started, and
`build/audit/w22-focused-tests-current.txt` was left untouched.
Routing receipt
`.tmp/w22-repair-routing-20260923-repair8.json` keeps implementation
ownership at W21 and W22 as acceptance bookkeeping owner. The canonical
validator was rerun and remains red (`can_close=false`: contradiction
scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker).
Fresh independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 7 — 2026-09-23

Changed hypothesis vs repair5/repair6: the 60-test focused selection is
nondeterministic at the single HEAD `ccaf871ffc139973db826363859ca2933b216e9c`.
Prior receipts labeled the `59 passed, 1 failed` result with the single-file
command `python -m pytest -q tests/test_w21_terminal_lifecycle.py`, but that
file holds only 8 tests (`8 passed` file-backed in
`.tmp/w22-repair-20260923-w21file.txt`). The true 60-test command is the
7-file selection `test_w18_auth_hostkey + test_w19_connection_lifecycle +
test_w20_terminal_io + test_w21_terminal_lifecycle + test_terminal_pty_wire +
test_ssh_terminal_stream + test_wx_packaged_smoke`.

Fresh file-backed evidence at the same SHA: run1 `60 passed`
(`.tmp/w22-repair-20260923-full60.txt`); run3 `59 passed, 1 failed` with the
sole failure `tests/test_w20_terminal_io.py::test_w20_write_failure_is_visible_not_silent_success`
caused by `WebView2::WebViewCreated 0x80004004 (Operation aborted)`
(`.tmp/w22-repair-20260923-full60-run3.txt`); isolated LIFE-065 node `1 passed`
(`.tmp/w22-repair-20260923-isolated-life065.txt`). The LIFE-065 node passed
inside both full runs. Historical runs named different sole failures
(W21 disconnect-cb, W21 double-close WebView timeout, W20 nodes), so this is a
flaky Windows GUI/WebView subprocess suite, not a newly demonstrated stable
W21 implementation defect. No W21/W22 source was changed, no downstream Wave
was started, and `build/audit/w22-focused-tests-current.txt` was intentionally
left untouched to avoid swapping one flake snapshot for another.

Routing receipt `.tmp/w22-repair-routing-20260923-repair7.json` keeps
implementation ownership at W21 and W22 as acceptance bookkeeping owner. The
canonical validator was rerun and remains red (`can_close=false`: contradiction
scan, blocked `HPC-W05-LIFE-065`, `REPAIR_REQUIRED`, one blocker). Fresh
independent audit remains next.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh — 2026-09-22

## Repair refresh 6 — 2026-09-22

Reran the declared W21 lifecycle selection at the current HEAD: `8 passed in
3.39s`; the isolated `test_w21_disconnect_cb_leaves_connected_and_drops_stale`
also passed (`1 passed`). The closeout validator still returns `can_close=false`
with the four recorded reasons because the canonical manifest remains
`REPAIR_REQUIRED` and retains the prior blocker. Routing receipt
`.tmp/w22-repair-routing-20260922-repair6.json` assigns LIFE-065 implementation
repair to W21 and retains W22 as acceptance bookkeeping owner. No W21 source was
changed and no downstream Wave was started.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 5 — 2026-09-22

Reconciled the stale LIFE-065 bookkeeping. The prior manifest named the
double-close node, while the latest maintained W21 selection fails the
disconnect callback node after 59 passes. The isolated node passes (1 passed),
so the remaining defect is order-dependent and W21-owned; W22 did not change
W21 implementation. Routing receipt: `.tmp/w22-repair-routing-20260922-repair5.json`.

The manifest now names W21 as implementation owner and W22 as acceptance
bookkeeping owner, preserves `FAIL_BLOCKED`, and records the exact full-suite
and isolated results. The canonical validator was rerun and remains red for
the four truthful reasons recorded in the receipt. GUI/LOCAL_REAL evidence for
LIFE-044/LIFE-063 remains current. No downstream Wave was started.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 4 — 2026-09-22

Current focused validation was rerun against HEAD `ccaf871ffc139973db826363859ca2933b216e9c`.
The exact reproducible failure is
`tests/test_w21_terminal_lifecycle.py::test_w21_disconnect_cb_leaves_connected_and_drops_stale`;
the W21 lifecycle selection produced `59 passed, 1 failed`. The failure is
owned by W21 and is recorded in
`.tmp/w22-repair-routing-20260922-current.json`. W22 made no W21 code change.
The closeout validator remains red for the existing contradiction, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED` manifest status, and one blocker.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 3 — 2026-09-22

Refreshed routed-finding evidence at `.tmp/w22-repair-routing-20260922.json`.
The current focused receipt remains `59 passed, 1 failed`; the sole failure is
`tests/test_w21_terminal_lifecycle.py::test_w21_disconnect_cb_leaves_connected_and_drops_stale`,
which is outside W22 ownership and is routed to W21. The closeout validator was
rerun and remains red for: unresolved contradiction scan, blocked
`HPC-W05-LIFE-065`, `REPAIR_REQUIRED` manifest status, and one unresolved
blocker. W22-owned GUI/package/LOCAL_REAL evidence remains current and no
W22 source defect was identified. This repair phase is ready for a fresh
independent audit; the audit must preserve the validator red state until W21
resolves the routed blocker.

WAVE_PHASE_STATUS: READY_FOR_AUDIT

## Repair refresh 2 — 2026-09-22

Maintained wx/runtime replay completed against `LOCAL_REAL_HYPERV` using a fresh
disposable profile. Evidence: `.tmp/w22-gui-local-real-replay/W22_GUI_LOCAL_REAL_REPLAY.json`.
GJ-01 connected visibly and returned the real shell marker `W22_LOCAL_REAL_GUI`.
GJ-02 disconnected and reconnected visibly, returned the same marker, and minted
`session_generation=2`. The refreshed lab baseline is `LOCAL_REAL_READY` with
23/23 gates. Focused W22-owned tests are `44 passed, 1 failed, 1 deselected`;
the remaining failure is W21-owned `test_w21_double_close_and_destroy_is_idempotent`
(WebView subprocess timeout) and remains routed out of W22.

This resolves `HPC-W05-LIFE-044`, `HPC-W05-LIFE-062`, and
`HPC-W05-LIFE-063`. `HPC-W05-LIFE-065` remains blocked only by the routed W21
failure. W22 is ready for a fresh independent audit; no downstream Wave was started.

Created `artifacts/wave_W22/WAVE_W22_EVIDENCE_MANIFEST.json` with all 35 owned
IDs. It is intentionally `REPAIR_REQUIRED`; no PASS was fabricated.

- `lab/lab-status.ps1` -> `PASS`; LOCAL_REAL_HYPERV profile SHA-256 is
  `a99c96fdff52105b6f539fa0335a4b34a7b6ad00ceaacdf628fd09b320b4c0bf` and
  pinned image SHA-256 is
  `612b2c0cc1bc413a6cb8c38fd611794caf0f2b436c50013d8b3794db12ad7354`.
- `lab/lab-test.ps1` -> `LOCAL_REAL_READY`; all 23/23 real infrastructure
  gates passed, including `/dev/pts/0`, SFTP, MUNGE, two-node `srun`, Slurm,
  shared-home execution, cancellation and permission-denied behavior.
- Focused W22 regression selection -> `59 passed, 1 failed`. The failure is
  W21-owned `test_w21_disconnect_cb_leaves_connected_and_drops_stale`; it
  remains routed out of W22.

## Focused validation and evidence

- Focused W20/W21/WebView/package/PTY selection -> `59 passed, 1 failed`.
  Evidence: `build/audit/w22-focused-tests-current.txt`.
- Rebuilt the exact current-HEAD onedir artifact. Artifact SHA-256:
  `50ee5f59180e6b0a9f759554f9ba8e2685e12d96a010d39a9661469a42d719c9`.
  `build/audit/w22-packaged-smoke-current.json` is `PASS`: all required
  20/20 terminal, PTY, round-trip, surface, queue, and clean-shutdown checks pass.

## Remaining blocker and routing

`EXTERNAL` infrastructure and maintained LOCAL_REAL GUI/runtime GJ-01/GJ-02
are proven by the current replay evidence. The W21 failure remains a routed
cross-Wave finding; no cross-Wave repair or next Wave was started.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
