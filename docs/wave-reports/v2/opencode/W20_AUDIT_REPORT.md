# W20 Audit Report

```text
Wave: W20
Audit cycle: 1
Decision: PASS
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Date: 2026-09-20
```

## Authority and dependency

Fresh-context review used `CORE_EXECUTION_RULES.md`, the sole executable
`waves/pending/W20.md`, all 26 `HPC-W05-TERM-001..026` registry/index rows
(MANDATORY), the W20 TODO map rows (none), and Workstreams C, D, E and F of
`WAVE_V2_FINAL_05.md`. `waves/bak/` was not used. `W19_AUDIT_REPORT.md` is
PASS with no later contrary state; the predecessor gate is satisfied.

## Identity and working tree

- Branch `develop`; HEAD and `origin/develop` both
  `0f8902a023bac76071527232c2287af96478ed2b`.
- Plugin is `develop` at `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; no
  tracked plugin change was present (one unrelated untracked preview file).
- The main tree remains dirty with the pre-existing stacked changes. No
  reset, clean, commit, push, or implementation edit was performed by this
  audit; unrelated files were preserved.
- `git diff --check` exited 0. Secret-pattern scan over W20 source/tests,
  report and evidence found no credential/key/token material.

## Re-verification

Live review confirmed the canonical wx WebView input/output/clipboard/resize
paths, UTF-8/JSON handling, bounded queues, generation guards, subscriber
detachment, dead-widget checks, status restoration, and xterm bridge behavior.
FIX-A honors the `send_shell_input -> bool` contract and exposes the localized
failure diagnostic. FIX-B bounds and orders pre-ready paste, flushes on ready,
and clears on close. The legacy TextCtrl silent-write observation and the
single-byte truncation conservatism observation are accurately documented as
P3, non-blocking: the mandatory canonical path is fixed and TERM-016 requires
an explicit bound, not lossless retention beyond that bound.

Focused reruns:

```text
python -m pytest tests/test_w20_terminal_io.py -q -p no:randomly
4 passed, 0 failed, exit 0
python -m pytest tests/test_wx_terminal_webview.py -q -p no:randomly
29 passed, 0 failed, exit 0
python -m pytest tests/test_wx_terminal_behavioral.py -q -p no:randomly
19 passed, 0 failed, exit 0
python -m pytest tests/test_wx_terminal_parity_evidence.py tests/test_wx_terminal.py tests/test_wx_embedded_terminal.py -q -p no:randomly
23 passed, 0 failed, exit 0
python -m pytest tests/test_terminal_boundaries.py tests/test_terminal_pty_wire.py tests/test_terminal_bridge.py tests/test_terminal_assets.py -q -p no:randomly
8 passed, 0 failed, exit 0
scripts/check_i18n.py
key/reference/hardcoded checks OK
```

The first combined native-WebView run hit the already documented Windows
WebView2 access-violation/orphan-process environmental failure; after cleanup,
the same 83 tests passed in the segmented runs above (4+29+19+23+8), with no
test skip/xfail or assertion weakening.

## Evidence

- GUI artifact `build/audit/w20-gui-pytest.txt`: 4 passed, exit 0;
  SHA-256 `B4E93C7ECCBA6F3B0F4D11C8738FAEA16A6A5B093B938E14B1131BDC06D5E839`.
  The tests construct real wx panels and dispatch real bridge events; mocks
  are limited to SSH transport and JS sink boundaries.
- EXTERNAL artifact `build/audit/w20-external-matrix.txt`: E1, E2, E2b, E3,
  E4, E5, E5b, E5c, E6, E6b, E6c and E7 PASS; authorized hpclab identity,
  healthy-before/after and cleanup are recorded in the canonical report.
  SHA-256 `B88A14418046638029F0DD39D63B898ECEEBFB4F0EB571A1C264247F73FE2DF5`.
  The logged WebView2 “Operation aborted” line is the known test-process
  cleanup noise and did not alter the external PASS/cleanup results.
- PACKAGE is correctly N/A: W20 has no package requirement and no package or
  build-input change.

## Findings and verdict

No owned P0/P1/P2 blocker remains. `OBS-W20-003` and `OBS-W20-004` remain
honest, explicitly scoped P3 observations and do not invalidate the required
canonical GUI or real external evidence. The W20 report, implementation
traceability, tests, and required evidence are current and consistent.

**PASS.** W20 is eligible for close; W21 was not started.
