# W08 Fresh-Context Audit Report

Wave: `W08`  
Executable authority: `waves/pending/W08.md` only
Audit date: 2026-09-21 UTC
Auditor: `openai/gpt-5.6-luna`

## Authority and scope

- Re-read the canonical pending W08 contract, audit prompt, core protocol, all 14 owned `HPC-W02-SCHEMA-*` registry rows, W08 index rows, TODO ownership, and Workstreams C, D and E of `WAVE_V2_FINAL_02.md`.
- Exactly one canonical W08 target was audited. `waves/bak/` was not read.
- W08 requires GUI evidence; no EXTERNAL/LOCAL_REAL, package, or private-key evidence is required by this contract.

## Current repository and dependency truth

- Main checkout: `develop`, HEAD `f94adb640136181dbaafa84f62c753b013f0b94e`.
- Plugin checkout: `D:\Projeler\hpc-client-gui-plugins`, `develop`, `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; only disclosed plugin working-tree item is untracked `.github/social-preview.jpg`.
- The canonical W08 report and its evidence bind the implementation to `0f8902a023bac76071527232c2287af96478ed2b`, not current HEAD. The intervening history includes provider/plugin validation and loader behavior changes. That stale identity cannot be inherited.
- The required dependency W07 is currently `BLOCKED` in its canonical audit: its report/evidence is also stale at `0f8902a0`, and W06 is blocked. W08 cannot inherit dependency acceptance.
- The working tree has unrelated dirty lab/report/test changes and untracked files. `git diff --check` also reports pre-existing trailing whitespace in `W04_AUDIT_REPORT.md`; no unrelated change was modified.

## Independent current checks

- `python -m pytest tests/test_w08_schema_isolation.py -q -p no:cacheprovider` → **15 passed**, exit 0.
- With `HPC_GUI_CONTRACT_REPO=D:\Projeler\hpc-client-gui-plugins`, `python -m pytest tests/test_plugin_contract.py -q -p no:cacheprovider` → **20 passed**, exit 0.
- Real wx probe `C:\Users\mskomek\AppData\Local\Temp\opencode\w08_wx_probe.py` → **12/12 PASS**, exit 0.
- Current source contains the shared storage/quota validator, isolated loader paths, deterministic discovery, and the W08 regression suite. These fresh checks support the claimed behavior but do not repair stale canonical evidence identity or the blocked W07 dependency.

## Requirement and evidence assessment

The W08 report traces all 14 owned requirements to live owners, tests, and evidence, and the current focused checks exercise the principal schema/isolation and GUI paths. The prior closed `DEF-W08-001` finding is consistent with current source behavior. No new product/test finding was fixed by this audit.

## Findings

| Finding | Severity | Owner/state |
|---|---|---|
| `W08-AUDIT-001`: canonical W08 report/evidence is bound to `0f8902a0`, while current main is `f94adb64`; intervening behavior-affecting provider/plugin history invalidates the prior audit/evidence identity. | P1 | W08 report/evidence refresh required; BLOCKING |
| `W08-AUDIT-002`: required dependency W07 is canonically `BLOCKED` because its evidence is stale and W06 is blocked. | P1 | Earlier dependency reconciliation; BLOCKING |

No package or EXTERNAL claim was accepted. No private-key bytes were read. No product or test files were changed.

## Verdict

W08 cannot be accepted until its evidence/report is rebound to current HEAD and the W07 dependency chain is truthfully accepted. Fresh focused tests and GUI runtime checks pass, but they do not clear these lifecycle blockers.

WAVE_PHASE_STATUS: BLOCKED
