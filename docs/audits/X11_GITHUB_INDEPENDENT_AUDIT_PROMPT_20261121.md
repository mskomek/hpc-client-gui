# Independent GitHub Audit Request: HPC Client GUI X11 Final Repair

You are an independent auditor. You were not involved in the implementation. Audit the current GitHub state and the exact source revisions below; do not assume this handoff or prior audit reports are correct. Inspect actual GitHub commits, PR diffs, checks, files, and available evidence. Report discrepancies and missing evidence plainly. Do not modify branches, approve reviews, push, or merge.

## Repository and target

- Repository: `mskomek/hpc-client-gui` (`https://github.com/mskomek/hpc-client-gui`)
- Intended integration target: `develop`
- Main implementation branch: `codex/x11-final-develop-20261119`
- Main branch baseline recorded by the implementation session: `0ea4a5953228fe79ce7ce7c07c0b7ed04a03b2b8`
- Separate protocol/security branch: `codex/audit-x11-paramiko-forwarder-20261114`
- Existing draft PR: `#67`, base `develop`
- PR #67 head recorded by the implementation session: `339b86bada84504d2d02af002fad6b6af13777a5`
- `develop` baseline recorded in the session: `2be856dbc3d7a75f7149b1c6243e25af005de799`

These are historical identifiers from the session. Verify the live refs and PR head before drawing conclusions. The user has now authorized publishing the implementation branch. Verify whether that push completed and inspect the actual remote head; if it did not, report the exact reason. Audit only what is actually available remotely, and clearly distinguish it from local-only work. Do not infer that uncommitted or unpushed changes are on GitHub.

## Goal

Evaluate whether the current X11 and active-terminal changes are safe, correctly split, independently verifiable, and ready for review or integration. The expected PR decomposition is:

| Part | Responsibility | Dependency |
|---|---|---|
| A | X11 protocol/security and Paramiko forwarding (existing PR #67) | Independent |
| B | WebView terminal behavior and lifecycle | Independent |
| D | wx/Qt ordering and independent regression coverage | Independent |
| C | Active Paramiko/X11 GUI integration | Requires A and B |

Reassess this split from actual changed hunks and dependencies. The proposed order is A → B → D → C, subject to actual `develop` state and branch protection.

## Relevant history and reports

Read these in the repository if available, but verify their claims against source and artifacts:

- `docs/audits/X11_FINAL_REPAIR_AND_PR_SPLIT_20261117.md`
- `docs/audits/R14_EVIDENCE_REPAIR_VERIFICATION_20261118.md`
- `docs/audits/evidence/r14-final-repair/`
- `docs/audits/evidence/x11-final-develop-integration-20261119/`
- `docs/v2/V2_MAIN_TO_DEVELOP_CHANGE_LEDGER.md`
- `docs/v2/WX_ACCESSIBILITY_AUDIT.md`

Historical R14 disposition is `EVIDENCE_INCONSISTENT`; do not rewrite it or promote it to PASS. In particular, the original F-03 threeprior stdout/JSON/XML evidence was inconsistent and remains `UNVERIFIED` unless original provenance is independently established. F-02 wxstate log was recovered and hash-verified; F-04 explains 751 requests versus 750 unique tests; F-05 has missing Task Scheduler provenance; F-09 chronology was corrected. Treat missing historical artifacts as `MISSING_EVIDENCE`, separate from new acceptance evidence.

## Work and test attempts reported so far

All counts below are claims to check against retained raw receipts, exact source identities, and live CI. Do not report a result as verified if its raw evidence is absent.

1. Earlier integrated full pytest attempt: 3,983 collected; two failures were reported in `tests/test_docs_references.py::test_referenced_local_files_exist` and `tests/test_wx_a11y.py::test_wx_a11y_terminal_limits_documented`; the process then suffered a native crash near 96%, so there was no valid successful exit or complete final JUnit. This was not a passing full suite.
2. An earlier Ubuntu v39 run from an incomplete source archive reportedly ended `3963 passed, 45 skipped, 29 subtests, 3 failed`; harness/source completeness was inadequate.
3. Ubuntu v44 run from a Git-backed but incomplete snapshot reportedly ended `3953 passed, 45 skipped, 29 subtests, 13 failed`; many failures were attributed to omitted `.git`, historical GUI artifacts, and an untracked W61 artifact. It was explicitly not accepted as final source evidence.
4. Ubuntu v42 focused wx layout tests reportedly passed 4 tests under GNOME/Xwayland at 1024×768. Raw evidence and source SHA still need checking.
5. Ubuntu v45 snapshot was reportedly built from baseline SHA `0ea4a595...` with local overlay: 2,104 file entries; manifest SHA `71d21fd1445452156ad717422a482d84ddda4b9723e21c332efa9e3cd26f4c13`; source listing hash `37bfdc34222057d6a27783c598c268ebef219f6aea9e51ac876b8baa3c6c0a61`; an earlier GUI audit commit was fetched only to supply historical fixtures. A focused set covering earlier failure areas reportedly passed 37/37. The v45 full pytest was launched, but its recorded directory was later absent from the reachable `ubuntu-test` account; no final JUnit, exit code, or valid full-suite result was available at handoff. Do not claim full pytest PASS.
6. Baba Windows GUI evidence reportedly ran ten predecessor stress invocations, each 1/1 passing under interactive Session 2, with Task Scheduler Last Result 0. The evidence folder is expected under `docs/audits/evidence/x11-final-develop-integration-20261119/windows/baba-v44-predecessor-10x/`. It is focused GUI lifecycle evidence, not X11 acceptance.
7. Kole Windows11-New evidence reportedly ran in active `home` Session 1: ten predecessor runs each 1/1 and `tests/test_wx_terminal_webview_bridge.py` 12/12, all exit 0; task Last Result 0. Expected evidence folder: `docs/audits/evidence/x11-final-develop-integration-20261119/windows/win11new-v45-session1-native-stress/`. It does not establish a root cause for the historical native crash, end-to-end SSH/X11, or packaged shutdown.
8. Focused Ubuntu set v45 reportedly passed 37/37 after earlier failures were replayed, but the full v45 receipt was not available. An Ubuntu evidence auditor noted that no retained v45 receipt was present at the time of its review.
9. Latest code checks reportedly passed: Ruff on changed source/tests, `compileall`, source architecture gate (`1105 Python files; 0 over 500 lines`), and Ubuntu `pip check`. Independently reproduce or inspect exact receipts.
10. A real Ubuntu GUI splitter probe reportedly showed that a 300 px requested sash was clamped to 450 px and yielded a 276×33 px local listing area. Evaluate whether that is usable and inspect its raw receipt.
11. Native crash evidence historically includes Windows exit codes `0xC0000005` and `0xC0000374`; the root cause is still open. Bridge-module-only tests reportedly passed 9/9; ordered GUI sequences were intermittent. Ten repeated predecessor runs reportedly passed on Baba and ten on Kole Windows11-New, but do not call the native crash fixed without checking exact sequence equivalence, source SHA, interactive session, process exits, and crash telemetry.
12. Earlier external audit reviews: native lifecycle audit found no newly identified lifecycle defect but kept native crash/root cause HIGH/OPEN/UNVERIFIED; evidence audit found the Baba and Kole Windows bundles internally consistent (checksums, source manifests, JUnit/stdout/exits, scheduler metadata; no secret-pattern findings); protocol audit of a PR #67 candidate reported no remaining lifecycle/security findings in its reviewed scope, while noting lack of real packetizer/socket tests. Re-read the actual audit artifacts and confirm which exact code SHA they reviewed.

## Audit work required

### 1. GitHub state and provenance

- Verify live branch heads, ancestry, PR #67 state/base/head, required checks, reviews, branch protection, and current `develop` head.
- Identify which changes are remote and which are only in local worktrees. Do not treat local uncommitted state as a GitHub diff.
- For every proposed PR, list exact base/head SHAs, commits, changed paths, and dependency edges.
- Inspect path and hunk ownership for `wx_shell_frame.py`, `wx_shell_events.py`, `ssh/client.py`, `ssh/contracts.py`, `tests/test_linux_x11.py`, and `tests/test_security_hardening_wave.py`; identify overlap, missing hunks, accidental cherry-picks, and API compatibility issues.
- Preserve PR #67 as protocol/security-only. Do not move its changes into another PR without proving ownership and ancestry.

### 2. PR #67 protocol/security

Inspect actual implementation and tests for active relay sockets/channels, `close()` lifecycle, blocked `sendall()` teardown, bounded shutdown/backpressure, X11 cookie validation, trusted/untrusted separation, fake-cookie rewriting, fail-closed behavior, local display boundaries, worker cleanup, and unauthenticated clients. Pay special attention to concurrent `close()` during a blocked relay. Require negative tests and a reproducible shutdown regression. Distinguish unit/fake-server evidence from real X11 acceptance.

### 3. Native wx/WebView lifecycle

Inspect app/event loop activation, `Dispatch()`/`wx.Yield()`, WebView2 and HWND creation/destruction, pending callbacks, event handlers, GC, Qt/wx import and collection order, test fixture cleanup, worker threads, delayed callbacks, resize/repaint, navigation callbacks, UI-thread affinity, and state leaking between tests. Evaluate the claimed minimal fix and predecessor stress evidence. If the root cause is not proven, leave it open. Native crash closure requires the original failing ordered sequence to be run at least ten times on a real Windows Session 1 GUI with fresh JUnit/stdout/stderr and native process exit 0 every time, with no access violation or heap corruption.

### 4. Tests and evidence integrity

- Bind every result to source SHA, environment, command, UTC/local time, native process exit, stdout/stderr, and fresh JUnit.
- Parse JUnit and compare totals/failures/errors/skips to console summary and exit status.
- Check that no stale JUnit was reused and that evidence checksums match.
- Verify Task Scheduler task identity, interactive session, process identity/exit, and Last Result where applicable.
- Scan evidence for secrets and credentials; do not expose secret content.
- Maintain historical-vs-current evidence separation and leave missing records explicitly missing.
- Confirm whether the failed docs references and accessibility tests are fixed for real reasons rather than weakened or skipped.
- Confirm the full suite has a complete successful run; if not, mark it incomplete.

### 5. Platform and packaging acceptance

Determine whether there is reproducible, source-bound evidence for real Windows GUI, SSH, X11 off/on trusted/on untrusted, real xclock or equivalent, reconnect, terminal output/UTF-8/ANSI/clipboard, GUI close/reopen, WebView child cleanup, native shutdown, untrusted cookie rejection, relay cleanup, and packaged executable natural shutdown using the actual main HWND. Check real Ubuntu X11 desktop and headless tests similarly. Require exact source/package hashes and smoke receipts. Do not accept mocks as platform acceptance.

### 6. Code quality and develop readiness

Check repository instructions, architecture rules (acyclic dependencies; first-party source/test files ≤500 physical lines), Ruff, compileall, typing if configured, i18n/security/architecture checks, test collection, packaging, dependency consistency, and Windows/Linux compatibility. Evaluate PR split A/B/D/C from exact hunks. Verify CI on each exact proposed head. Do not infer independent PR success from a combined working tree.

## Required output

Write an independent audit report with:

1. Audited timestamp and exact GitHub repository/branch/PR SHAs.
2. A concise verdict for each of A, B, D, C and PR #67: `READY`, `NOT READY`, or `UNVERIFIED`.
3. Findings sorted by severity `CRITICAL / HIGH / MEDIUM / LOW`, with exact path and line or GitHub diff location, technical explanation, reproduction/evidence, and recommended repair.
4. A test/evidence table with source SHA, platform/session, command, exit, JUnit totals, evidence hashes, and gaps.
5. Explicit distinction between verified remote state, local-only state, historical evidence, and missing evidence.
6. The minimum next tests needed. Avoid rerunning the full suite for a narrow change; prefer focused tests and only reserve a full integrated run for the final acceptance gate or broad-impact changes.
7. Whether any PR is safe to publish for review now. Do not merge or approve.

No final PASS should be issued while a critical/high finding remains open, the native crash root cause is unverified, the full pytest receipt is missing, or required real Windows/Ubuntu X11 acceptance is absent.
