# WAVE 12 — Final Acceptance

Status: **WAVE_BLOCKED**. Code and global architecture work are complete and locally integrated through source commit `f6eb59c0bf20d6f5dd3015a0f7bcb258c79fd913`. Release acceptance remains blocked by Ubuntu wxPython absence and unresolved Windows portable/UI/SFTP results. Terminal verdict: **INTEGRATION_CODE_COMPLETE_ACCEPTANCE_BLOCKED**.

## Source identity

- Jobs source SHA: `713949fb752b90601e007812ebf2bd765da5ad52`.
- V2 source SHA: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.
- Integrated source commit/tree: `f6eb59c0bf20d6f5dd3015a0f7bcb258c79fd913` / `450c1d0ddb079122d5aa3efc90516bead03f0797`.
- Source fingerprint SHA-256: `bbfbbfad02d5d3b0a2ae7acd143c49ae62349b8136b1bf766c7bd85f729bdbef`, covering 1,516 tracked files (23,440,549 bytes).
- Ubuntu-Test r33 Git snapshot commit: `0ad0542918b49a4039db41c27ff62e2ab4c86ea1`. The final architecture JSON preserves the VM `source_commit` and records the corresponding local integration SHA/tree/fingerprint separately.
- Windows W15 source manifest SHA-256: `72d5333de0d59dd6a5bc4f0d2e7036d359d8bb24a06d96acc516e8fd1315d86a`; test file SHA-256 `d9511a924bc76601b4a63baafe4f5aa02361758a4c6e13be13152363593b38e6`.
- Windows terminal bridge run `e404c71b7f3c40069b7efb5d2d984006` used the same source manifest SHA-256. Its source hashes were verified equal between host and guest before launch.
- WAVE 12 code commits: `e888745396bab2a9c3f1be8e4333fab729ede79f` (localized connection status assertions) and `f6eb59c0bf20d6f5dd3015a0f7bcb258c79fd913` (remove unused screenshot DC objects).

## Final gates

| Gate | Result | Evidence / limit |
|---|---|---|
| Source identity | PASS | Source commit/tree/fingerprint above; Jobs/V2 SHAs recorded |
| Global architecture | PASS | Ubuntu-Test r33: 1,015 Python files, 0 over 500, 0 dependency errors, 0 cycles, 0 public API errors |
| Shared LOC gate | PASS | 1,041 source entries; 0 over-limit; 91 warning-band entries; baseline removed |
| Ruff | PASS | Ubuntu-Test r33: `ruff check src scripts tests tools`, exit 0 |
| Compileall | PASS | Ubuntu-Test r33: `compileall -q src/hpc_gui scripts tests tools`, exit 0 |
| i18n | PASS | Ubuntu-Test r33 check, exit 0 |
| Focused architecture/docs/Qt/provenance regressions | PASS | Ubuntu-Test r33: 41 passed, exit 0 |
| Ubuntu acceptance runner | BLOCKED_ENVIRONMENT | 2,639 passed, 0 failed assertions, 210 skipped, 61 deselected, 29 subtests passed; exit 5 because 105 wx-only partitions had no runnable tests without wxPython |
| Ubuntu wheel packaging | PASS | 1 passed, 3 deselected, exit 0 after installing the missing `build` dependency in the VM venv |
| Linux release package plan | PASS (plan only) | AppImage/deb/Flatpak dry-run validation; no artifact built |
| Windows W15 connection/startup | PASS | Windows11 r33: 11 passed, exit 0; assertions now verify controller state and exact localized status |
| Windows full portable suite | BLOCKED_TIMEOUT | Windows11 r28 run `7ad295fc24b14163adf32c241c49eed1`, 2,700-second timeout, exit `-1`, owned process tree stopped |
| Windows download-cancel SFTP | FAIL / unresolved | Full run isolated suite reported 2 passed / 2 failed: resume observed a dropped Paramiko connection; skip saw no progress. Ubuntu r30 same file passed 4/4. Later Windows attempt did not collect because its task environment lacked PySide6 |
| Windows terminal bridge | BLOCKED_TIMEOUT / unresolved | Windows11 run `e404c71b7f3c40069b7efb5d2d984006`, 600-second timeout, exit `-1`, owned process tree stopped. Guest stdout contained `.F` but no pytest summary or failure traceback; one pass and one failure marker were emitted before hang. Do not count this as a passing run |
| Windows task executable resolution | ENVIRONMENT ERROR | Full portable task could not resolve `powershell.exe` for updater test and `git` for docs/Qt-removal tests; no full retry with corrected task PATH was completed |
| Windows/Linux release artifacts | NOT RUN | No source-matched release package/artifact built |
| GitHub Actions | NOT RUN | No hosted workflow result |

## VM test execution

- Ubuntu-Test r30 ran `scripts/release_test_suite.py --scope acceptance` to completion. The aggregate run reported 2,639 passed, 0 failed assertions, 210 skipped, 61 deselected, and 29 passed subtests. Its exit code was 5 because wx-only partitions skipped without wxPython; this run is not PASS.
- Ubuntu-Test r30 ran `tests/test_download_cancel_wire.py`: 4 passed, exit 0. No real HPC job or remote file deletion was used.
- Ubuntu-Test r33 ran the full architecture validator, Ruff, compileall, i18n, and 41 focused regressions on the updated source snapshot; each completed command exited 0. After the final report files were copied to the VM, `tests/test_docs_references.py` passed 2/2 with exit 0 after restoring the VM Git executable to `PATH` and setting `GIT_EXEC_PATH`. The first attempt failed before assertions because Git was not on that task PATH (exit 1).
- Windows11 r33 ran `tests/test_w15_fresh_user_startup.py`: 11 passed, exit 0. The earlier two failures were English-only assertions against correct Turkish text; the test now verifies exact translation and controller state.
- Windows11 r28 full portable acceptance timed out after 2,700 seconds. It included 2 SFTP failures, 2 old localization assertion failures, executable-resolution errors, and an incomplete terminal bridge partition result. The localization test failures were fixed and the targeted suite passed; the SFTP and bridge results remain unresolved.
- Windows11 r36 focused terminal bridge run timed out at 600 seconds after printing `.F`; no traceback or final pytest summary was captured. Host and guest source manifest and focused source hashes matched.
- A separate Windows SFTP invocation exited 2 before collection because that task environment lacked PySide6; it is an environment diagnostic and does not clear the SFTP failures.
- Qt editor tests under Ubuntu Xvfb/xcb had 3 focus assertion failures; rerunning with offscreen backend passed 14/14. The exploratory failures remain classified as backend-specific and are not counted as PASS.
- Expanded Ruff initially found three unused items in `tools/gen_updater_screenshots.py`. The unused import and unused DC objects were removed; final Ruff passed. The screenshot generator itself was not executed because it writes documentation images.

No Linux or Windows release artifact was built. GitHub Actions was not run. No remote branch, PR, or release was changed. Full release acceptance is not established.
