# W07 Fresh-Context Audit Report

Wave: `W07`  
Executable authority: `waves/pending/W07.md` only  
Audit date: 2026-09-21 UTC
Model: `openai/gpt-5.6-luna`

## Authority and dependency

- Re-read `waves/pending/W07.md`, `.opencode/prompts/30_AUDIT_WAVE.md`, core
  protocol, all 16 W07 registry rows, the W07 index rows, and both mandatory
  source sections (Workstream A and Workstream B). No W07 TODO rows exist.
- `waves/pending/W07.md` is the sole executable target; `waves/bak/` was not
  read. The pending namespace contains the canonical W01-W61 files.
- W07 depends on W06. The current canonical `W06_AUDIT_REPORT.md` records
  `WAVE_PHASE_STATUS: BLOCKED` because its report/evidence identity is stale
  and its dependency chain is unresolved. Therefore W07 cannot truthfully be
  accepted, even though its own focused checks currently pass.

## Current repository and plugin truth

- Main: `develop`, `f94adb640136181dbaafa84f62c753b013f0b94e`.
- Plugin: `develop`, `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; remote develop
  matches. Only disclosed plugin working-tree item is untracked
  `.github/social-preview.jpg`.
- The W07 wave report and prior audit are bound to main SHA
  `0f8902a023bac76071527232c2287af96478ed2b`, not current HEAD. The intervening
  history includes behavior-affecting provider/plugin validation and loader
  changes, so the old W07 evidence cannot be inherited. The current working
  tree also contains unrelated dirty lab/report/test changes, including
  `tests/test_local_real_lab_static.py`; these were not modified by this audit.
- `git diff --check` has pre-existing line-ending advisories and a known
  trailing-whitespace error in another Wave audit report. No secret or private
  key bytes were read.

## Independent verification

- Current source still exposes the reported seven provider-presentation
  capabilities, ten environment-report keys, five manifest capabilities, and
  allow-listed v4 adapter/parser contracts. Capability absence, quota-gate
  distinctions, total contract extraction, and honest unsupported UI labels
  remain consistent with the W07 contract.
- Real GUI probe rerun:
  `python C:\Users\mskomek\AppData\Local\Temp\opencode\w07_wx_probe.py`
  → exit 0, **17/17 PASS**, using real wx runtime/event handling.

## Tests

- Combined W07-focused suites: **232 passed, 20 skipped**, exit 0. The skips
  are the expected environment-gated plugin-contract cases.
- With `HPC_GUI_CONTRACT_REPO=D:\Projeler\hpc-client-gui-plugins`,
  `python -m pytest tests/test_plugin_contract.py -q -p no:cacheprovider`
  → exit 0, **20 passed**.
- These fresh results do not repair the stale SHA binding in the canonical W07
  report or clear the blocked W06 dependency. No test was weakened and no
  fabricated GUI/package/external evidence was accepted. W07 requires GUI
  evidence only; LOCAL_REAL/EXTERNAL evidence is not applicable.

## Findings and verdict

| Finding | Severity | Owner/state |
|---|---|---|
| `W07-AUDIT-001`: canonical W07 report/evidence is bound to `0f8902a0`, while current main is `f94adb64`; intervening provider/plugin behavior changes invalidate the prior audit/evidence identity. | P1 | W07 report/evidence refresh required; BLOCKING |
| `W07-AUDIT-002`: required dependency W06 is currently `BLOCKED` in its canonical audit, so W07 cannot inherit dependency acceptance. | P1 | W06/earlier dependency reconciliation; BLOCKING |

Do not fix product or test findings in this audit. Rebind W07 evidence to the
current implementation state and obtain a fresh PASS for W06 before re-auditing
W07.

WAVE_PHASE_STATUS: BLOCKED
