# Wave 08 — Documentation and Maintenance Policy

Status: waiting
Owner: Codex; DeepSeek drafts only
Priority: P2
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, draft/delivery 30m, review 20m

## Goal

Document the complete CLI in Turkish and English and make GUI/CLI parity,
testing, TODO, CHANGELOG, and release maintenance rules enforceable.

## Why This Wave Exists

Documentation must be generated from the verified final command surface, not
from planned or assumed behavior. Maintenance rules must prevent future drift.

## Depends On

- Waves 01 through 07 are under `waves/done/`
- final parser/help surface and release gates are verified

## Target Files

- `README.md`
- one canonical documentation directory selected by Codex
- maintenance/release checklist
- relevant TODO and new CHANGELOG records

## In Scope

- command inventory and links
- Turkish and English CLI guides with equal topology
- exit codes, text/JSON, confirmation flags, safe examples
- GUI-counterpart evaluation and shared-service policy
- test and release enforcement rules

## Out of Scope

- runtime behavior changes
- unverified example output
- rewriting historical CHANGELOG entries
- claims that unrun live tests passed

## Packets and Tasks

### DS-08A1 — Root README inventory (Small)

- [ ] Inventory every verified parser command.
- [ ] Add concise summary and canonical guide links.
- [ ] Do not draft the full guides in this packet.

### DS-08A2 — Turkish CLI guide (Medium)

- [ ] Cover every inventory command.
- [ ] Document exit codes, text/JSON, confirmation, and safe examples.
- [ ] Use the canonical section topology.

### DS-08A3 — English CLI guide (Medium)

- [ ] Mirror the Turkish guide's command and section coverage.
- [ ] Verify examples against actual help and tests.
- [ ] Do not combine this call with DS-08A2.

### DS-08B — Maintenance and GUI/CLI parity process (Small)

- [ ] Define CLI-counterpart evaluation for new GUI actions.
- [ ] Require shared-service use or explicit GUI-only rationale.
- [ ] Connect help, JSON, unit, smoke, release, TODO, and CHANGELOG gates.
- [ ] Keep technical reports and new CHANGELOG entries English.

## Validation

- [ ] Parser-to-document command scan passes.
- [ ] Turkish and English guides cover identical commands/topics.
- [ ] Links resolve.
- [ ] TODO/CHANGELOG/checklist cross-scan passes.
- [ ] `python scripts/check_i18n.py`
- [ ] `git diff --check`
- [ ] `git status --short`
- [ ] PASS verdict exists for DS-08A1, DS-08A2, DS-08A3, and DS-08B.

## Done Criteria

1. README covers every command and links canonical guides.
2. Turkish and English guides have equal verified scope.
3. Maintenance and release checklist rules are enforceable.
4. All technical reports and new CHANGELOG text follow the English policy.

## Possible Blockers

- parser/help surface differs from completed wave evidence
- canonical documentation location is undecided
- repository-wide i18n failures remain unresolved

## Completion Notes

- Completed at:
- Packet verdicts:
- Documents changed:
- Tests and exit codes:
- Remaining uncertainty:

## On Completion

- Codex marks this file done and moves it to `waves/done/` after all gates PASS.
- Stop the prompt; report Wave 09 as blocked next and do not start it.
