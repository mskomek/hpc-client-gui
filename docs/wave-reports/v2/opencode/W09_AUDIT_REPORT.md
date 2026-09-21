# W09 Fresh-Context Audit Report

Wave: `W09`
Auditor: GPT-5.6 Luna (`openai/gpt-5.6-luna`)
Audit date: 2026-09-21 UTC
Decision: **REOPEN**

## Authority and scope

- Audited exactly canonical `waves/pending/W09.md`; `waves/bak/` was not read.
- Re-read the audit prompt, Core execution rules, all 34 W09 registry rows, all 7 W09 TODO rows, the W09 index/ownership map, and all seven mandatory `WAVE_V2_FINAL_02.md` sections.
- Re-read the canonical W09 report, prior audit, current provider/plugin source and tests, current diff, and current dependency identities.
- W09 has required `GUI,PACKAGE` evidence. It does not require `EXTERNAL` evidence for its owned scope, so `LOCAL_REAL_HPC_LAB.md` was not applicable. No private-key bytes were read.

## Current identity and diff

- Main repository: branch `develop`, HEAD `f94adb640136181dbaafa84f62c753b013f0b94e`, equal to `origin/develop`.
- Plugin repository: `D:\Projeler\hpc-client-gui-plugins`, branch `develop`, HEAD `f0abb7e7037e66ab451d463c699fecf4e00c89eb`, equal to `origin/develop`; tracked tree clean, with only the pre-existing untracked `.github/social-preview.jpg`.
- Current main working-tree diff (before this audit artifact update): SHA-256 `CDE2F896FCBE9AFB5417F069F7E316765F2DEEBF88483F60FAB97A34C8DE8AAB`, 193,773 UTF-8 bytes. It contains unrelated lab/report changes and no W09 product-file change; `git diff --check` reports only pre-existing trailing whitespace in other Wave audit reports.
- HEAD advanced from the identity recorded by the W09 report/audit (`0f8902a...`) to `f94adb64...` through subsequent commits. This is a changed integration/repository identity, so the prior W09 audit/evidence cannot be inherited as current.

## Current re-verification

- Focused W09 compatibility/provider/plugin/schema/installer tests with `HPC_GUI_CONTRACT_REPO=D:/Projeler/hpc-client-gui-plugins`: **117 passed, 0 failed**, exit 0.
- The live validator still accepts the plugin contract's `access` and `requirements` object sections and retains fail-closed unknown-key validation. The plugin pin and the six-provider compatibility fixture remain present.
- A fresh package build from the current checkout completed successfully. Current artifacts are wheel `dist/hpc_client_gui-1.5.9-py3-none-any.whl`, 908,009 bytes, SHA-256 `DEDBCB238544E5B1AD392A7A0C6934A3493D588EF6B8B0474C60CE5273FC3A07` and sdist `dist/hpc_client_gui-1.5.9.tar.gz`, 1,339,101 bytes, SHA-256 `41B3BE0DCA884800066BF0A396ED2FF96A50B1797604B893607D557A2BE1ECC3`.
- The current canonical W09 report still records the old main SHA/diff identity and old package hashes (`E575BF8A...` / `3E7F5F2A...`), and its resume/final summary says the old identity is current. The current audit therefore cannot certify the report/evidence as exact-current despite the focused tests passing.

## Finding

| Finding ID | Severity | Requirement / gate | Finding | Required owner action |
|---|---|---|---|---|
| `AUD-W09-003` | P1 / blocking | `HPC-GOV-011`, `HPC-GOV-022`, W09 package gate and Definition of Done | Subsequent repository commits changed HEAD from `0f8902a...` to `f94adb64...`; the canonical W09 report and its prior audit/evidence remain bound to the old main identity and old package hashes. The focused source tests pass on the new identity, but the canonical Wave report is not reconciled to the current HEAD and current artifact identity. | Reconcile the canonical W09 report to the current tested tree, refresh all affected W09 evidence/package identity (and GUI evidence if the implementation tree used for that evidence changes), then obtain a fresh independent audit. Do not close W09 on the stale report. |

## Verdict

The provider/plugin behavior and focused tests currently pass, but stale canonical report/evidence identity after repository advancement is a blocking audit finding. No product or test finding was fixed by this audit.

**REOPEN**
