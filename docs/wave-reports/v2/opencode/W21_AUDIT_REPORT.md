# W21 — Audit Report

```text
Wave: W21
Auditor: GPT-5.6 Luna (openai / gpt-5.6-luna)
Decision: PASS
Audited: 2026-09-20
Branch: develop
HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Working tree: dirty; unrelated stacked changes preserved
Plugin: D:\Projeler\context-mode-opencode-v2
  branch: opencode-v2-compat
  SHA: 0788169cdc6aeeadee2a14015a85f3ee7e44fa20
  state: pre-existing dirty changes
```

## Authority and scope

Audited exactly `waves/pending/W21.md`; no `waves/bak/` copy was used. Re-read:
`opencode/protocol/CORE_EXECUTION_RULES.md`; all owned registry rows
`HPC-W05-LIFE-001..030` and `HPC-W05-LIFE-066..070`; TODO row
`HPC-W05-TODO-LIFECYCLE-NATIVE-002`; and the mandatory sections of
`opencode/sources/WAVE_V2_FINAL_05.md` (Entry criteria, Scope, Non-scope,
Workstream H, Targeted tasks, and Hard blockers). The W21 implementation report,
prior audit, current source, tests, diff, evidence, and plugin truth were also
re-read.

## Findings and implementation review

The WebView terminal now stops and detaches its native view during
`IsBeingDeleted()` teardown without explicitly calling `Destroy()`, while normal
close remains idempotent. The fallback terminal pins subscription generations,
removes every panel-owned callback on A→B→C replacement/disconnect/close, and
drops queued, stale, and post-close output before touching wx controls. Worker
updates remain marshalled through `wx.CallAfter`.

The prior `DEF-W21-AUDIT-001` subscriber leak is closed and is covered by the
current A→B→C regression. No additional in-scope P0/P1 defect was found. The
reviewed W21 material contains no secret exposure, weakened test, skip, or xfail.
Unrelated stacked working-tree changes were preserved; no product or test
finding was fixed by this audit.

## Verification

Rerun against the current working tree:

```text
.venv\Scripts\python.exe -m pytest tests/test_w21_terminal_lifecycle.py -q
8 passed, 0 failed

.venv\Scripts\python.exe -m pytest tests/test_w19_connection_lifecycle.py tests/test_w20_terminal_io.py tests/test_wx_terminal_webview.py -q
53 passed, 0 failed

git diff --check
clean (pre-existing line-ending warnings only)
```

`build/audit/w21-gui-pytest.txt` records 8 passing real-wx/event-loop tests,
including native teardown, fallback reconnect/close guards, and lifecycle
cleanup. SSH is faked only at the transport boundary.

`build/audit/w21-external-matrix.txt` records healthy-before/after,
`W21-EXTERNAL DONE`, and PASS for E1–E7: real loopback SSH/PTY Unicode,
burst, resize, loss/reconnect, stale-callback suppression, disconnect input
rejection, diagnostics, and subscriber detachment.

Package evidence is N/A for this Wave with a concrete justification: the W21
changes alter no build/package inputs, assets, or frozen artifact bytes; exact
packaged acceptance is owned by W22. GUI and EXTERNAL are the required W21
evidence classes.

## Gate assessment

- All 35 source-derived W21 IDs and the one TODO-detail ID are traced.
- GUI and EXTERNAL evidence are current and truthful.
- W20 dependency and entry criteria are satisfied.
- Hard blockers LIFE-066 through LIFE-070 are closed or truthfully justified.
- No owned blocking defect remains.

WAVE_PHASE_STATUS: PASS
