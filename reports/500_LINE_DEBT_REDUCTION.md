# 500-Line Debt Reduction

Date: 2026-10-23

## Result

Status: PASS for the repository architecture gate, with 42 existing over-limit allowlisted files remaining.

The current checker passed over 853 first-party files. No unallowlisted over-limit file was reported. The allowlist was reduced from 49 to 42 entries during this work: seven entries were removed. There are 30 remaining entries that are independent of the other dirty checkout, and 12 cross-checkout conflict files were intentionally left untouched. The 400–500 line warning zone also remains.

The SSH retry policy was extracted into a cohesive helper, keeping the SSH client source below the hard limit at 496 lines. Journal Studio's large-file visual refresh now pauses structure rendering beyond 10,000 lines while retaining the journal text. Focused tests passed for the SSH jump boundary (24), large-file behavior (6), and adjacent packaging/version checks (20).

The 12 conflicted files overlap changes in the separate user checkout on codex/log-repeat-groups. That checkout was not modified. No new exception was added to hide debt.

The 42 remaining entries are time-limited through the existing allowlist policy. The next refactor wave should prioritize the 30 independent entries, then handle the 12 conflicts only after a safe integration with the other checkout. Do not describe the remaining debt as resolved.

Evidence: evidence/line-limit-final.log in the handoff ZIP.
