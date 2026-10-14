# Candidate6 exhaustive packaged UI and real lab acceptance

**Verdict: `FULL_ACCEPTANCE_BLOCKED_LAB_UBUNTU_TEST_HPC_SERVICES_ABSENT_AND_WINDOWS11_SSH_NETWORK_TIMEOUT`**

This is a partial acceptance record, not a full acceptance. Candidate6 has a confirmed window sizing defect at the Windows 11 guest default display size. Candidate7 fixes the measured layout case and passes the focused packaged keyboard journey. The source-based catalog covers 152 action rows: 5 PASS, 1 FAIL, 144 BLOCKED/unexecuted, and 2 NOT_APPLICABLE. The user has directed us to accept the virtual Ubuntu-Test system as the lab target because its system power is comparable. Its read-only inventory confirms SSH/SFTP, but no active Slurm, MUNGE, accounting database, or NFS stack. The user supplied the ED25519 fingerprint from the Ubuntu console. I verified it against the host’s already-trusted key and saved the matching ED25519 key to the Windows11 app profile. The latest SSH attempt timed out before key exchange, so the packaged GUI lab journey remains unrun.

## Frozen Candidate6 identity

- Source commit: `d40f03d0289be158294241b8542e64ba6a0947be`
- EXE SHA-256: `67f60b50f1ea0ff45347b1c9afa942eb12172b21523d67011ec2d28e9379aae6` (7,549,252 bytes)
- Package ZIP SHA-256: `41714332b3fbf6568684e2baf14339e7377240bdbb52835131c933692fd1d212` (27,998,208 bytes)
- Frozen package and prior report are preserved under `artifacts/candidate6/`.

## Candidate6 findings

The exact Candidate6 package launched on the Windows 11 guest as `test\home`, session 2, from a fresh isolated configuration root. A real Tab/Enter sequence opened **Add Connection**; a second Tab/Enter sequence activated **Cancel**; the app exited with code 0. Those actions passed.

At 1366×768, the observed frame rectangle was `[0,0,1386,788]` and Add Connection was `[36,706,108,23]`. The frame exceeded the display and the button overlapped the work-area/taskbar edge. This is a product failure. Evidence is in `artifacts/candidate6-full-e2e/runtime-add-cancel.json` and `artifacts/candidate6-full-e2e/screenshots/`.

## Candidate7 focused repair result

Repair branch: `codex/c6-full-e2e-fix`, based on the Candidate6 source commit. The repair clamps fresh and restored geometry to the available work area and derives a minimum size from display work areas. Focused geometry tests passed (`5 passed`); the changed-source architecture validator passed for four files, with `wx_shell_frame.py` at 463 LOC. The Windows onedir package built successfully.

- EXE SHA-256: `a95a71c3b296d279f548330598e9e1e44f468b32bc0514f056b376deae600266` (7,550,025 bytes)
- Package ZIP SHA-256: `9085561a41e1a83a1ee4235ebe68922e9354af785b7b39bcac0f6ff3a6420f80` (28,848,723 bytes; 157 files)
- Candidate7 EXE and ZIP are copied under `artifacts/candidate7-validation/` with the matching manifest.
- Guest runner verified host and guest EXE hashes match, interactive Explorer session belongs to `test\home`, timeout false, cleanup completed.
- At 1366×768, measured work area was 1366×728, Candidate7 frame rectangle `[-8,-8,1382,736]`, and Add Connection rectangle `[28,646,108,23]`; its bottom is y=669, within the work area. Candidate7 passed the same Add Connection → Cancel → exit journey.
- DPI scale was not measured. 1280×720, 1920×1080, and other requested size/scale combinations were not run.

The Candidate7 repair is only a targeted fix. It does not establish complete Candidate7 acceptance or authorize replacement of the frozen Candidate6 artifact.

## Virtual lab accepted by user direction

Ubuntu-Test is accepted as the test lab target for this pass. The live Hyper-V status showed it running with 8 vCPUs and 4.67 GB assigned memory. The user supplied the Linux username `test`; canonical SSH doctor passed, and the inventory ran from the host over its configured strict SSH trust.

The guest reported Ubuntu 24.04.5, Linux 7.0.0-38-generic, 4.4 GiB memory, and 97 GB root storage with 82 GB free. SSH was active and SSH/SFTP tools were present. MUNGE, Slurm controller/worker, MariaDB/MySQL accounting, and NFS services were inactive; `srun`, `sinfo`, `sbatch`, `sacct`, and `squeue` were absent. This confirms comparable VM resources while limiting actual HPC feature acceptance. No services were installed or changed.

Full inventory: `artifacts/candidate7-validation/virtual-lab-inventory.json`. The console fingerprint supplied by the user is `SHA256:KEFEY0srtHIesFWiooG697/hyEYhhTYL6U2pwH12STQ`. It matched the host’s trusted ED25519 key. I saved that public host key to `C:\Users\home\.truba_slurm_gui\known_hosts` for `172.23.44.150`; the file now reports the same fingerprint. No passwords or private keys were accessed. The latest strict SSH attempt timed out before key exchange, so the app cannot yet complete its lab connection journey.

## LOCAL_REAL baseline record

The separate LOCAL_REAL status check passed on 2026-10-09 at 18:48:04 UTC. It remains supplemental historical infrastructure evidence. No packaged Candidate6/Candidate7 GUI connect, job, terminal, directory, transfer, or accounting journey was run against LOCAL_REAL or Ubuntu-Test.

The current inventory lacks isolated endpoints/fixtures for MFA, host-key mismatch/rotation, a jump host, X11, quota, controlled latency/packet loss, and large/resumable transfers. These are recorded in `artifacts/candidate6-full-e2e/LOCAL_REAL_CAPABILITY_MATRIX.json`; no security controls or shared services were changed.

## Coverage and evidence

- `artifacts/candidate6-full-e2e/UI_ACTION_CATALOG.json` is a source-based action inventory with source references. Dynamic plugin, template, path, output-channel, and document cardinality remains open-ended.
- `artifacts/candidate6-full-e2e/UI_ACTION_COVERAGE.csv` records 152 per-action rows. BLOCKED means unexecuted in this acceptance pass; it does not imply a product failure.
- `artifacts/candidate6-full-e2e/UI_LAYOUT_MATRIX.json` records the measured Candidate6 failure and Candidate7 repair plus the unrun cases.
- `artifacts/candidate7-validation/ui-interaction.json`, `runner-result.json`, `candidate7-validation-manifest.json`, and screenshots contain the focused Candidate7 evidence.
- The original Candidate6 report `artifacts/CANDIDATE6_FINAL_ACCEPTANCE_20261009.md` documents earlier smoke-only evidence. It is not an exhaustive acceptance report.

The requested exhaustive action-handler coverage, full layout/DPI matrix, packaged Ubuntu-Test connection/session journeys, and isolated HPC service fixtures remain outstanding. Accordingly, this record does not claim Candidate6 or Candidate7 fully accepted.
