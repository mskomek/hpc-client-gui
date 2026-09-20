# W12 Audit Report

**Decision: PASS**

Audited exactly `W12` against `waves/pending/W12.md` in fresh context. The
pending definition is present and unambiguous; no `waves/bak/` material was
used.

## Authority and scope

- Read `CORE_EXECUTION_RULES.md`, `W12.md`, and `30_AUDIT_WAVE.md`.
- Read all 15 owned registry rows `HPC-W03-SFTP-001..015`, the W12 index
  entries, and confirmed W12 owns no TODO rows.
- Read Workstream B of `WAVE_V2_FINAL_03.md` (SFTP steps 1–13 and hash
  requirement).
- Cross-Wave boundary is respected: SSH lifecycle remains W11 and Slurm
  remains W13; no W13 work was started.

## Repository/plugin and diff audit

- Main: `develop`, HEAD
  `0f8902a023bac76071527232c2287af96478ed2b`.
- Plugin: `develop`,
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; only the pre-existing
  untracked social-preview image is present there.
- Existing unrelated working-tree changes were preserved. The W12 product
  changes are limited to the SFTP error-translation paths in
  `services/files_ssh.py` and wx file-view progress forwarding in `wx_shell.py`;
  the W12 regression module is `tests/test_w12_sftp_semantics.py`.
- Full relevant diff was inspected; `git diff --check` is clean. No secrets,
  generated/binary noise, weakened tests, skips, or xfails were found.

## Verification

- Focused regression suite rerun: `python -m pytest tests/test_w12_sftp_semantics.py -q`
  → **13 passed** (including real wx `App`/`Frame` button-event tests).
- External evidence independently rerun against authorized `hpclab` at
  `127.0.0.1:2222` using the product `SSHFilesBackend`: **14/14 PASS**.
  The run covered all 15 rows, including real permission/missing-path
  filename attribution, overwrite/cancel byte preservation, Unicode/space
  paths, hash equality (`82f100670e8176a0`), and forced mid-transfer
  disconnect (`OSError` after callbacks, no false success).
- Lab identity was checked (`healthy`, `sinfo` idle node, `slurmctld UP`). The
  disposable W12 fixture was removed and verified absent; the pre-existing
  container remained healthy. The fixture password was not recorded in the
  report/evidence.
- The report’s baseline, sensitivity, broader regression, GUI, and diff
  evidence was re-read. The two claimed P1 fixes each have pre-fix failure and
  post-fix success proof; the reported native/timing flakes were rerun green
  and are outside the touched behavior.

## Requirement trace verdict

`HPC-W03-SFTP-001..015` each has a live implementation owner, behavioral test
or proof, and current matrix/external evidence in `W12_WAVE_REPORT.md`.
GUI evidence is real wx runtime/event evidence, not static-only inspection;
external evidence is real infrastructure, not a mock substitution. No owned
P0/P1/P2/P3 finding remains, and no cross-Wave ownership escape was identified.

W12 satisfies its GUI and EXTERNAL evidence classes and is ready for closeout.
