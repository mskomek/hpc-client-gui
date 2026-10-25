# V2 + Jobs Integration Checkpoint

Status: **r17 VM acceptance complete; local integration branch is `READY_FOR_DEVELOP_MERGE`.** The r17 source overlay is committed at `5861ec6b296e8a48236aaa72c87abe9ec59edd4f` on `codex/integration/v2-jobs-staged-20261021`. Local `develop` remains at `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`; the separate develop checkout was preserved because it contains the validation overlay and unrelated untracked `uname` files.

The source identity is the base SHA plus the 39-file r17 overlay fingerprint `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`. Kole Ubuntu-Test and Windows11-New release acceptance passed, the global architecture check found 0 files over 500 lines, and Linux/Windows package builds and smoke checks passed. GitHub Actions was not run.

Start with [the branch source map](BRANCH_SOURCE_MAP.md), [the architecture baseline](ARCHITECTURE_BASELINE.md), and [the wave tracker](WAVE_TRACKER.md). Current acceptance evidence is in [WAVE 12](WAVE_12.md), [the r17 VM record](VM_ACCEPTANCE_2026-10-24.md), [the test matrix](TEST_MATRIX.md), and [the final report](FINAL_INTEGRATION_REPORT.md). Historical earlier VM attempts remain in [VM_RERUN_2026-10-22.md](VM_RERUN_2026-10-22.md).

The separate V2 WIP snapshot and the main user checkout `D:\Projeler\hpc-client-gui` remain preserved. The Jobs and V2 source branches were not changed. No push, PR, GitHub Release, or hosted workflow was performed.
