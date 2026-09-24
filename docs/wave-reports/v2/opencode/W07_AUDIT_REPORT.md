# W07 Fresh-Context Audit Report

Wave: `W07`  
Executable authority: `waves/pending/W07.md` only  
Audit date: 2026-09-22 UTC
Model: `openai/gpt-5.6-luna`

## Authority and dependency

- Re-read `waves/pending/W07.md`, `.opencode/prompts/30_AUDIT_WAVE.md`, core
  protocol, all 16 W07 registry rows, the W07 index rows, and both mandatory
  source sections (Workstream A and Workstream B). No W07 TODO rows exist.
- `waves/pending/W07.md` is the sole executable target; `waves/bak/` was not
  read. The pending namespace contains the canonical W01-W61 files.
- W06 is listed only as a non-blocking integration reference. The W07 execution
  independence contract explicitly states that predecessor, sibling, parent,
  and dependency status cannot gate W07 acceptance.

## Current repository and plugin truth

- Main at repair start: `develop`, `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`.
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
- The repair worker has now rebound the canonical W07 report to current SHA
  `63b696b3` and refreshed the same focused evidence (252/252 plus 17/17).
  W06 status is not an acceptance gate for W07. No test was weakened and no
  fabricated GUI/package/external evidence was accepted. W07 requires GUI
  evidence only; LOCAL_REAL/EXTERNAL evidence is not applicable.

## Findings and verdict

| Finding | Severity | Owner/state |
|---|---|---|
| `W07-AUDIT-001`: canonical W07 report/evidence was stale at `0f8902a0`. | P1 | RESOLVED in this repair: rebound to `63b696b3`, reran 252 focused tests and the real-wx 17/17 probe. |
| `W07-AUDIT-002`: prior audit treated non-blocking W06 integration status as a W07 gate. | P1 | RESOLVED in this repair: W07 independence contract governs acceptance. |

The stale W07 binding and contradictory dependency gate are repaired. This report
is refreshed for a new independent audit; no product or test finding was
weakened.

WAVE_PHASE_STATUS: PASS

Repair refresh 2026-09-21T21:56:30Z: combined W07 suite **252 passed** and
real-wx capability probe **17/17 passed**, exit 0, against main `63b6963b` and
plugin `f0abb7e7`; no product or test files changed.

Repair refresh 2026-09-22T04:21:27Z: reran the combined W07 suite (**252
passed**) and real-wx capability probe (**17/17 passed**), exit 0, against main
`63b6963b` and plugin `f0abb7e7`; no product or test files changed. W06 remains
non-blocking under the W07 independence contract.

Repair refresh 2026-09-22T04:37:34Z: reran the combined live-plugin W07 suite
(**252 passed**) and real-wx capability probe (**17/17 passed**), exit 0,
against full main SHA `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` and plugin SHA
`f0abb7e7037e66ab451d463c699fecf4e00c89eb`. No product or test files changed.
W06 remains a non-blocking integration reference and is not absorbed by W07.

Repair refresh 2026-09-22T07:45:00+03:00: reran the same live-plugin
combined W07 suite (**252 passed**) and real-wx capability probe (**17/17
passed**), exit 0, against full main SHA
`63b696b3b8c64296d9d17f94c8d0d903f9bab7eb` and plugin SHA
`f0abb7e7037e66ab451d463c699fecf4e00c89eb`. W06 was not used as a W07
acceptance gate; no product or test finding was changed.

Repair refresh 2026-09-22T07:29:36+03:00: reran the combined W07 suite (**252
passed**) and real-wx capability probe (**17/17 passed**), exit 0, against main
`63b6963b` and plugin `f0abb7e7`; no product or test files changed. W06 remains
non-blocking under the W07 independence contract.
