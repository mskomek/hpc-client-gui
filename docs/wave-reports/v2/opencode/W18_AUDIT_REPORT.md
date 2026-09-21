# W18 Audit Report

```text
Wave: W18
Audit cycle: 2
Decision: REOPEN
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Audit date: 2026-09-21 UTC
Authority: waves/pending/W18.md only
```

## Authority, scope, and dependency

Re-read `30_AUDIT_WAVE.md`, `CORE_EXECUTION_RULES.md`, the sole canonical
`waves/pending/W18.md`, all 16 W18 registry/index rows, the zero-row TODO
ownership result, and both mandatory sections of
`opencode/sources/WAVE_V2_FINAL_05.md`. `waves/bak/` was not read. Re-read the
W18 report, audit/evidence artifacts, live SSH/wx/controller code and tests,
current diff/HEAD, and the dependency audit chain. No product or test code was
changed; only this audit artifact is being updated.

W18 depends on W17. The current canonical W17 audit is cycle 4 `REOPEN` because
its dependency W16 is reopened and its GUI evidence is bound to the obsolete
`0f8902a...` identity. W18 therefore cannot close while that repository-owned
dependency chain remains unresolved.

## Current identity and diff

- Branch: `develop`
- HEAD and `origin/develop`: `f94adb640136181dbaafa84f62c753b013f0b94e`
- W18 report/audit and cited evidence identify
  `0f8902a023bac76071527232c2287af96478ed2b`.
- The repository advanced through LOCAL_REAL/lab commits after that identity;
  the prior W18 audit/evidence is consequently stale under the final-SHA and
  behavior-affecting-change rules.
- Working tree is dirty with unrelated lab, report, and untracked changes;
  no reset, clean, push, or destructive operation was performed. `git diff
  --check` was run; existing whitespace findings are outside W18.
- No package/final-artifact claim is applicable to W18. Private-key bytes were
  not read; only the emitted profile path and non-secret lab status identity
  were inspected.

## Re-verification

Live source review still finds plausible coverage for all 16 requirements:
password/key/certificate/agent discovery, provider-gated keyboard-interactive,
visible classified failures, secret-redacted messages, explicit host-key
accept-new/strict/reject/mismatch behavior, key-type/fingerprint/role prompt
data, and safe cancellation. The W18 test file has meaningful assertions and
no skip/xfail.

Fresh current focused execution:

```text
python -m pytest tests/test_w18_auth_hostkey.py -v -p no:randomly
14 passed in 1.12s
```

The recorded GUI artifact reports 14/14, but it is not freshly bound to the
current HEAD. More importantly, `build/audit/w18-external-matrix.txt` is a
loopback/mock-style `127.0.0.1` matrix from 2026-09-20, not LOCAL_REAL evidence
and not bound to the current repository identity. The LOCAL_REAL protocol
explicitly disallows loopback support evidence as a substitute for required
real external evidence.

Current `lab-status.ps1` independently returned `PASS` with identity
`LOCAL_REAL_HYPERV`, controller `192.168.250.11:22`, valid emitted profile path,
and healthy controller/compute/Slurm services. That health result does not by
itself prove the W18 authentication/host-key GUI journey; a fresh W18
LOCAL_REAL external replay and current-identity evidence artifact are still
required. The lab is available, so this is not an external-authority BLOCKED
condition.

## Findings

### REOPEN-W18-001 — W18 GUI/EXTERNAL evidence is stale and externally invalid

The accepted evidence is tied to `0f8902a...`, while live HEAD is
`f94adb64...`. The external matrix also uses loopback rather than the verified
LOCAL_REAL environment required by `.opencode/protocol/LOCAL_REAL_HPC_LAB.md`.
Refresh the required GUI and real LOCAL_REAL authentication/host-key matrix,
bind it to the current repository HEAD and environment/profile identity, scan
for secret leakage, and run a fresh independent audit.

### REOPEN-W18-002 — W18 predecessor dependency is reopened

W17 currently has canonical decision `REOPEN` for its reopened W16 dependency
and stale GUI evidence. W18 cannot close until W16/W17 are repaired and
re-audited, with any invalidated downstream evidence refreshed.

## Verdict

The current focused test is green and the live implementation remains
consistent with the owned behavior, but stale/misclassified required evidence
and the reopened W17 dependency prevent acceptance. Findings route to the true
owner through resume/repair; no product/test repair was performed.

WAVE_PHASE_STATUS: REOPEN
