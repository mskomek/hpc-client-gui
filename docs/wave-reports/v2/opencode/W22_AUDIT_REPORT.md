# W22 — Audit Report

```text
Wave: W22
Auditor: GPT-5.6 Luna (openai / gpt-5.6-luna)
Decision: BLOCKED
Audited: 2026-09-20
Branch: develop
HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Working tree: dirty; unrelated and stacked changes preserved
Product plugin repo: D:\Projeler\hpc-client-gui-plugins
  branch: develop
  SHA: f0abb7e7037e66ab451d463c699fecf4e00c89eb
  state: dirty with pre-existing .github/social-preview.jpg
Context plugin: D:\Projeler\context-mode-opencode-v2
  SHA: 0788169cdc6aeeadee2a14015a85f3ee7e44fa20
  state: dirty with pre-existing bundle/temp files
```

## Audit scope and authority

Audited exactly the present, unambiguous `waves/pending/W22.md`; no
`waves/bak/` copy was used. Re-read `opencode/prompts/30_AUDIT_WAVE.md`, core
rules, all owned registry rows `HPC-W05-LIFE-031..065`, the empty W22 TODO set,
and all three mandatory sections of `opencode/sources/WAVE_V2_FINAL_05.md`.
The W22 implementation report, prior audit, current source/tests, full current
working-tree status/diff checks, package evidence, and both repository
identities were also inspected. W21 has a canonical audit `PASS` and satisfies
the declared dependency.

## Gate assessment

- **GUI/runtime:** the supplied current W22 evidence records 67 passed focused
  checks. The package smoke evidence records terminal readback, PTY input/output,
  resize, and clean shutdown as `PASS`.
- **PACKAGE:** PASS for exact artifact SHA-256
  `ff050baf26fd73f59d46c6a7ed5290913e1669b67cecbbfa13bb29e5c0122876`.
  Evidence: `build/audit/w22-packaged-smoke-current.json`, whose main SHA is
  `0f8902a023bac76071527232c2287af96478ed2b` and whose artifact hash was
  independently confirmed from `build/hpc-client-gui/hpc-client-gui.exe`.
- **EXTERNAL:** BLOCKED. W22 requires real-target connection/profile cases,
  real SSH-shell proof, and `GJ-01`/`GJ-02`. No authorized real-target matrix
  or real SSH-shell/GJ evidence is present. Disposable loopback/package proof
  cannot substitute for this required evidence.
- **Current test truth:** the supplied W22 evidence is `67 passed`; an
  independent broader selection completed with `103 passed, 1 failed`. The
  failure is `test_w21_disconnect_cb_leaves_connected_and_drops_stale` in the
  W21 lifecycle suite, not an audited W22-owned test; it is recorded as a
  current dependency/stacked-tree observation and was not repaired here.
- **Diff hygiene:** `git diff --check` completed without errors (only existing
  line-ending warnings). The working tree contains extensive unrelated and
  stacked changes; no product or test finding was fixed by this audit.

The external evidence gate prevents PASS. No P0/P1 claim was fabricated and no
cross-Wave finding was absorbed. Resume at authorized real-target/real-SSH and
GJ-01/GJ-02 evidence collection; do not use loopback evidence as a substitute.

WAVE_PHASE_STATUS: BLOCKED
