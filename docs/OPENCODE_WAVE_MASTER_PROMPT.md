EXECUTE THE NEXT TRUBAGUI WAVE NOW.

This entire file is the concrete task. Do not summarize it as reference
documentation, ask what the user wants, request another task, or offer a menu
of possible actions. The next eligible local wave manifest is the task. Begin
with repository inspection and queue commands immediately.

## Non-negotiable authority

1. Read `rules.md` and `AGENTS.md` completely before any non-trivial action.
2. Follow the stricter rule when this prompt overlaps repository instructions.
3. Execute exactly one wave during this invocation.
4. Use the project-local OpenCode DeepSeek v4 Flash worker as much as the rules
   allow, but keep every worker call limited to one packet.
5. Running under DeepSeek is not a reason to stop or ask for another task.
   Claim the wave and execute every worker-authorized packet action; reserve
   only independent verdict authorship and final archival for Codex.
6. Never give the complete wave manifest to one worker call.
7. Never stage, commit, push, publish, deploy, alter remotes, rewrite history,
   access sensitive material, or perform real SSH/Slurm/SFTP/transfer actions.
8. Never make product, architecture, security, authorization, schema,
   migration, provider, release, credential, or live-HPC decisions on behalf of
   Codex or the user.
9. Wave 09 must remain blocked unless explicit user authorization, exact target
   scope, isolation, and cleanup rules already exist in the current session.

10. In the Codex desktop environment, a delegated sibling worktree may be
    outside the current OpenCode file-read permission boundary. Never use
    OpenCode `Read` or `Glob` directly on an absolute sibling-worktree path.
    Inspect that worktree only through the project worker's logged summary and
    metadata, plus shell commands such as `git -C <WORKTREE> status --short`,
    `git -C <WORKTREE> diff --check`, `git -C <WORKTREE> diff --stat`, and
    bounded `git -C <WORKTREE> diff` output. If the worker itself cannot access
    the worktree, stop with the exact permission error; do not ask for a broad
    external-directory approval or copy the entire worktree into the primary.

11. Never invoke Python, pytest, unittest, or another interpreter directly
    against an absolute sibling-worktree path from the OpenCode session. The
    delegated `deepseek-worker.ps1 -Mode implement|review -WorktreePath ...`
    process owns all sibling-worktree tests and reports their exact exit codes.
    In the OpenCode session, run authoritative checks only in the primary
    worktree or through the delegated worker; use `git -C` shell inspection for
    sibling status and diffs.

12. Do not stop merely because an analyze report lists bounded implementation
    choices as “reserved”. When the wave plan and acceptance criteria provide a
    deterministic recommendation, use that recommendation and continue through
    implement, review, tests, verdict, and archive. For Wave 03 DS-03A use the
    documented defaults: `--if-exists overwrite` by default, force overwrite at
    the CLI boundary, preserve existing backend resume behavior for `resume`,
    and report additive `skipped` and `renames` payload fields. Stop only for a
    genuinely unresolved product, security, authorization, schema, migration,
    provider, release, credential, or live-HPC decision.

13. During DeepSeek review, never create or inspect a temporary comparison
    checkout and never compare it with the sibling worktree using absolute
    paths. Review the delegated worktree's own `git diff`, status, worker logs,
    and reported test output only. If a broad GUI test suite hangs, do not wait
    indefinitely: use the packet's focused non-GUI tests and report the broad
    timeout as a limitation while continuing the bounded review.

14. For Wave 04 DS-04A, use the wave-plan recommendations for bounded CLI
    contract decisions: keep the existing `doctor connection` command, expose
    canonical stages `port`, `auth`, `sftp`, and `checksum` with statuses
    `PASS`, `FAIL`, or `not_attempted`, emit the nested `stages` payload in both
    text and JSON, return exit 0 only when all stages pass and exit 3 otherwise,
    and place reusable diagnostics logic in the narrowly justified service
    module. Adding an `open_sftp=False` opt-out while preserving the current
    default is allowed. Do not stop for these listed choices.

15. After claiming the wave, map packet dependencies before launching workers.
    Run independent packets in parallel only when their allowed paths are
    disjoint and neither packet consumes another packet's output. Keep phases
    within one packet sequential (`analyze` before `implement`, `implement`
    before `review`). Every parallel implementation requires its own clean
    sibling worktree. If independence is uncertain, preserve manifest order.

16. Start every worker call with `tools/ai/start-deepseek-background.ps1`, not
    by invoking `deepseek-worker.ps1` synchronously. The launcher returns the
    process ID, exact log path, completion-signal path, and first-check time;
    report the log path immediately. Resume as soon as `completed.json`
    appears. If no signal arrives, inspect the process and start marker no
    later than five minutes after launch, then every five minutes while it is
    in flight. A completion signal reports process completion only; verify its
    exit code, filtered log, metadata, diff, and tests independently.

## Start immediately: recover, inspect, and claim

Run these commands in order:

```powershell
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action recover
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action status
```

The `status` result is JSON: `claim: null` means no active claim; a claim object
contains `waveId`, `waveFile`, `owner`, and the local claim value. The current
local owner is `$env:USERNAME`, which is also the queue manager's default.

If `status` reports `claim: null`, run:

```powershell
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action claim
```

Capture the returned `claim.token`, `claim.waveId`, and `claim.waveFile` without
printing the claim value in the final report.

If `status` reports an existing claim, read `waves/.state/claim.json`. Resume it
only when the recorded owner matches the current local owner:

```powershell
powershell -NoProfile -File tools/ai/wave-queue.ps1 -Action claim -ClaimToken <RECORDED_CLAIM_VALUE>
```

If another owner holds the claim, stop with the exact `[BLOCKED] ...` stderr,
exit code 3, and queue state. Do not force-release it and do not select a later
wave.

The absence of a separately supplied user task is not a blocker. The claimed
wave manifest is the task. After a successful claim, read that manifest and
start its first incomplete packet immediately.

## Execute the claimed wave

For the selected manifest only:

1. Confirm all lower-numbered manifests are under `waves/done/`.
2. Preserve packet dependency order; execute only proven-independent packets
   concurrently, using disjoint worktrees and write scopes.
3. For each packet, derive exact goal, allowed files, forbidden scope,
   acceptance criteria, checks, and size from the manifest and
   `docs/WAVE_PLAN.md`.
4. Use a separate English task file and separate logged call for every mode.
5. Use the generous budgets unless repository evidence justifies more:
   analyze 20 minutes, delivery 30 minutes, review 20 minutes.

Analyze launch pattern:

```powershell
powershell -NoProfile -File tools/ai/start-deepseek-background.ps1 `
  -Mode analyze `
  -TaskFile <ONE_PACKET_ANALYZE_TASK> `
  -Wave <CLAIMED_WAVE_ID> `
  -Card <PACKET_ID> `
  -TimeoutMinutes 20
```

After analyze, independently verify every repository claim. For a
delivery-eligible packet, use only a verified clean sibling Git worktree and
run one bounded delivery call:

```powershell
powershell -NoProfile -File tools/ai/start-deepseek-background.ps1 `
  -Mode implement `
  -TaskFile <ONE_PACKET_DELIVERY_TASK> `
  -Wave <CLAIMED_WAVE_ID> `
  -Card <PACKET_ID> `
  -WorktreePath <VERIFIED_CLEAN_SIBLING_WORKTREE> `
  -TimeoutMinutes 30
```

Inspect the complete worktree status and diff. Reject unrelated paths or scope
growth. Then run a separate review against the final bounded diff:

```powershell
powershell -NoProfile -File tools/ai/start-deepseek-background.ps1 `
  -Mode review `
  -TaskFile <ONE_PACKET_REVIEW_TASK> `
  -Wave <CLAIMED_WAVE_ID> `
  -Card <PACKET_ID> `
  -TimeoutMinutes 20
```

DeepSeek output is evidence, never proof. Independently run the manifest's
authoritative checks and inspect exact exit statuses and meaningful output.
Never report PASS for an unobserved command.

## Packet capacity and verdict gate

Every packet verdict must be written by Codex under:

```text
.agent-runs/evidence/<WAVE_ID>/<PACKET_ID>/verdict.json
```

It must validate against `tools/ai/packet-verdict.schema.json`, reference every
applicable successful analyze/delivery/review run, and include exact capacity:

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

Capacity ceilings are mandatory:

- `Audit`: 0 changed files, 0 changed lines.
- `Small`: at most 3 changed files and 200 changed lines.
- `Medium`: at most 5 changed files and 400 changed lines.
- `Reserved`: 0 DeepSeek-delivered files and 0 DeepSeek-delivered lines.
- `SEC-*` and `LIVE-*` use `Reserved`.

If a packet exceeds either ceiling, record `SPLIT`, leave the wave waiting, and
stop. Do not silently broaden it or continue to another packet.

## Stop conditions

Stop the invocation immediately, preserve the active claim, and report exact
evidence when any of these occurs:

- queue command returns nonzero;
- another owner holds the claim;
- dependency or authorization is missing;
- a reserved decision is required;
- a clean sibling worktree is unavailable;
- a packet crosses its file or line ceiling;
- a worker run times out, returns nonzero, or has no response;
- changed paths exceed the packet's allowed scope;
- an authoritative check fails;
- verdict is not PASS;
- a live or sensitive operation would be required.

Do not ask a vague follow-up question. State the concrete blocker, exact failed
command, exit status, preserved evidence path, and required authority or input.

## Verify and archive exactly one wave

After every packet in the claimed manifest has an independently verified PASS
verdict and the manifest Done Criteria are satisfied, run:

```powershell
powershell -NoProfile -File tools/ai/wave-queue.ps1 `
  -Action verify `
  -ClaimToken <CLAIM_VALUE>
```

Only Codex may perform final archival. If this session is a delegated DeepSeek
worker rather than Codex, stop with `READY_FOR_CODEX_ARCHIVE`, retain the claim,
and provide the successful verify evidence. Do not print the local claim value;
Codex recovers it directly from `waves/.state/claim.json` before running the
guarded completion command.

If this session is Codex, archive through the manager only:

```powershell
powershell -NoProfile -File tools/ai/wave-queue.ps1 `
  -Action complete `
  -ClaimToken <CLAIM_VALUE> `
  -CompletionNote <CONCISE_ENGLISH_CLOSEOUT>
```

Never edit status or move a manifest by hand. The manager must rerun ordering,
ownership, schema, PASS, capacity, `git diff --check`, and `git status --short`
gates and move exactly the claimed file to `waves/done/`.

After successful archival, stop immediately. Do not audit the whole repository,
do not inspect or execute another wave, and do not perform any follow-up work.
The next fresh OpenCode session will receive this same master prompt and execute
the next waiting wave.

## Required final response

Return only a concise concrete execution report in English:

1. Claimed wave and manifest
2. Dependency state
3. Packet-by-packet run IDs and verdicts
4. Changed files and capacity results per packet
5. Exact tests with exit statuses
6. Wave Done Criteria result
7. Archive result or exact blocker

Do not respond with “What would you like me to do?”, “Please provide a task,” or
a list of options. Start the queue workflow now.
