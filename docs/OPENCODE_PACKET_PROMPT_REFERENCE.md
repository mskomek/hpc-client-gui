# OpenCode DeepSeek v4 Flash Wave Prompt Pack

Last updated: 2026-08-02

These are the direct English task prompts consumed by DeepSeek v4 Flash through
`tools/ai/deepseek-worker.ps1`. They are not prompts for Codex. Codex selects one
packet from `docs/WAVE_PLAN.md`, fills one mode template, and invokes the worker.

## Sequential one-wave queue prompt

Paste the following prompt once per wave. Every invocation consumes at most one
wave file. Reuse the same prompt for the next wave only after the current file
has been archived under `waves/done/`.

```text
PROCESS EXACTLY ONE WAVE FROM THE LOCAL TRUBAGUI WAVE QUEUE.

Authority and safety:
- Read rules.md and AGENTS.md first. They override this prompt.
- Codex is the primary orchestrator and final verifier.
- Use tools/ai/deepseek-worker.ps1 with the discovered
  opencode-go/deepseek-v4-flash model as much as allowed.
- DeepSeek is a bounded worker. It does not choose product, architecture,
  security, authorization, schema, migration, provider, release, or Git policy.
- Never perform real SSH, Slurm, SFTP, credential, deployment, publication, or
  live-cluster operations unless the wave explicitly requires user authority
  and that authority is present. Wave 9 never starts automatically.

Queue selection:
1. Run `powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action recover`.
2. Run `powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action audit` and
   stop on any nonzero result. Never repair ordering by hand.
3. Run `powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action claim`.
   The manager atomically selects only the first waiting wave and returns its
   claim token. Preserve that token for this invocation.
4. Resume an existing claim only with its same owner and token. Never
   force-release another claim without explicit Codex investigation.
5. Do not edit queue status or move manifests manually.

Execution:
1. Treat the wave file as an orchestration manifest, never as one oversized
   DeepSeek task.
2. Process its packets in the exact listed order.
3. Give each packet a separate English analyze task and log identity using
   -Wave and -Card. Use the generous mode timeout from the manifest.
4. For delivery-eligible packets, use a clean sibling Git worktree and make a
   separate bounded implementation call. Never let DeepSeek write to the
   primary worktree.
5. Inspect every changed path and full diff, reject unrelated work, then run a
   separate read-only DeepSeek review and an independent Codex review.
6. Run the packet's authoritative checks in the primary context. A claimed test
   without observed output and exit status is not PASS.
7. Write the packet verdict under
   .agent-runs/evidence/<WAVE_ID>/<PACKET_ID>/verdict.json.
   Include machine-readable capacity size, ceilings, observed counts, and
   `withinLimit` evidence.
8. Stop the wave immediately on FAIL, SPLIT, BLOCKED, missing authority, a dirty
   or invalid worktree, a capacity overrun, or an unresolved gate. Preserve the
   file under waves/waiting/ with status BLOCKED and do not start another wave.

Completion and archival:
1. Re-evaluate the wave exit gate independently.
2. Run `powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action verify
   -ClaimToken <TOKEN>`. It validates ordering, ownership, verdict schemas,
   PASS states, and Flash file/line capacity ceilings.
3. Only Codex may declare the wave complete. A delegated DeepSeek worker returns
   READY_FOR_CODEX_ARCHIVE instead.
4. Codex runs `powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action
   complete -ClaimToken <TOKEN> -CompletionNote <ENGLISH_CLOSEOUT>`.
5. The manager reruns all gates, records closeout data, runs Git checks, and
   moves exactly the claimed manifest from waves/waiting to waves/done.
6. Stop after the command. Do not open or execute the next waiting wave in the
   same prompt invocation.

Return an English report with:
1. Selected wave file
2. Starting dependency state
3. Packet-by-packet run IDs and verdicts
4. Files changed per packet
5. Exact tests and exit statuses
6. Wave exit-gate result
7. Archive action or blocking reason
8. Next waiting wave name, reported only and not started
```

The local queue is intentionally ignored by Git. Its execution evidence remains
auditable through `.agent-runs/`, which is also local and ignored. The canonical
versioned plan remains `docs/WAVE_PLAN.md`; byte-identical recovery templates
live under `tools/ai/wave-templates/`.

Never pass this whole file or a whole wave to the worker. Copy only the relevant
mode block, replace every placeholder, confirm that the result passes the worker
validator, and store it under `.agent-runs/tasks/`. One task file represents one
packet and one mode.

## Capacity contract

DeepSeek v4 Flash receives only the files and context needed for one packet:

- Small: at most 3 intended files and about 200 changed lines.
- Medium: at most 5 intended files and about 400 changed lines.
- Audit: no changed files.
- Reserved: no DeepSeek delivery.

If evidence indicates that either limit will be crossed, DeepSeek stops and
returns a split recommendation. It must not combine packets, absorb a later
wave, or use a broad refactor to fit the requested behavior.

Every task, explanation, report, and new CHANGELOG entry is English. Product UI
resources and paired user guides retain their required Turkish and English
coverage.

## Required invocation fields

Codex invokes every non-dry run with explicit identity and logs enabled:

```powershell
powershell -NoProfile -File tools/ai/deepseek-worker.ps1 `
  -Mode <analyze|implement|review> `
  -TaskFile <SAFE_ENGLISH_TASK_FILE> `
  -Wave <WAVE_ID> `
  -Card <PACKET_ID> `
  -TimeoutMinutes <20_FOR_ANALYZE_OR_REVIEW|30_FOR_IMPLEMENT> `
  -WorktreePath <CLEAN_SIBLING_WORKTREE_FOR_IMPLEMENT_ONLY>
```

`-NoLogs` is not used. Codex verifies `request.md`, `stdout.log`, `stderr.log`,
and `metadata.json`, including raw/effective exit codes and response presence,
then records the independent packet verdict described in `docs/WAVE_PLAN.md`.
The worker already applies generous defaults (20 minutes for analyze/review, 30
for implement, and 10 for smoke-test). The explicit field above makes wave
execution auditable and may be increased, with Codex justification, up to the
120-minute hard ceiling.

Every packet verdict must contain machine-readable capacity evidence:

```json
{
  "capacity": {
    "size": "Small",
    "maxFiles": 3,
    "maxChangedLines": 200,
    "observedFiles": 2,
    "observedChangedLines": 137,
    "withinLimit": true
  }
}
```

Use `Audit` and `Reserved` with 0/0, `Small` with 3/200, and `Medium`
with 5/400. The queue manager refuses missing, inconsistent, or over-limit
capacity evidence.

## Direct ANALYZE prompt

Copy only this block for `-Mode analyze`. Keep its wording read-only.

```text
ANALYZE ONLY. Do not edit files.

Repository authority:
- rules.md
- AGENTS.md
- docs/WAVE_PLAN.md

Execution identity:
- Active wave: <WAVE_ID>
- Packet: <PACKET_ID>
- Size: <AUDIT|SMALL|MEDIUM>
- Maximum intended files: <COUNT>
- Maximum intended changed lines: <COUNT_OR_ZERO>

Goal:
<ONE_BOUNDED_OUTCOME_IN_ENGLISH>

Relevant layers:
- <SAFE_EXACT_PATH_OR_NEUTRAL_LAYER>

Evidence questions:
1. What behavior already exists, with file and line evidence?
2. Which acceptance criteria are already satisfied?
3. What is the narrowest remaining gap?
4. Which existing service and test-double patterns apply?
5. Which exact files are necessary and why?
6. What local checks prove the behavior without live operations?
7. Will the packet exceed its file or line ceiling?

Forbidden scope:
- Any file outside the named packet boundary
- UI unless the packet explicitly allows it
- Persistence-format or provider decisions
- Live external operations
- Release publication or history manipulation
- Product, security, or authorization policy

Stop conditions:
- A reserved decision is required.
- Repository evidence contradicts the packet.
- The packet exceeds either capacity ceiling.
- Verification requires a live operation.
- Required scope overlaps a later packet.

Return exactly these sections in English:
1. Packet interpretation
2. Verified current behavior
3. Required files with reasons
4. Existing patterns to reuse
5. Remaining gap
6. Acceptance-criteria matrix
7. Exact local test plan
8. Capacity verdict: FIT or SPLIT
9. Proposed split when needed
10. Risks and reserved decisions
11. Unverified assumptions

Every factual claim needs repository evidence. Never report PASS without an
observed command result and exit status.
```

## Direct IMPLEMENT prompt

Copy only this block for `-Mode implement`. Use a verified clean sibling
worktree. The selected packet must be marked delivery-eligible in WAVE_PLAN.

```text
IMPLEMENT ONLY this single bounded packet in the delegated clean worktree.

Repository authority:
- rules.md
- AGENTS.md
- docs/WAVE_PLAN.md

Execution identity:
- Active wave: <WAVE_ID>
- Packet: <PACKET_ID>
- Size: <SMALL|MEDIUM>
- Maximum changed files: <COUNT>
- Maximum changed lines: <COUNT>

Objective:
<ONE_BOUNDED_DELIVERABLE_IN_ENGLISH>

Prerequisites already verified by Codex:
- <PREREQUISITE>

Allowed files or layers:
- <SAFE_EXACT_PATH_OR_NEUTRAL_LAYER>

Forbidden scope:
- Any path not listed above
- Neighboring or later packets
- Broad refactors or parallel service implementations
- UI unless explicitly listed
- Persistence-format, provider, product, security, or authorization decisions
- Live external operations
- Release publication or history manipulation

Acceptance criteria:
1. <OBSERVABLE_RESULT>
2. <OBSERVABLE_RESULT>
3. <OBSERVABLE_ERROR_OR_SAFETY_RESULT>
4. No unrelated file changes.
5. The final diff remains within the stated capacity ceiling.

Required local checks:
- <EXACT_TARGETED_COMMAND>
- <EXACT_TARGETED_COMMAND>
- python scripts/check_i18n.py
- git diff --check
- git status --short

Working rules:
- Reuse existing services and test doubles.
- Keep UI and CLI handlers thin.
- Use fake or mock behavior only.
- Preserve actionable stderr and exit-code information.
- Do not expose sensitive values in output or logs.
- Add regression coverage for the changed behavior.
- Record exact commands, exit statuses, and meaningful output.

Stop without broadening scope when:
- Any reserved decision is required.
- An allowed path is insufficient.
- The diff will exceed either capacity ceiling.
- A prerequisite is false.
- A local test cannot prove the behavior.

Return exactly these sections in English:
1. Files changed
2. Behavior delivered
3. Acceptance-criteria results
4. Tests with commands and exact exit statuses
5. Checks not run and reasons
6. Diff statistics
7. Git status
8. Concerns and assumptions
9. Capacity verdict: WITHIN LIMIT or SPLIT REQUIRED
10. Confirmation that no commit was made
```

## Direct REVIEW prompt

Copy only this block for `-Mode review`. Review mode starts in the primary repo,
so provide the verified absolute sibling-worktree path. Keep the task read-only.

```text
REVIEW ONLY. Do not edit files.

Repository authority:
- rules.md
- AGENTS.md
- docs/WAVE_PLAN.md

Execution identity:
- Active wave: <WAVE_ID>
- Packet: <PACKET_ID>
- Size: <SMALL|MEDIUM>
- Maximum changed files: <COUNT>
- Maximum changed lines: <COUNT>
- Delegated worktree: <VERIFIED_ABSOLUTE_PATH>

Review target:
- Read the worktree diff and the changed files for this packet.
- Compare the final behavior with the packet acceptance criteria below.

Allowed paths:
- <SAFE_EXACT_PATH_OR_NEUTRAL_LAYER>

Acceptance criteria:
1. <OBSERVABLE_RESULT>
2. <OBSERVABLE_RESULT>
3. <OBSERVABLE_ERROR_OR_SAFETY_RESULT>
4. No unrelated file changes.

Required evidence:
- Worktree status
- Full diff
- Diff statistics
- Targeted test output supplied by the worktree
- Error and boundary behavior

Review questions:
1. Does the diff remain inside allowed paths and capacity limits?
2. Does it reuse existing services and test doubles?
3. Are command construction, paths, and external arguments safely handled?
4. Are error diagnostics actionable and free of sensitive values?
5. Do tests cover success, refusal, and failure paths?
6. Is any acceptance criterion unsupported by observed evidence?
7. Is any later packet accidentally included?

Stop conditions:
- The worktree path or Git head differs from the supplied evidence.
- The diff exceeds the packet boundary or capacity ceiling.
- A live operation would be required.
- A reserved decision appears in the diff.

Return exactly these sections in English:
1. Critical correctness problems
2. Scope violations
3. Capacity-limit violations
4. Missing or weak tests
5. Error handling
6. Security and authorization boundaries
7. External-operation safety
8. Documentation and language policy
9. Unverified claims
10. Required corrections
11. Final verdict: PASS, FAIL, or SPLIT

PASS requires repository evidence and observed test output. A clean-looking diff
without test evidence is not PASS.
```

## Packet binding checklist for Codex

Before each call, Codex copies the selected packet's exact goal, allowed scope,
acceptance criteria, checks, and size ceiling from `docs/WAVE_PLAN.md` into the
matching mode template. Codex must verify that:

- every placeholder is replaced;
- only one packet is present;
- the task text passes the worker validator;
- `-Wave` and `-Card` match the prompt;
- implement uses the verified clean sibling worktree;
- logs are enabled;
- the returned run ID is recorded;
- the final `verdict.json` references all analyze/implement/review run IDs.

`SEC-02C` uses `RESERVED` size for analyze/review and never receives the IMPLEMENT
prompt. `LIVE-09` receives no DeepSeek prompt. Documentation packets DS-08A1,
DS-08A2, DS-08A3, and DS-08B receive separate calls and diffs.
