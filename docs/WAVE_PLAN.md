# TRUBAGUI CLI Wave Plan

Last updated: 2026-08-02

This plan orders the 58 unchecked items in `TODO.md` by dependency, security
risk, and release impact. Per `rules.md`, only one wave may be active at a time.
No implementation task may be taken from a later wave before the active wave's
exit gate is satisfied.

Local execution uses nine independent manifests under `waves/waiting/`. One
master-prompt invocation selects only the lexically first manifest, processes
its Flash-sized packets in order, and stops. After every packet verdict and the
wave exit gate pass, Codex uses `tools/ai/wave-queue.ps1` to move that manifest
to `waves/done/`; it never starts the next wave in the same invocation. The
manager enforces an exclusive claim token, ordering, recovery, verdict schemas,
capacity ceilings, and guarded archival. The entire `waves/` queue is
intentionally Git-ignored, while this document and canonical manifests under
`tools/ai/wave-templates/` remain recoverable repository sources.

## Language policy

- OpenCode task files, orchestration prompts, technical explanations, progress
  reports, review reports, test reports, and new CHANGELOG entries must be
  written in English.
- Historical CHANGELOG entries are not rewritten merely for consistency.
- Product-visible strings continue to be maintained in both Turkish and English.
- The separate Turkish and English user guides required by `TODO.md` remain in
  scope; this policy does not remove bilingual product documentation.

## Priority and status

| Priority | Wave | Status | Primary outcome |
|---|---|---|---|
| P0 | Wave 1 — CLI contracts and current-state audit | WAITING | Stable contracts for all later commands |
| P0 | Wave 2 — Profile lifecycle and session security | QUEUED | Safe and complete profile management |
| P1 | Wave 3 — File contracts and conflict policy | QUEUED | Predictable file and transfer behavior |
| P1 | Wave 4 — Detailed diagnostics and SFTP smoke | QUEUED | Stage-based diagnostics and JSON evidence |
| P1 | Wave 5 — Read-only jobs commands | QUEUED | Low-risk scheduler visibility |
| P1 | Wave 6 — Submit and cancel commands | QUEUED | Confirmation-gated mutating operations |
| P2 | Wave 7 — Local release gates | QUEUED | Automated EXE and transfer verification |
| P2 | Wave 8 — Documentation and maintenance policy | QUEUED | Complete CLI documentation and upkeep rules |
| BLOCKED | Wave 9 — Live-cluster release verification | USER AUTHORIZATION | Live verification with an isolated account |

## OpenCode and DeepSeek execution contract

Every `DS-*` card is a separate bounded task. Never pass an entire wave to one
DeepSeek call.

1. Codex verifies that the card is still valid against repository evidence.
2. DeepSeek `analyze` performs read-only discovery.
3. Codex fixes the allowed files, forbidden scope, acceptance criteria, and
   targeted checks.
4. DeepSeek `implement` runs only in a clean sibling worktree and only for one
   card. The primary or a dirty worktree is never used.
5. Codex inspects the full status and diff and rejects unrelated changes.
6. DeepSeek `review` examines the same bounded sibling-worktree diff.
7. Codex independently reruns targeted tests and authoritative project gates.
8. Only Codex updates final documentation, stages, commits, or hands off work.

DeepSeek must never perform live remote or cluster operations, access sensitive
stores or material, deploy, publish, or manipulate Git history. Product,
architecture, security, authorization, schema, migration, provider, release,
and live-operation decisions remain with Codex or the user.

The complete wave file must not be supplied as a worker task file. Each call
uses a small English task file containing only one card and phrased so it passes
the worker's safety validation without weakening that validation.

## TODO coverage map

| TODO area | Open items | Owning card or gate |
|---|---:|---|
| Shared exit-code contract | 1 | DS-01B |
| Profile lifecycle and authentication | 10 | DS-02A, DS-02B, SEC-02C |
| Detailed diagnostics and SFTP smoke | 11 | DS-04A, DS-04B |
| Read-only file metadata and error contract | 2 | DS-01C |
| Turkish file and folder names | 1 | DS-03B |
| Existing-file transfer policy | 1 | DS-03A |
| Jobs commands and shared output/safety behavior | 10 | DS-05A, DS-05B, DS-06A, DS-06B |
| GUI/CLI parity and per-command quality gates | 8 | Definition of Done, DS-08B |
| Release and packaging verification | 8 | DS-07A, DS-07B, Wave 9 |
| Documentation and maintenance | 6 | DS-08A, DS-08B |
| **Total** | **58** | **Complete coverage** |

## DeepSeek v4 Flash sizing policy

Every delivery packet is sized for one focused OpenCode DeepSeek v4 Flash turn
and one reviewable diff.

| Size | Maximum intended scope | Use |
|---|---|---|
| Audit | No changed files | Repository mapping and evidence only |
| Small | Up to 3 files and about 200 changed lines | One contract tail, one command, or one test matrix |
| Medium | Up to 5 files and about 400 changed lines | One cohesive command pair or orchestration slice |
| Reserved | No DeepSeek delivery | Policy, authorization, or live-operation work |

These are hard planning ceilings, not targets. If repository evidence indicates
that a packet will cross either ceiling, Codex must split it before the worker
call. DeepSeek must not broaden the packet, combine neighboring packets, or use
a large refactor to stay within the line estimate.

## DeepSeek delivery packet matrix

| Packet | Wave | Size | Estimated files | Estimated changed lines | Delivery authority |
|---|---:|---|---:|---:|---|
| DS-01A | 1 | Audit | 0 | 0 | Analyze only |
| DS-01B | 1 | Medium | 3–5 | 200–300 | Implement and review |
| DS-01C | 1 | Medium | 5 | 200–300 | Implement and review |
| DS-02A | 2 | Medium | 2–3 | 150–300 | Implement and review |
| DS-02B1 | 2 | Small | 2–3 | 100–200 | Implement and review |
| DS-02B2 | 2 | Small | 2–3 | 50–150 | Implement and review |
| SEC-02C | 2 | Reserved | 0 | 0 | Analyze/review only; Codex owns any change |
| DS-03A | 3 | Medium | 2–3 | 150–300 | Implement and review |
| DS-03B | 3 | Small | 2 | 100–200 | Implement and review |
| DS-04A | 4 | Medium | 2–3 | 150–300 | Implement and review |
| DS-04B1 | 4 | Medium | 2–3 | 150–250 | Implement and review |
| DS-04B2 | 4 | Small | 2–3 | 100–200 | Implement and review |
| DS-05A1 | 5 | Small | 2–3 | 100–200 | Implement and review |
| DS-05A2 | 5 | Medium | 2–3 | 150–250 | Implement and review |
| DS-05B | 5 | Medium | 2–3 | 150–300 | Implement and review |
| DS-06A | 6 | Medium | 2 | 100–250 | Implement and review |
| DS-06B | 6 | Medium | 2 | 100–250 | Implement and review |
| DS-07A | 7 | Small | 2–3 | 50–150 | Script diff only; Codex executes EXE |
| DS-07B | 7 | Medium | 3–4 | 100–250 | Implement and review |
| DS-08A1 | 8 | Small | 1–2 | Up to 200 | Draft and review |
| DS-08A2 | 8 | Medium | 1–2 | Up to 300 | Draft and review |
| DS-08A3 | 8 | Medium | 1–2 | Up to 300 | Draft and review |
| DS-08B | 8 | Small | 2–3 | 100–200 | Draft and review |
| LIVE-09 | 9 | Reserved | 0 | 0 | User and Codex only |

## Auditable evidence-log protocol

Every OpenCode call must keep logs. `-NoLogs` is forbidden for wave execution.
The caller supplies `-Wave <WAVE_ID>` and `-Card <PACKET_ID>` to the project
worker. Each call produces an immutable run directory under `.agent-runs/`:

```text
.agent-runs/<timestamp>-<mode>/
  request.md
  stdout.log
  stderr.log
  metadata.json
```

`metadata.json` must contain the schema version, run ID, wave, card, mode,
discovered model, OpenCode version, worktree, starting and ending Git heads,
start/end timestamps, duration, raw child exit code, effective worker exit code,
whether a model response was present, any wrapper failure message, timeout state,
the effective timeout budget, log paths, and changed-path and diff-statistic keys that are non-null only for
implement mode. Read-only runs must record those change fields as `null` rather
than attributing pre-existing primary worktree changes to DeepSeek.

DeepSeek v4 Flash calls use generous mode defaults: analyze 20 minutes,
implement 30 minutes, review 20 minutes, and smoke-test 10 minutes. A packet may
raise its budget explicitly when repository evidence justifies it, up to the
worker's 120-minute hard ceiling. A timeout always produces a failed run record;
Codex may retry only after inspecting the preserved logs and deciding whether
the packet should be narrowed or the explicit budget increased.

Codex verifies every run directly from these files. A packet cannot pass when:

- `childExitCode` is missing or non-zero;
- `workerExitCode` is non-zero or `responsePresent` is false;
- the recorded model is not the discovered approved model;
- wave/card identity differs from the selected packet;
- analyze or review metadata claims attributable file changes;
- implement changed paths exceed the packet's allowed files or size ceiling;
- stdout claims a test passed without a matching observed command outcome;
- stderr contains an unresolved failure;
- the recorded worktree or Git head is not the one Codex inspected.

After independent verification, Codex records a packet-level verdict at:

```text
.agent-runs/evidence/<wave>/<packet>/verdict.json
```

The verdict references every related analyze, implement, and review `runId` and
contains: `verdict`, `verifiedBy`, `verifiedAt`, `allowedPaths`, `observedPaths`,
`diffStat`, `testsRun` with command/exit code/outcome, `evidenceFiles`, review
findings and resolutions, remaining uncertainty, and the next permitted packet.
DeepSeek never authors or changes `verdict.json`.

Every wave-packet verdict also includes a machine-readable `capacity` object.
The queue manager requires the manifest size and exact ceilings
(`Audit`/`Reserved` 0 files and 0 lines, `Small` 3 and 200, `Medium` 5 and 400),
observed file and changed-line counts, and `withinLimit: true`. Missing,
inconsistent, or over-limit capacity evidence blocks verification and archival.

Queue state changes only through:

```powershell
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action recover
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action audit
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action claim
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action verify -ClaimToken <TOKEN>
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action complete -ClaimToken <TOKEN> -CompletionNote <ENGLISH_CLOSEOUT>
```

Manual status edits or waiting-to-done moves are invalid and detected by
`audit`. Interrupted work resumes with the same owner/token or is explicitly
released after Codex investigation. Wave 9 additionally requires an explicit
authorization note when claimed.

Worker metadata and primary verdict files follow
`tools/ai/run-metadata.schema.json` and
`tools/ai/packet-verdict.schema.json`, respectively.

Each packet needs one successful analyze run, one successful implement run when
delivery is allowed, and one successful review run against the final diff. If
the diff changes after review, the verdict must reference a later successful
review run. Audit-only and reserved packets record the applicable subset and an
explicit reason.

## Definition of Done for every card

- New commands include help text and stable text and JSON contracts.
- Reusable behavior stays in the service layer; UI and CLI handlers remain thin.
- Remote behavior is verified through fake or mock backends only.
- Error handling preserves actionable stderr and exit-code information without
  exposing sensitive data.
- At least one unit test and, when appropriate, an integration or smoke test is
  present.
- The related release-checklist impact is evaluated.
- New product-visible strings update Turkish and English resources together.
- Targeted tests, `python scripts/check_i18n.py`, `git diff --check`, and
  `git status --short` are run with actual outcomes recorded. PowerShell
  source-tree checks set `$env:PYTHONPATH = "src"`.
- TODO items are closed only after behavior and test evidence are observed.
- Technical reports and new CHANGELOG entries are written in English.

---

## Wave 1 — CLI contracts and current-state audit

**Status:** WAITING — becomes ACTIVE only when selected as the first local queue file

**Priority:** P0

**Goal:** Stabilize exit-code, JSON, error, timeout, and verbosity contracts and
reconcile `TODO.md` with behavior already present in the repository.

### DS-01A — Audit unchecked items

**Type:** DeepSeek analyze followed by Codex verification. No source change.

**Scope:** `TODO.md`, `src/hpc_gui/cli/`, related services, and
`tests/test_cli.py`.

**Output:** Classify each unchecked item as `missing`, `partial`,
`implemented-tests-missing`, or `complete`, with file and line evidence.

**Acceptance:** Independently verify profile selection, key-path handling,
stdin-based secret input, host-key policy, timeout, verbosity, and file JSON
metadata. No TODO checkbox changes without evidence.

### DS-01B — Exit-code and shared error contract

**Type:** DeepSeek implement and review after Codex approves numeric values.

**Allowed:** `src/hpc_gui/cli/`, narrow CLI tests, and the CLI contract docs.

**Forbidden:** UI, live remote calls, persistence-schema changes, release output.

**Acceptance:** Success, usage/confirmation refusal, connection, operation, and
timeout failures have one mapping; text and JSON errors are tested; diagnostics
from stderr are retained.

**Checks:**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_cli.py -q
python -m hpc_gui --format json version
python -m hpc_gui doctor environment
git diff --check
git status --short
```

### DS-01C — Existing flags and file JSON completion

**Type:** DeepSeek implement and review.

**Scope:** Verify the already-checked timeout and verbosity TODO claims first and
implement only an evidence-backed gap; complete size, mtime, type, and
permissions in `files stat`; standardize empty-directory, access, and not-found
outcomes.

**Acceptance:** Flags have mock-observable effects; `files ls` and `files stat`
use consistent metadata names; errors follow the Wave 1 contract.

**Checks:** Extend `tests/test_cli.py` with fake-session timeout, verbosity,
metadata, and error matrices; run `python -m pytest tests/test_cli.py -q`.

**Exit gate:** The audit matrix is approved, contracts are documented and tested,
and later waves can reuse one stable error and JSON model.

---

## Wave 2 — Profile lifecycle and session security

**Status:** QUEUED

**Priority:** P0

**Dependency:** Wave 1.

### DS-02A — Profile CRUD

**Type:** DeepSeek implement and review.

**Scope:** `profile create`, `profile update`, and confirmation-gated deletion,
using existing `config/storage.py` helpers and round-trip tests.

**Allowed:** `src/hpc_gui/cli/`, a narrowly justified `config/` helper, and
`tests/test_cli.py`.

**Forbidden:** GUI profile flows, a new persistence format, or plaintext
sensitive-value storage.

**Acceptance:** Updates preserve unspecified fields; deletion requires explicit
confirmation; list/show never expose sensitive fields; no sensitive-value
command-line argument is introduced.

### DS-02B — Profile selection and connection test

**Type:** DeepSeek implement and review with fake sessions only.

**Scope:** `profile test NAME`, consistent `--profile NAME` support across remote
commands, and tests for existing key-path and strict/accept-new behavior without
reimplementing it.

**Allowed:** `src/hpc_gui/cli/`, `tests/test_cli.py`, and only when justified
`tests/test_optional_ssh_credentials.py`.

**Forbidden:** A parallel connection implementation, GUI profile flows, or live
connections.

**Acceptance:** One profile-resolution path; standard not-found exit behavior;
PASS/FAIL JSON from the test command; no live connection.

**Checks:** Fake `CLISession` profile matrix, `python -m pytest
tests/test_cli.py -q`, and `python -m unittest
tests/test_optional_ssh_credentials.py`.

**Flash-sized subpackets:**

- **DS-02B1:** `profile test NAME`, common profile selection, not-found behavior,
  and fake-session JSON results; Small.
- **DS-02B2:** Evidence-first verification and regression tests for existing
  key-path and strict/accept-new behavior; Small. It may deliver code only for a
  gap proven by DS-01A.

Do not combine DS-02B2 with SEC-02C.

### SEC-02C — Stored-secret resolution policy

**Owner:** Codex. DeepSeek may only analyze or review masked fixtures without
making policy decisions.

**Scope:** Safe use of the existing Windows protection/store flow, stdin input,
rejection of command-line sensitive values, and actionable non-Windows behavior.

**User decision:** Whether an interactive prompt is supported. The recommended
default is stdin-only.

**Exit gate:** The profile lifecycle is tested, logs and output do not leak
sensitive data, and all remote commands share one profile-resolution path.

---

## Wave 3 — File contracts and conflict policy

**Status:** QUEUED

**Priority:** P1

**Dependencies:** Wave 1; Wave 2 when profile-based verification is required.

### DS-03A — Existing-file policy

**Type:** DeepSeek implement and review.

**Scope:** Explicit upload/download choices for overwrite, skip, rename, and
resume, reusing the existing backend resume behavior.

**Allowed:** `src/hpc_gui/cli/files.py`, `cli/main.py`, a narrowly justified
file-service helper, and tests.

**Forbidden:** Changes to the GUI conflict dialog, silent overwrite, live
transfers.

**Acceptance:** All four policies have documented text/JSON outcomes; rename
never overwrites; skip reports a no-op; verification interaction is tested.

### DS-03B — Unicode and error matrix

**Type:** DeepSeek implement and review.

**Scope:** Turkish file/folder names and regression coverage showing that they
preserve the metadata and error contract established by DS-01C. DS-03B inherits
that contract and does not redefine its standard mappings.

**Allowed:** CLI files, existing backend test doubles, and narrow tests.

**Forbidden:** Live remote directories, production data, UI changes.

**Acceptance:** Turkish names remain intact in text/JSON; errors use Wave 1 exit
codes; an empty directory is a successful empty result.

**Checks:** `tests/test_cli.py` plus existing local file/backend tests.

**Exit gate:** File commands expose a loss-averse conflict policy and consistent
error and JSON behavior.

---

## Wave 4 — Detailed diagnostics and SFTP smoke

**Status:** QUEUED

**Priority:** P1

**Dependencies:** Waves 1 and 2.

### DS-04A — Stage-based connection diagnostics

**Type:** DeepSeek implement and review using fake behavior only.

**Scope:** Report port reachability, connection/authentication, SFTP subsystem,
and remote checksum-tool availability as separate fields.

**Allowed:** `src/hpc_gui/cli/`, a narrowly justified diagnostics service, and
`tests/test_cli.py`.

**Forbidden:** Live network calls, sensitive stores, UI changes.

**Acceptance:** One stage failure does not erase other results; text/JSON expose
the same stages; no sensitive data appears.

**Checks:** A fake-session matrix failing each stage independently;
`python -m pytest tests/test_cli.py -q`.

### DS-04B — SFTP smoke orchestration

**Type:** DeepSeek implement and review; no live remote call.

**Scope:** Temporary test directory, upload, listing, download, SHA-256
verification, optional cleanup, and JSON result output using a fake backend.

**Allowed:** CLI files, the existing `FilesBackend` test double, and one narrow
smoke-test file when needed.

**Forbidden:** Live calls, user directories, persistent test data, release
scripts.

**Acceptance:** Each stage reports PASS/FAIL and diagnostics; cleanup is
reported; partial failure still writes an artifact; no production path is
assumed.

**Checks:** Fake-backend success and per-stage failure matrices plus temporary
artifact validation.

**Flash-sized subpackets:**

- **DS-04B1:** Command surface and fake-backed temporary-directory, upload,
  listing, and download stages; Medium.
- **DS-04B2:** Checksum comparison, optional cleanup, partial-failure JSON, and
  artifact tests built on DS-04B1; Small.

Each subpacket has its own analyze/implement/review run IDs. DS-04B2 must reuse
DS-04B1 rather than refactor its command surface.

**Exit gate:** Deterministic smoke JSON is produced locally. Live execution is
deferred to Wave 9.

---

## Wave 5 — Read-only jobs commands

**Status:** QUEUED

**Priority:** P1

**Dependencies:** Waves 1 and 2 and the shared scheduler service.

### DS-05A — `jobs list` and `jobs status`

**Type:** DeepSeek implement and review with a mock backend.

**Scope:** Reuse the existing scheduler service, structured record parsing,
text/JSON output, preservation of stderr and remote exit codes, and the shared
jobs-output helper that later jobs packets must reuse.

**Allowed:** `src/hpc_gui/cli/`, `src/hpc_gui/__main__.py` for top-level jobs
dispatch, a narrowly justified parser service, `tests/test_cli.py`, and
`tests/test_slurm_ssh.py`.

**Forbidden:** Jobs UI, live cluster access, new provider or resource policy.

**Acceptance:** Help, text/JSON, and error contracts are tested; CLI code does
not compose remote command text; mock calls and arguments are asserted.

**Flash-sized subpackets:**

- **DS-05A1:** Top-level `jobs` dispatch, parser/output foundation, and shared
  text/JSON/stderr helper; Small.
- **DS-05A2:** `jobs list` and `jobs status` behavior and mock-backed tests using
  DS-05A1; Medium.

DS-05A2 may extend the foundation but must not replace it or absorb DS-05B.

### DS-05B — `jobs accounting` and `jobs lssrv`

**Type:** DeepSeek implement and review with a mock backend.

**Scope and boundaries:** The same allowed and forbidden scope as DS-05A.

**Acceptance:** All four read-only commands have help, text/JSON, and error
tests and interpret service output without duplicating command composition.

**Checks:** `python -m pytest tests/test_cli.py -q` and
`python -m unittest tests/test_slurm_ssh.py`.

**Exit gate:** The complete read-only jobs surface is proven with mocks and has
no mutating operation.

---

## Wave 6 — Submit and cancel commands

**Status:** QUEUED

**Priority:** P1

**Dependency:** Wave 5.

### DS-06A — Submit

**Type:** DeepSeek implement and review using fake behavior only.

**Scope:** `jobs submit SCRIPT`, mandatory `--yes`, shared service use, text/JSON
results, and stderr/exit-code preservation.

**Allowed:** CLI, the existing scheduler service, and narrow CLI/service tests.

**Forbidden:** Live submission, UI, invented partition/account/resource values.

**Acceptance:** Without `--yes`, the backend is not called; fake success/failure
is tested; the script path is safely passed to the service.

### DS-06B — Cancel

**Type:** DeepSeek implement and review using fake behavior only.

**Scope:** `jobs cancel JOB_ID`, mandatory `--yes`, safe job-ID validation, and
log redaction.

**Forbidden:** Live cancellation, invented scheduler policy, command composition
in UI or CLI.

**Acceptance:** No backend call without `--yes`; special-character input is
handled safely; diagnostics remain actionable.

**Checks:** CLI tests for confirmation and input rejection plus
`tests/test_slurm_ssh.py`.

**Exit gate:** Both mutating commands are confirmation-gated, mock-tested, and
follow shared exit-code and JSON contracts.

---

## Wave 7 — Local release gates

**Status:** QUEUED

**Priority:** P2

**Dependencies:** Wave 4 and the final CLI surface from Waves 5–6.

### DS-07A — Packaged-EXE CLI smoke

**Type:** DeepSeek implements and reviews only the release-script diff. Codex
builds the EXE and executes smoke commands.

**Scope:** Run `--help`, `version`, and `doctor environment` against the release
EXE and stop artifact production on failure.

**Allowed:** `scripts/release_smoke.ps1`, narrowly justified
`scripts/release.ps1` changes, and script tests.

**Forbidden:** DeepSeek package execution, publishing, version changes, or
overwriting artifacts.

**Acceptance:** Any non-zero command stops the script; stdout/stderr remain
available; Codex records actual exit codes from a clean build.

### DS-07B — Local transfer and JSON artifact gate

**Type:** DeepSeek implement and review.

**Scope:** A disposable local fixture, Turkish-name transfer gate, Wave 4 smoke
JSON in the version folder, and English checklist/CHANGELOG test records.

**Ownership boundary:** DS-04B produces the smoke-result schema and local JSON;
DS-07B only validates and places that existing artifact in the canonical release
folder. It must not define a second schema.

**Allowed:** Release scripts, the local transfer-test script, and the production
checklist.

**Forbidden:** Live cluster access, release-layout changes, deployment,
publication, or overwriting an existing version.

**Acceptance:** Every gate stops the release on failure; JSON lands under
`dist/releases/v<version>/`; Turkish-name transfer is mandatory.

**Exit gate:** Release verification is fully local and reproducible.

---

## Wave 8 — Documentation and maintenance policy

**Status:** QUEUED

**Priority:** P2

**Dependency:** Waves 1–7.

### DS-08A — Turkish and English CLI guides

**Type:** DeepSeek drafts; Codex performs final editing and verification.

**Scope:** Root README command summary, complete Turkish and English CLI guides,
exit codes, text/JSON behavior, confirmation flags, and safe-use examples.

**Allowed:** `README.md` and the single canonical documentation directory chosen
by Codex.

**Forbidden:** Runtime code and unverified example output.

**Acceptance:** Every parser command appears in both guides; examples match the
actual help surface; both guides cover the same topics.

**Flash-sized subpackets:**

- **DS-08A1:** Root README command inventory and links only; Small.
- **DS-08A2:** Turkish CLI guide using the verified inventory; Medium.
- **DS-08A3:** English CLI guide using the same inventory and section topology;
  Medium.

Each subpacket receives its own analyze/draft/review cycle. Do not draft both
language guides in one DeepSeek call.

### DS-08B — Maintenance and GUI/CLI parity process

**Type:** DeepSeek drafts; Codex performs final editing.

**Scope:** CLI-counterpart evaluation for new GUI actions, shared-service use,
GUI-only rationale, help/JSON/unit/smoke/release gates, TODO-to-CHANGELOG flow,
and refusal to release untested remote operations.

**Language:** Orchestration, technical explanations, progress/review reports,
and all new CHANGELOG entries are English. Product UI and paired user guides
remain bilingual.

**Forbidden:** Claiming an unrun live test passed, runtime changes, or rewriting
historical CHANGELOG records.

**Checks:** Parser-to-document scan, link checks, TODO/CHANGELOG/checklist cross
scan, `python scripts/check_i18n.py`, and `git diff --check`.

**Exit gate:** README covers every command; Turkish and English guides have equal
scope; maintenance rules are enforceable release-checklist items.

---

## Wave 9 — Live-cluster release verification

**Status:** USER AUTHORIZATION

**Priority:** BLOCKED UNTIL AUTHORIZED

**Owner:** User and Codex. DeepSeek may neither implement nor execute this wave.

**Scope:**

- Provision a dedicated SFTP release-test account through its owner.
- Prove through access design that the account cannot reach production data.
- After explicit user authorization, run upload, download, directory, and
  checksum verification.
- Store the English result record in release JSON, checklist, and CHANGELOG.

**Prerequisites:** Waves 4 and 7 complete; the target, test directory, cleanup
policy, and data isolation explicitly approved by the user.

**Acceptance:** Least-privilege account; production data out of scope; every
operation and cleanup result recorded; failure blocks release; no sensitive
value appears in logs or artifacts.

## Why this order

1. Contracts and a current-state audit prevent duplicated implementation and
   inconsistent exit-code or JSON behavior.
2. Profile and session safety are dependencies of all remote commands.
3. File and diagnostics work establish safe remote-operation patterns before
   jobs commands.
4. Jobs work is split into read-only and mutating waves to control risk and diff
   size.
5. Release gates become meaningful only after behavior stabilizes.
6. Documentation describes the final CLI surface; live-cluster verification
   waits for explicit authorization and external account provisioning.

## Complete unchecked-TODO execution ledger

This ledger gives every unchecked item a primary owner. Cross-cutting
Definition-of-Done gates and explicitly named reuse relationships still apply.

| ID | Unchecked outcome | Primary packet | Delivery note |
|---|---|---|---|
| T01 | Document the shared exit-code contract | DS-01B | Codex approves numeric values first |
| T02 | Add profile creation | DS-02A | Fake config round trip |
| T03 | Add profile update | DS-02A | Preserve unspecified fields |
| T04 | Add confirmation-gated profile removal | DS-02A | No action without confirmation |
| T05 | Add profile connection test | DS-02B1 | Fake session only |
| T06 | Make profile selection common to remote commands | DS-02B1 | One resolution path |
| T07 | Support private-key profile connection from CLI | DS-02B2 | Verify existing behavior before any gap work |
| T08 | Resolve a safely stored protected value through the existing flow | SEC-02C | Codex-owned security policy |
| T09 | Support stdin-based sensitive-value input | SEC-02C | Verify existing behavior first |
| T10 | Reject sensitive values as command-line arguments | SEC-02C | Policy and regression test |
| T11 | Support strict and accept-new host policy | DS-02B2 | Verify existing behavior first |
| T12 | Report connection, port, and authentication stages separately | DS-04A | Fake per-stage matrix |
| T13 | Check SFTP subsystem availability | DS-04A | No live call |
| T14 | Check remote checksum-tool availability | DS-04A | No live call |
| T15 | Add the SFTP smoke command surface | DS-04B1 | Fake backend |
| T16 | Use a temporary remote test directory | DS-04B1 | Fake backend lifecycle |
| T17 | Verify smoke upload | DS-04B1 | Stage result recorded |
| T18 | Verify smoke directory listing | DS-04B1 | Stage result recorded |
| T19 | Verify smoke download | DS-04B1 | Stage result recorded |
| T20 | Verify smoke SHA-256 equality | DS-04B2 | Reuse DS-04B1 result model |
| T21 | Add optional smoke cleanup | DS-04B2 | Cleanup result is explicit |
| T22 | Produce smoke JSON for release reuse | DS-04B2 | Defines the single schema |
| T23 | Complete file size, mtime, type, and permissions JSON | DS-01C | Align list and stat fields |
| T24 | Test Turkish file and folder names | DS-03B | Preserve Wave 1 contracts |
| T25 | Standardize empty, access, and not-found outcomes | DS-01C | Shared error mapping |
| T26 | Add overwrite, skip, rename, and resume choices | DS-03A | Loss-averse policy matrix |
| T27 | Add jobs list | DS-05A2 | Uses DS-05A1 foundation |
| T28 | Add jobs status | DS-05A2 | Uses DS-05A1 foundation |
| T29 | Add jobs accounting | DS-05B | Read-only mock path |
| T30 | Add jobs lssrv | DS-05B | Read-only mock path |
| T31 | Add jobs submit | DS-06A | Fake backend and confirmation gate |
| T32 | Add jobs cancel | DS-06B | Fake backend and confirmation gate |
| T33 | Require confirmation for mutating jobs commands | DS-06A | Defines the shared gate; DS-06B reuses it |
| T34 | Return jobs results as text and JSON | DS-05A1 | Shared by Waves 5 and 6 |
| T35 | Preserve remote stderr and exit code | DS-05A1 | Shared output contract |
| T36 | Redact sensitive command parameters in logs | DS-05A1 | Shared safety contract |
| T37 | Evaluate a CLI counterpart for every new GUI action | DS-08B | Maintenance gate |
| T38 | Reuse the same service when a CLI counterpart exists | DS-08B | Architecture gate |
| T39 | Record rationale for GUI-only actions | DS-08B | TODO maintenance rule |
| T40 | Add help text for every new CLI command | Definition of Done | Enforced per packet |
| T41 | Add a JSON contract for every new CLI command | Definition of Done | Enforced per packet |
| T42 | Add a unit test for every new CLI command | Definition of Done | Enforced per packet |
| T43 | Add integration or smoke coverage for every new CLI command | Definition of Done | Enforced per packet |
| T44 | Update the related release-checklist item | DS-08B | Definition of Done enforces it per packet |
| T45 | Run help and version against the release EXE | DS-07A | Codex executes the EXE |
| T46 | Run doctor environment against the release EXE | DS-07A | Codex executes the EXE |
| T47 | Provision a dedicated live release-test account | LIVE-09 | User authorization required |
| T48 | Run live upload, download, directory, and checksum verification | LIVE-09 | User authorization required |
| T49 | Prevent the live test account from reaching production data | LIVE-09 | Access design required |
| T50 | Place smoke JSON in the release folder | DS-07B | Consumes DS-04B2 schema |
| T51 | Record test results in checklist and CHANGELOG | DS-07B | New entries in English |
| T52 | Make Turkish-name release transfer a mandatory gate | DS-07B | Disposable local fixture |
| T53 | Add every CLI command to the root README | DS-08A1 | Verified command inventory |
| T54 | Add the Turkish CLI guide | DS-08A2 | Same topology as English guide |
| T55 | Add the English CLI guide | DS-08A3 | Same topology as Turkish guide |
| T56 | Move completed TODO items to CHANGELOG for each release | DS-08B | New records in English |
| T57 | Update this list for command or service changes | DS-08B | Maintenance rule |
| T58 | Block release of untested remote operations | DS-08B | Enforceable checklist gate |
