# W14 Audit Report

```text
Wave: W14
Decision: PASS
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna)
Date: 2026-09-19
Repair cycle: 2 re-audit (FINAL)
```

## Authority and scope

Audited exactly against `waves/pending/W14.md` (present and unambiguous),
`CORE_EXECUTION_RULES.md`, all eight W14 registry/index rows, the empty W14
TODO ownership slice, `opencode/sources/WAVE_V2_FINAL_04.md` Workstreams A/B/F,
current main/plugin truth, diff and hygiene, tests, the canonical Wave report,
and current PACKAGE evidence. No `waves/bak/` material was used. No product
files were changed; only this audit report was written.

## Current repository and plugin truth

- Main repository: `develop`, HEAD
  `0f8902a023bac76071527232c2287af96478ed2b`; working tree dirty with
  preserved unrelated changes and W14 scope/evidence files.
- Plugin repository: `D:\Projeler\hpc-client-gui-plugins`, `develop`, HEAD
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; only untracked
  `.github/social-preview.jpg`. This matches the plugin SHA bound by the
  candidate manifest, identity header, and Wave report.
- `git diff --check` is clean. No credential, token, private-key, or secret
  value was found in the W14 scope report, evidence, helpers, or tests;
  existing generic `loopback_password` is a test variable name only.

## Eight-row canonical trace

The canonical Wave report now contains its own explicit eight-row
requirement → live implementation owner → test → evidence trace (lines
38–52), rather than relying on an audit table. All eight owned IDs are present:

| Requirement group | Audit result |
|---|---|
| `HPC-W04-ART-001` | Trace names manifest/provenance/smoke owners, four relevant tests, and current candidate/package evidence. PASS |
| `HPC-W04-PROV-001..003` | Trace names provenance capture and stale-guard owners, focused tests, and current identity/stale-guard evidence. PASS |
| `HPC-W04-MANIFEST-001..002` | Trace names manifest/version owners, manifest/version tests, exact manifest and isolated wheel evidence. PASS |
| `HPC-W04-IDENTITY-001..002` | Trace names identity helper/wiring and exact-hash owners, identity tests, six-line header and hash evidence. PASS |

## Verification gates

- **Tests/count:** the exact impacted command named by the report was rerun:
  `python -m pytest tests/test_w14_provenance_manifest.py tests/test_release_manifest.py tests/test_version_consistency.py tests/test_release_surface.py tests/test_sync_version.py tests/test_wave10_release_gate.py tests/test_release_test_suite.py -q`
  → **43 passed, 0 failed, exit 0**. The canonical count is exactly 43 with
  partition `17+3+1+2+1+16+3`; its recorded `43 passed in 8.35s` is
  consistent with the rerun (this environment took 13.35s).
- **PACKAGE binding:**
  `dist/w14-candidate-r1/hpc_client_gui-1.5.9-py3-none-any.whl` independently
  hashes to
  `3b2849b7916741455aaff47625043ee343b32a921cfb713e8c80bb8c66fcda48`,
  matching `MANIFEST.json`, the identity header, and the report. The manifest
  binds main/plugin SHA, timestamp, version, runtime, packager, target,
  command, lock hash, filename, and artifact hash. Isolated wheel import
  reports version `1.5.9`.
- **Plugin freshness:** current sibling plugin HEAD is the exact bound
  `f0abb7e...`; status is documented and the candidate evidence is not bound
  to the unrelated context-mode checkout.
- **Stale guard:** current CLI reruns fail closed with exit 2. Without
  `--known-fresh`, the candidate wheel is listed among 13 stale paths; with
  `--known-fresh hpc_client_gui-1.5.9-py3-none-any.whl`, it is excluded and
  12 genuine stale paths remain. This matches the corrected report and proves
  the declaration is effective rather than silently accepting stale output.
- **Evidence honesty:** the packaged-smoke JSON truthfully records `.whl` as
  unsupported by that wx harness (`FAIL`), while the wheel version probe and
  identity/header tests provide the applicable package evidence. GUI and
  EXTERNAL are correctly N/A for W14.

## Findings and decision

No blocking or in-scope findings remain. The prior missing canonical trace and
stale count are corrected: the trace is present in the Wave report and the
exact impacted result is 43 passed with the required command and partition.

**PASS.** W14 is accepted. No W15 action was taken or started.
