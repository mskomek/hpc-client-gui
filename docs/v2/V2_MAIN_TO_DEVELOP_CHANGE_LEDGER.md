# HPC Client GUI — `main` → V2 `develop` Change Ledger

**Captured:** 2026-10-17 (Europe/Istanbul)
**Repository:** `https://github.com/mskomek/hpc-client-gui`
**Ledger purpose:** give an independent auditor a reproducible map of the current `main` tree, the current V2 `develop` tree, the product work represented between them, and the evidence that supports the V2 noninteractive acceptance claim.

## 1. Authoritative refs and comparison limits

| Ref | Full commit | Observed identity |
|---|---|---|
| `origin/main` | `063d83b523be377d4ef02dc8a61e2fdd15876ecc` | Merge PR #40 from `develop`, 2026-08-30 |
| `origin/develop` | `8c53b3e68d3bd4fc5f44ed2d9ded19645e9bf585` | Merge PR #45, V2 noninteractive closure, 2026-10-17 |
| V2 product source tested by final acceptance report | `e41cb02613b6bad32c41480a88308750bd05ce15` | Ancestor of `origin/develop`; the subsequent tree delta in `src/` and `build/` is empty. PR #45 adds terminal-test import/export corrections. |

These branches have **two best merge bases**: `81fa71db89bae25d9fd3535fa9ea2336e7494595` and `d230ea3c62d554c895d2b0c172e5b92c1d3899d4`. Therefore `git diff main...develop` warns that it selected one merge base. This ledger uses direct endpoint comparison (`git diff origin/main origin/develop`) for the tree delta and reports graph counts only as graph counts, not as a linear “commits since main” claim.

At capture time:

- `git rev-list --left-right --count origin/main...origin/develop`: `331 978` (left-only/right-only reachable commits under Git's symmetric difference semantics).
- Direct endpoint tree delta: **972 paths**, **155,781 insertions**, **5,596 deletions**.
- Largest changed path families include `src/hpc_gui` (253 paths), `docs/wave-reports` (110), `build/audit` (57), and `docs/v2` (33). The complete exact path list is reproducible using the commands in §8.
- This is a long-lived branch/tree comparison, not a statement that every delta was created for V2. Existing product history, wave implementation, retained audit records, moved/deleted records, and V2 closure are separated below.

## 2. Product and engineering work represented in the endpoint delta

The following is a responsibility-level index of the changed tree, based on the endpoint diff and repository history. It groups work so an auditor can trace it to canonical source/tests rather than treating every report or wave as a product feature.

| Workstream | What to inspect in the current tree | Audit focus |
|---|---|---|
| GUI/runtime and wx migration | `src/hpc_gui/`, `docs/v2/`, GUI contracts and migration wave records | wx is the V2 default runtime; Qt is legacy-only where documented. Check GUI responsibilities, accessibility, keyboard/pointer parity, layout/DPI, ownership and lifecycle boundaries. |
| Connection and provider model | provider/profile code under `src/hpc_gui/`, provider tests and authoring docs | structured provider metadata, declared capabilities, safe profile duplication, semantic diffs, provider-specific storage and submission UX, and backward-compatible profile migration. |
| Slurm/jobs/workflow | Slurm and job domain/UI modules, wave tests and provider tests | validated directives/arrays/dependencies, conservative failure explanations, job identity/refresh, submit/cancel/output flows and actual ownership boundaries. |
| Files, SFTP, editor and transfers | file/editor/transfer modules, `tests/test_wx_*`, transfer contracts and evidence | remote navigation, editor encoding policy, conflict/resume behavior, integrity verification, background work, GUI-thread updates, cancellation and shutdown cleanup. |
| Terminal and WebView | terminal modules, terminal contracts, W19 tests and diagnostics | session ownership, VT/ANSI/Unicode behavior, fragment IPC limits/ordering/ACK/reconnect, data privacy, native teardown and CSP. Preserve `script-src 'self'` and `connect-src 'none'`. |
| Packaging and update/release | `build/`, release workflow, package specs, updater code/docs, `docs/VERIFYING_RELEASES.md` | platform-specific package contents, runtime closure, update handoff/rollback, immutable candidate identity, provenance and release gates. |
| CI, architecture and test harness | `.github/workflows/`, `scripts/`, `tests/`, `build/audit/` | source CI coverage by OS, test validity, skip/de-select semantics, architecture gate, lint, packaged smoke, candidate identity and repeatability. |
| Security, licensing and operations | `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, trusted-tool and lab docs | trust boundaries, dependency/license disclosures, credential handling, host-key behavior, safe lab provisioning and non-leakage of terminal/session content. |
| Waves, evidence and documentation | `docs/wave-reports/`, `build/audit/`, `artifacts/`, `TODO_V2_REMAINING.md` | treat these as traceability/evidence inputs, not as proof by filename. Bind every claim to the referenced source SHA, command, exit code and artifact hash. |

### History note

The endpoint history covers many waves before the final V2 closure. Examples visible in first-parent history include provider/profile and Slurm additions from late August/early September, wx terminal and transfer work, W19–W25 product/test/evidence work, and the W26–W55 runtime/lifecycle/package work. The reviewable V2 closure sequence is the PR chain in §3. Do not attribute all 972 changed paths or all graph-only commits to PRs #41–45.

## 3. V2 closure PR and commit ledger

The final V2 closure merged to `develop` through these PRs, in order:

| PR | Merge commit | Subject / accepted change | Verification facts recorded by repository |
|---|---|---|---|
| #41 | `935bc1c57b14438d7b657f3c6cddab2328ecc3e2` | Restore source CI and repair portable wx audit assertions | Re-established source-level CI and portable assertions; check run records are in GitHub/repository evidence. |
| #42 | `2d8a34c920bc771d7c370b4d73236b96c8c56c65` | Repair packaged shutdown evidence and refresh remaining TODO | Routed W55/W16 shutdown ownership and refreshed V2 open-work state. |
| #43 | `10ac46557c81b8f0445fd9ee06b35faf0cec8dc3` | Fix Jobs shutdown and prove Windows onedir smoke | Windows packaged lifecycle correction; original PR summary reports 20/20 onedir smoke. Later final acceptance reran the final Candidate at 21/21. |
| #44 | `062773261040fe3d3194c64ab74e461e14609481` | Fix native Ubuntu SIGSEGV and strict-CSP terminal readback | Ubuntu WebKit/native lifecycle correction; PR title records 6/6 CI. CSP was retained. |
| #45 | `8c53b3e68d3bd4fc5f44ed2d9ded19645e9bf585` | Merge V2 noninteractive acceptance into `develop` | Final acceptance/TODO evidence. PR head included `4434b727d8465e2d6a5b687348f6c10434be38b6`, fixing unused imports in split terminal tests and explicitly exporting test-support names. Final source Ruff and targeted tests passed before merge. |

The branch used for the acceptance execution also contains local commits recorded in the final report: `32c174c`, `0e3e555`, `b76aa72`, `d31dcb71`, `7b626d29`, `8345c825`, and `e41cb026`. The report says these were merged through PR #45. Verify the complete objects and ancestry from Git; the short IDs are labels only.

## 4. Final noninteractive acceptance record

The canonical detailed record is [`V2_FINAL_ACCEPTANCE_REPORT_2026-10-17.md`](V2_FINAL_ACCEPTANCE_REPORT_2026-10-17.md); current open-work ledger is [`TODO_V2_REMAINING.md`](../../TODO_V2_REMAINING.md). The report's claim is **`V2_ACCEPTED` for the noninteractive scope only**, not manual user acceptance or authenticated real-HPC endpoint acceptance.

Recorded final source and artifact identities:

| Item | Identity |
|---|---|
| Product source tested | `e41cb02613b6bad32c41480a88308750bd05ce15` |
| `develop` merge endpoint | `8c53b3e68d3bd4fc5f44ed2d9ded19645e9bf585` |
| Windows onedir Candidate SHA-256 | `77a82b273c97b0d6168fdd718509032a1f49d49f2e5a52e38582c5607c4f9216` |
| Linux `.deb` SHA-256 | `1eaeb425b8a52df14b33abc60960f686946142e001a9272d51ee9383d5c46892` |
| Linux executable payload SHA-256 | `309dd25c9fb3c61c28afdc2b367ee84fa463921c2e8e9e048d504b807dcb9e95` |
| W04 supplied support freeze SHA-256 | `6c41e085a1ecaeaedf6261316ea483cccaafc9b3dbea2ba71bda313fc56d6ed5` |

The report records Windows broad **3052 PASS / 0 FAIL / 2 SKIP / 65 DESELECTED / 29 subtest PASS**, exit 0; W37 file group 8/8; architecture 25 source files, no over-limit or dependency violations; Ruff PASS. It records Candidate packaged smoke 21/21, Windows 11 UIA of 22 visible controls, normal GUI close, host/guest hash match, reconnect with fresh identity, and no Candidate-related WER crash in the queried interval. Linux Ubuntu 24.04 `.deb` install, test-version upgrade, rollback, installed-binary GUI smoke 21/21, purge and cleanup are recorded. W04 support freeze and 28 probes/tests are recorded resolved. Terminal/WebKitGTK, W19 lifecycle and fragment queue suites are recorded 51/51, 20/20 and 10/10, with synthetic queue performance only; no real-cluster soak is implied.

These figures are **claims to verify against the raw logs/manifests**, not substitutes for those artifacts. The detailed raw evidence used by the run was under ignored local `.tmp/evidence-v2-final-closure/` and `.tmp/evidence-windows-v2-final/` paths; those local files are not guaranteed to be part of a clone or GitHub. If unavailable to the auditor, mark the corresponding evidence unavailable and do not infer a pass from this ledger/report alone.

## 5. Current acceptance boundary

- Noninteractive V2 report state: `V2_ACCEPTED`, subject to independently re-verifying source and artifact evidence.
- Out of scope: manual interactive user acceptance; tests requiring real HPC credentials/endpoints; real-cluster network/long-duration soak beyond recorded synthetic throughput.
- AppImage/Flatpak: report treats them as nonmandatory alternatives to the accepted `.deb` path. Recheck the actual V2 acceptance specification before treating either as a gate.
- CI/build evidence: bind each result to its recorded revision. Do not transfer a pass from an older commit or artifact to a newer source without proving the tested bytes are identical.
- GitHub publication: this ledger records no push, PR creation, merge, or release as part of the local documentation action.

## 6. Audit checkpoints / evidence locations

At the time of the original closure, local ignored evidence was reported at:

- `.tmp/evidence-v2-final-closure/` — broad-suite logs and exit, architecture/lint, Candidate and `.deb` manifests, Ubuntu apt migration/smoke/cleanup, Audit A/B verification.
- `.tmp/evidence-windows-v2-final/` — Windows 11 UIA, WER and guest acceptance.
- Tracked evidence includes `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` and the `build/audit/`, wave-report and workflow records.

An independent auditor should first test whether each raw local file exists, read it, parse its result, recompute recorded hashes from the referenced artifacts, and compare source identities. Missing ignored evidence is an evidence availability limitation, not a pass.

## 7. Change ledger completeness and exclusions

This document provides a complete **review index and reproducible inventory method**, not a hand-written description of all 972 path entries. The exact path inventory, endpoint diff, commit graph and V2 PR list can be regenerated from the refs in §1. Historical audit reports and wave verdicts may be stale, superseded, or removed at the current endpoint; preserve their date/SHA context. Current acceptance status comes from the final report/TODO plus the raw evidence, after independent verification.

## 8. Reproduction commands

Run in a read-only checkout after fetching `origin` (fetch updates refs; do not change working files):

```powershell
git status --short --branch
git show -s --format="%H %ad %s" --date=iso-strict origin/main origin/develop
git merge-base --all origin/main origin/develop
git rev-list --left-right --count origin/main...origin/develop
git diff --stat origin/main origin/develop
git diff --name-status origin/main origin/develop
git log --first-parent --format="%H %ad %s" --date=iso-strict origin/main..origin/develop
git log --first-parent --format="%H %ad %s" --date=iso-strict origin/develop -n 20
git diff --quiet e41cb02613b6bad32c41480a88308750bd05ce15 origin/develop -- src build
```

The last command exits `0` if `src/` and `build/` have no endpoint changes after the recorded product source SHA. `git diff --name-status` is the exhaustive changed/added/deleted path ledger. Do not use `git diff A...B` as the endpoint tree comparison here because of the multiple merge bases.
