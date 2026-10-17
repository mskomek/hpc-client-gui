# Independent Audit Prompt — HPC Client GUI V2 (`main` → `develop`)

Use this prompt with [`V2_MAIN_TO_DEVELOP_CHANGE_LEDGER.md`](V2_MAIN_TO_DEVELOP_CHANGE_LEDGER.md) as the audit map. The ledger is an index and contains claims; it is **not** authoritative evidence. Independently inspect the repository, Git objects, tracked artifacts, raw test outputs, and package bytes. Do not assume any result in the ledger or final acceptance report is true until verified.

## Role and objective

Act as an independent release/acceptance auditor for HPC Client GUI V2. Determine whether the current `develop` state satisfies the documented **noninteractive** V2 acceptance scope relative to current `main`, and whether the evidence chain is internally consistent. Audit source behavior, tests/harness validity, platform execution, packages, security, architecture and provenance. Report only facts you can reproduce or directly verify.

You are not authorized to edit product files, alter evidence, change branch refs, install packages on shared/system environments, contact external systems, push, create/merge a PR, publish a release, or weaken any gate. Work read-only. Keep any scratch output outside the repository or under a clearly disposable audit directory that you do not mistake for supplied evidence. Never print credentials, tokens, SSH/session data, or terminal contents.

## Required starting identity and safety checks

1. Record UTC/local time, OS/environment, repository root, `git status --short --branch`, current HEAD, branch/upstream, and recent log.
2. Verify the exact refs before comparison:
   - expected `origin/main`: `063d83b523be377d4ef02dc8a61e2fdd15876ecc`
   - expected `origin/develop`: `8c53b3e68d3bd4fc5f44ed2d9ded19645e9bf585`
   If refs have advanced, record the new exact SHAs and repeat the endpoint audit against them; do not silently use this ledger's old refs.
3. Find all merge bases. Because this history has multiple merge bases, use `git diff origin/main origin/develop` for the endpoint tree comparison. Do not describe `origin/main..origin/develop` as a linear post-main history. Recompute graph counts, endpoint file inventory and endpoint diff statistics.
4. Preserve all pre-existing user files and changes. Do not run reset, clean, stash, forced checkout, or destructive cleanup. Never alter the main checkout to make the audit easier.
5. Confirm the V2 closure merge chain PR #41–#45 from Git objects and, when available read-only, GitHub metadata. Verify merge commits and the PR #45 test correction commit. Treat the chain as the final closure, not as the entirety of the long-lived main/develop delta.

## Audit procedure

### A. Ledger and scope integrity

- Review the ledger's endpoint facts and recompute them.
- Inspect `TODO_V2_REMAINING.md`, the final acceptance report, V2 baseline/specification, mandatory acceptance gates, relevant workflow files, canonical wave manifests/reports and current acceptance manifest.
- Distinguish requirements from historical status notes. Resolve contradictions using current specs, exact source refs and raw results. Identify stale dates, SHAs, candidate IDs, missing files and claims accidentally carried from older candidates.
- Build a requirement → implementation → test command → raw evidence → source/artifact SHA map. Include additions, modifications, deletions and moves from the endpoint diff. Group by responsibility, but preserve an exhaustive path inventory as a machine-readable attachment/output.
- Verify the relationship between reported tested product source `e41cb02613b6bad32c41480a88308750bd05ce15` and current `develop`. Confirm ancestry and independently verify the stated `src/` and `build/` tree equality after that SHA. A report/test-support commit does not automatically invalidate product bytes; prove which bytes were packaged and tested.

### B. Source and architecture

- Run the repository's canonical architecture gate and lint commands in a clean/read-only or disposable checkout, recording command, versions, exit code and exact source SHA. Do not invent a replacement gate.
- Inspect the changed code and its tests for behavior, security, lifecycle ownership, teardown, error handling and dependency direction. Verify first-party source/tests remain within 500 physical lines, excluding only named and justified generated/vendor files.
- Verify the web security policy still includes `script-src 'self'` and `connect-src 'none'`; reject `unsafe-eval`, added CDN/script origins, or a new unsafe network path.
- Review terminal IPC queue limits, ordering, ACK/retry/timeout behavior, malformed input, stale callbacks, reconnect, URL/history/log/file privacy, ANSI/Unicode/high-volume handling and native teardown. Do not expose real terminal text in audit output.
- Do not rerun lengthy tests until checking current process/job state and canonical harness instructions. Never start a duplicate active runner.

### C. Test and harness validity

- Independently inspect CI definitions, test selection, skip/deselect markers, xfail/skip use, mocks/fixtures, assertions and test ownership. Identify fake PASS conditions, swallowed errors, broad catches, process-alive-only checks, cleanup by forced kill, and tests that never assert the behavior named by their test ID.
- Verify the recorded Windows broad summary from its raw output and exit file: expected claim is `3052 PASS / 0 FAIL / 2 SKIP / 65 DESELECTED / 29 subtest PASS`, exit 0. Confirm this is the broad invocation, not a targeted rerun. Explain each skip and deselection and whether it is mandatory. Do not call isolated W37 success a broad pass.
- Verify W37's original WinError 5, root cause and correction. Ensure the test fix addresses path/read/replace race without production sleep/retry or weakened assertion, and confirm focused plus broad evidence targets the same source and test implementation.
- Verify Linux WebKitGTK/terminal, W19 native lifecycle, queue-boundary/performance/privacy and shared SSH/SFTP/Slurm/Jobs/Files/Terminal regression evidence against raw logs and exact commands. Mark synthetic throughput as synthetic; it is not a real-cluster soak.
- Check that test evidence has real exit codes, timestamps, environment/tool versions, exact command and output provenance. Recompute summary counts from machine output where feasible.

### D. Windows Candidate and Windows 11 guest

- Locate the exact immutable onedir Candidate. Recompute its SHA-256 and compare it with `77a82b273c97b0d6168fdd718509032a1f49d49f2e5a52e38582c5607c4f9216`. Verify the manifest binds the artifact to the build source and toolchain.
- Verify the recorded packaged smoke is 21/21 on the same bytes and includes a genuine application clean-shutdown assertion.
- Inspect canonical Windows 11 guest-runner evidence. Confirm GUI launch reached the intended main window, UIA exercised the claimed 22 visible controls, reconnect asserted a fresh expected session identity, WER query covers the test interval and correct executable identity, and clean shutdown used the application's normal close route without timeout/tree kill.
- Independently confirm host and guest EXE hashes match. Process exit alone is not GUI acceptance. A runner failure before app launch is a harness/environment limitation, not product PASS or FAIL.
- State which Windows interactive/manual tests are explicitly outside the noninteractive scope.

### E. Linux package and migration

- Locate the exact `.deb`, recompute SHA-256 and compare to `1eaeb425b8a52df14b33abc60960f686946142e001a9272d51ee9383d5c46892`; verify source identity, version, architecture, package control metadata, file listing and executable payload hash `309dd25c9fb3c61c28afdc2b367ee84fa463921c2e8e9e048d504b807dcb9e95`.
- Verify rootless extraction, CLI/version and GUI smoke evidence; for actual package migration inspect apt/dpkg history proving install → upgrade → rollback → installed-binary smoke → purge/cleanup. Distinguish the temporary version-only migration package from the release Candidate and verify payload bytes are identical where claimed.
- Confirm no cleanup evidence is represented as an install result, no privileged operation is claimed without raw authorized evidence, and final cleanup checks actually ran. Check dependency closure and metadata against the package spec.
- Check the V2 acceptance spec before evaluating AppImage/Flatpak. Do not add optional formats as acceptance gates. If mandatory, locate reproducible tooling/evidence or state a proven blocker.

### F. W04 supplied evidence and manifest consistency

- Read the specification that requires W04 and determine what the supplied evidence is, who owns it, and whether repository tooling can generate it.
- Verify the canonical path `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`, recompute its SHA-256 (`6c41e085a1ecaeaedf6261316ea483cccaafc9b3dbea2ba71bda313fc56d6ed5`) and inspect its 28 tests/probes. Search the whole repository and available local evidence/artifact stores for duplicate, stale or mis-referenced copies. Do not fabricate missing evidence.
- Cross-check source SHA, Candidate SHA, package manifest, guest evidence, Linux evidence, wave state, TODO, acceptance manifest and both audit reports. No stale Candidate or SHA may be passed off as current.
- Verify Audit A and Audit B are separately authored procedures with distinct checks and evidence. A second summary repeating the same evidence is not an independent audit.

## Verdict rules

Return exactly one terminal state and justify it:

- **`V2_ACCEPTED`** — every mandatory noninteractive gate passes on the bound source/artifacts; Windows broad has zero failures; Windows Candidate, guest GUI/UIA, reconnect, WER and clean shutdown pass; mandatory Linux package/migration gates pass; W04 is resolved; manifests agree; two genuinely independent audits pass. Explicitly list interactive/manual and real-HPC credential tests outside scope.
- **`V2_BLOCKED_EXTERNAL`** — only if every remaining unmet gate is proven to require an external credential, authorized privilege, supplied evidence or unavailable authorized infrastructure that this repository/harness cannot produce. Include the exact prerequisite and discovery performed. Do not use this for a repository, source, test or harness defect.
- **`V2_FAILED`** — a current source/test/harness/repository-owned defect remains, any mandatory gate fails, or integrity/provenance is unsound.
- **`V2_PENDING`** — only if the audit/execution was forcibly interrupted before a terminal determination; never use for convenience.

Do not convert FAIL to SKIP, weaken assertions, infer PASS from a report headline, transfer evidence across source/artifact identities without hash proof, or label runner kills as clean shutdown.

## Required audit output

Provide:

1. Terminal verdict and concise rationale.
2. Exact main/develop/source/Candidate/package/W04 identities and current worktree cleanliness.
3. A table: gate, requirement, exact evidence/command, source or artifact SHA, independent result, remaining issue.
4. Windows broad PASS/FAIL/SKIP/DESELECTED counts and focused W37 result as separate rows.
5. Windows guest GUI/UIA, reconnect, WER, shutdown, and host/guest hash-match results separately.
6. Linux package identity, metadata, installed smoke, install/upgrade/rollback/purge result separately.
7. W04 provenance and hash result.
8. Audit A and Audit B findings; disclose any non-independent overlap.
9. All unresolved findings with classification: product defect, test defect, harness defect, environment blocker, external dependency, or out-of-scope interactive test.
10. Reproduction commands, tool versions, durations and raw artifact locations. Include SHA-256 values, not only filenames.

Do not commit, push, merge, publish, or edit acceptance state during this audit.
