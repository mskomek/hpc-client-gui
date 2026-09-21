# W10 Audit Report — fresh independent audit

Wave: `W10`  
Auditor: GPT-5.6 Luna (`openai/gpt-5.6-luna`)  
Audit date: 2026-09-21 UTC

## Authority and scope

Audited exactly `waves/pending/W10.md`; `waves/bak/` was not used. Re-read the
core execution rules, all 27 W10 registry rows, all 7 W10 TODO rows, the
requirement/index ownership entries, and the mandatory `WAVE_V2_FINAL_02.md`
sections (Workstream G, Test matrix, Acceptance criteria, Required evidence).
The canonical W10 report, dependency report, current main/plugin identities,
current diff, tests, GUI/package claims, and security/routing boundaries were
also re-read. W10 requires `GUI,PACKAGE`; it does not require EXTERNAL
evidence, so LOCAL_REAL evidence is not applicable to this audit.

## Current repository truth

- Main repository: `develop`, HEAD
  `f94adb640136181dbaafa84f62c753b013f0b94e`; `origin/develop` is the same.
- HEAD is a post-report sync commit (`Align LOCAL_REAL storage permissions`),
  changing lab files and the lab static test, not the W10 provider sources.
- Plugin repository: `develop`,
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; its only worktree item is the
  pre-existing untracked `.github/social-preview.jpg`.
- The main worktree remains dirty with unrelated changes. Current non-audit
  diff identity captured for review is SHA-256
  `ACA7E23F7F7E7F0EDD099B2E03A76B7B1B764B6D577E1E65A410C0219CFAF22D`
  (201,618 bytes). `git diff --check` reports no new whitespace error in the
  W10-owned implementation, but existing unrelated report whitespace warnings
  remain in the broader worktree.

The prior W10 report and audit are bound to main HEAD
`0f8902a023bac76071527232c2287af96478ed2b` and diff identity
`BAE26D91531BBDC7A01E1A068FEF95E47629B3C82D16F3B1F317B2B4DEEB1784`.
Because repository history changed, that audit/evidence required this fresh
audit and cannot be accepted unchanged.

## Independent verification

- Focused W10 matrix, with the pinned plugin checkout configured: **106 passed,
  2 skipped**, exit 0. The skips are Windows symlink and POSIX-permission
  limitations in the tests, not weakened assertions.
- The provider inventory/disposition and provider-contract trace in the W10
  report remain internally consistent with the mandatory source: exactly one
  `NO-EXPANSION-FOR-V2` disposition, six pinned providers, and the expected
  provider/capability and containment coverage.
- Current plugin identity still matches the recorded compatibility pin.
- No W10 provider implementation change, credential exposure, unsafe command
  interpolation, or cross-Wave ownership defect was found in the current
  source/diff review.

## Finding

**AUD-W10-002 — P1 — PACKAGE evidence is stale and not bound to current
repository truth.**

The canonical report claims package evidence for main HEAD
`0f8902a0…` and records wheel SHA-256
`CE41D5F66521549B2D21FA5171AE73F16532016D606EC6C81B8704AE6C4B3618` plus
sdist SHA-256
`A05CD586F4A4794F5EF7087FC2D1892AA13FD62A88A0D87CD2F2903A60B3A60C`.
The currently present artifacts are instead 908,009-byte wheel
`DEDBCB238544E5B1AD392A7A0C6934A3493D588EF6B8B0474C60CE5273FC3A07` and
1,339,101-byte sdist
`41B3BE0DCA884800066BF0A396ED2FF96A50B1797604B893607D557A2BE1ECC3`.
They have no evidence binding to the current HEAD plus current diff, and the
recorded accepted artifacts are no longer present at those hashes. Therefore
the required exact-artifact PACKAGE gate is not currently auditable, even
though the focused source tests pass. A fresh package build and package-byte
proof bound to the current tested tree are required before PASS.

## Verdict

No product or test code was changed by this audit. The finding routes to W10
resume/repair; the prior PASS is not carried forward across the sync/history
change and stale package identity.

WAVE_PHASE_STATUS: REOPEN
