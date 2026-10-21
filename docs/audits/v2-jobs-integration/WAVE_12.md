# WAVE 12 — Final Acceptance

Status: **IN_PROGRESS; acceptance is not complete**. The source architecture and dependency gates passed on a final Ubuntu-Test r29 snapshot. Linux wx coverage is blocked by the VM environment. A full Windows11 portable release test is still running; release packaging and artifact acceptance have not been performed.

## Source identity

- Integrated source commit: `0ece0ad8fb52f028e9acf23bdc792dc6fd266fc0` on `codex/integration/v2-jobs-staged-20261021`.
- Local `develop` was fast-forwarded from `d91c84f1d784fd3391bf132a54134faef44e63c9` to this source commit with no conflicts. No remote mutation occurred.
- Ubuntu-Test r29 manifest fingerprint: `a2aae9badd57dc929844606342be468ffa62bdb0d604fd9501add61759fe4007`; manifest SHA-256: `af3d75bc8538b8d494d79bd80910816fe11feea802e8209c8f99fb1f925bcc1b`; archive SHA-256: `b36380f1c806aa54eb11d5e80c74c842ee78c0f212fc10aca8a1005ab1bdd2dc`.
- The VM lacked a Git executable. A temporary outside-repository adapter supplied a complete physical file inventory and a synthetic VM commit for the full-mode architecture scan. Its use is disclosed in `ARCHITECTURE_FINAL.json`; no source files were excluded through the adapter.

## Acceptance matrix

| Gate | Status | Evidence / limitation |
|---|---|---|
| Git source identity | PASS | Integration commit and VM manifest/archive hashes recorded above |
| Global 500-line architecture | PASS | Ubuntu-Test r29: 1,015 Python files, 0 over 500 |
| Imports, dependencies, public API, cycles | PASS | 0 errors across all four gates |
| Ruff | PASS | Ubuntu-Test r28, all `src scripts tests`; source Python unchanged in r29 |
| Python compileall | PASS | Ubuntu-Test r28, `src/hpc_gui scripts tests`; source Python unchanged in r29 |
| i18n | PASS | Ubuntu-Test r28: key, reference, and hardcoded UI text checks all passed |
| CLI / config / SSH / Jobs / Files / Outputs / plugin contracts | PARTIALLY VERIFIED | Covered by portable release main suite and earlier focused wave suites; see `TEST_MATRIX.md`. Windows native targeted batch passed 114 tests; plugin manager UI passed 12. |
| Qt GUI | PARTIALLY VERIFIED | Linux offscreen portable suite and Windows plugin UI batch passed; full cross-platform acceptance remains pending |
| wx GUI | BLOCKED_ENVIRONMENT on Ubuntu | `wxPython` unavailable; 101 isolated wx modules contained only skips and returned pytest exit 5. Windows11 targeted wx batch passed 114 tests; full portable result pending. |
| FTP transfer | PARTIALLY VERIFIED | Fake/mocked and portable tests ran; no destructive remote operations; complete release acceptance pending |
| Security regressions | PARTIALLY VERIFIED | Focused Windows connection/auth/host-key batch passed; full release acceptance pending |
| Release test runner | BLOCKED_ENVIRONMENT on Ubuntu; Windows pending | Ubuntu r28 combined counts: 2,639 passed, 206 skipped, 61 deselected, 29 subtests passed; no assertion failures; runner exit 5 because wx-only partitions could not collect runnable tests. Windows11 full portable run is running under interactive task `7ad295fc24b14163adf32c241c49eed1`. |
| Windows build and smoke | NOT RUN | No Windows artifact built from this source commit |
| Ubuntu/Linux package | NOT RUN | No Linux package built from this source commit |
| Artifact/source SHA match | SNAPSHOT VERIFIED; RELEASE ARTIFACT NOT VERIFIED | VM source archive and manifest hashes match; no release artifact exists to accept |
| GitHub Actions | NOT RUN | Local CI configuration updated, but hosted workflow has not executed |
| Final report and audit | IN PROGRESS | Architecture report and matrix are written; Windows run result still required |

Local VM results and GitHub Actions results are kept separate. No GitHub Actions check is marked PASS.

## Test execution summary to date

- Ubuntu-Test r29 full architecture validator: exit 0; 1,015 Python files; 0 LOC/import/API/cycle violations.
- Ubuntu-Test r29 architecture regressions: 7 passed, exit 0.
- Ubuntu-Test r28 quality: Ruff, compileall, and i18n each exit 0.
- Windows11 r27 focused wx/Qt/Jobs/Files batch: 114 passed, exit 0.
- Windows11 r28 plugin manager UI: 12 passed, exit 0; host and guest file hashes matched.
- Ubuntu-Test r28 portable release runner: 2,639 passed, 0 assertion failures, 206 skipped, 61 deselected, 29 subtests passed; overall exit 5 because 101 wx-only isolated partitions skipped for missing wxPython.
- Windows11 full portable release runner: pending.

The displayed counts are executed test results across separate runs, not deduplicated test cases. A skipped wx-only process is not counted as a pass. No failing assertion is hidden.

## Verdict

Current verdict: **INTEGRATION_CODE_COMPLETE_ACCEPTANCE_BLOCKED**. The source code and global architecture gate are complete and integrated locally. Full release acceptance cannot be claimed while the Windows full suite is pending, Ubuntu wxPython is unavailable, and new Windows/Linux release artifacts and GitHub Actions have not been verified.
