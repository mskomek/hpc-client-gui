# Final Integration Report

Current verdict: **INTEGRATION_PARTIAL**. WAVEs 00–04 are complete on isolated integration branch `codex/integration/v2-jobs-staged-20261021`. The latest source commit is `71ef960bb486cc821e1a79f969e5b58913841715`; local `develop` remains unchanged.

WAVE 04 replaced the 832-line config module with a 233-line facade and four responsibility-based modules, restored the hide-finished and SSH retry preferences missing from V2, and migrated the relevant tests to the canonical config-core patch points. Its focused config/profile/CLI/history/SSH suites passed 356 tests with one Windows/POSIX-semantic skip; wx settings/window-state tests passed 27/27 and the FTP sbatch-follow regression passed. Ruff, config compileall, the 93-symbol facade check, and the changed-source architecture gate passed.

The latest architecture gate at `71ef960b` scans 822 Python files and records 50 files over 500 lines, 2 inherited unresolved internal symbol imports, 8 inherited dependency cycles, and 0 public API errors. It reports no new LOC/import/API/cycle violations. WAVE 05–12, zero-over-limit architecture, full release acceptance, Windows11 guest acceptance, Ubuntu/Linux packaging, artifact identity, and GitHub Actions remain pending. No remote branch, PR, or release was modified.

`develop` is checked out in a separate worktree and was not modified. WAVE 04 is committed only on the isolated integration branch; all successful wave commits remain pending a safe local develop merge after the remaining work.
