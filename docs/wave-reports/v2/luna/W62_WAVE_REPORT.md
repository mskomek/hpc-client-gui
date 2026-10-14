# W62 Wave Report

## U02 — W57 frozen artifact identity reconciliation

**Requirement:** `HPC-W62-BASE-002`  
**Disposition:** `MISMATCH` — the historical W57 input remains unavailable in the bounded search scope.

The U02 receipt was checked against `W57_FREEZE_DECLARATION.md`, the W57.4 evidence manifest, W62 Candidate-10 provenance, and the available executable. Both current and frozen declarations name `dist/hpc-client-gui/hpc-client-gui.exe`, so the file is one shared observation, not independent evidence of frozen bytes.

The available executable independently hashes to `DB29B6A8BD2C78FE1D9169F36B595752DEC40F411085AB8E6032384E740BBFBD` and is 7,675,423 bytes. This matches the U02 receipt and differs from both the current executable declaration (`8B51407C7040CC12EE5E161B6797F44C83069FC404F75EE974F5FDA03AA8BB20`, Candidate-10) and the W57 frozen declaration (`B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD`, 7,672,106 bytes). Candidate-10 provenance's prior observed hash was mistyped; its W62-owned record now carries the recomputed value. No historical declaration or executable was changed.

The separately retained frozen artifact was not found in the bounded search recorded by `artifacts/wave_W57.4/W57.4_REPAIR_EXACT_ARTIFACT_RECOVERY.json`: current designated artifact; retained W57-named `.tmp` candidate directories; W57.1–W57.3 directories; known distinct declaration-listed builds; and nine additional repository `artifacts` executable/archive candidates. The receipt reports no exact match. Other retained storage remains unsearched, so global absence is not claimed. The prior search was not repeated.

**Evidence:** `artifacts/refactored-v2/w62/W57_FROZEN_ARTIFACT_SHA256_RECONCILIATION.json`; `artifacts/refactored-v2/w62/CANDIDATE10_PROVENANCE.json`; `artifacts/wave_W57.4/W57.4_REPAIR_EXACT_ARTIFACT_RECOVERY.json`.

**Current disposition:** Preserve the mismatch and unavailable historical-input status. Do not treat the shared-path DB29B6A8 executable as the W57 frozen artifact or transfer historical PASS evidence to it.

## U06 — Legacy freeze-debt forward routing

**Requirement:** `HPC-W62-BASE-006`  
**Disposition:** `PARTIAL_FORWARD_ROUTING; ITEMIZED_LEDGER_UNAVAILABLE`

The W62 receipt `artifacts/refactored-v2/w62/LEGACY_FREEZE_DEBT_REBIND.json` records aggregate routing without reopening historical Waves: W57.4's artifact identity and successor-authority debt remains with W62 for candidate authority and proceeds to W73 for final acceptance/freeze; W61.1–W61.4 release decision, NO-GO, handoff, and package-census debt is assigned to W73. These routes follow the successor routing authority. No candidate-bound rebind or closure is claimed.

The expected six-entry successor evidence ledger was not present in the bounded W62 evidence paths inspected. I did not invent item IDs or per-entry dispositions. U03 remains `AWAITING_INPUT`, with no successor candidate authority, so the receipt preserves this limitation and requires importing the authoritative entries and binding them after release-owner authorization.

## Current repair dispatch — identity and materialization reconciliation

**Dispatch:** `20261012-184650-167f2810:5:W62:repair`  
**Candidate identity:** `103399427530f30878f01b77b4937eafbac4a68da7596f62d82ee7f92a35e74e`  
**Current EXE:** `dist/hpc-client-gui/hpc-client-gui.exe`, SHA-256 `db29b6a8bd2c78fe1d9169f36b595752dec40f411085ab8e6032384e740bbfbd`, 7,675,423 bytes. It differs from the declared Candidate-10 and W57 hashes. The EXE identity was recomputed; six JSON receipts referenced by the reconciliation were parsed and hashed. Candidate-10 source commit `8177ee9c0992f6a3d6285b146f64abef1192b064` resolves to tree `05b9d456fef4217699a992cf5cf8d45dac30177d`. The previously bounded artifact searches were not repeated.

Official `setup/materialize-ac-core.py --verify-only` completed for this dispatch with exit code 0. Candidate guard and configured validators (`validate-ac-project`, agent parity, source architecture, Wave authoring, Wave orchestration) passed in scratch. Verify-only made no managed-mirror writes. This is materialization evidence only; it does not close Candidate-10/W57 bytes, successor authorization, itemized ledger, or packaged GUI requirements.

The current-dispatch receipt is `artifacts/refactored-v2/w62/U01_U02_CURRENT_IDENTITY_RECONCILIATION.json`; materialization receipt is `artifacts/refactored-v2/w62/U06_MATERIALIZATION_VERIFY_ONLY.json`. `artifacts/wave_W62/WAVE_W62_EVIDENCE_MANIFEST.json` binds these current-dispatch records and records retained U04/U05 receipts as context only. Requirements remain explicitly unresolved where required authority or bytes are absent. No historical declaration or artifact was modified.
