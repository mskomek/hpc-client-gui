# V2 + Jobs Integration Checkpoint

Status: **WAVEs 00–11 complete; WAVE 12 code complete, release acceptance blocked**. Integration code is on `codex/integration/v2-jobs-staged-20261021` and has been fast-forwarded to local `develop` through code commit `f6eb59c0bf20d6f5dd3015a0f7bcb258c79fd913`. Final documentation checkpoint is being recorded separately. No remote branch was changed.

The final source gate is bound to tree `450c1d0ddb079122d5aa3efc90516bead03f0797` and fingerprint `bbfbbfad02d5d3b0a2ae7acd143c49ae62349b8136b1bf766c7bd85f729bdbef`. Ubuntu-Test r33 reports zero global architecture violations across 1,015 Python files and 1,041 shared LOC entries. Release acceptance remains blocked by Ubuntu wxPython availability and unresolved Windows portable-suite results.

Start with [the branch source map](BRANCH_SOURCE_MAP.md), [the architecture baseline](ARCHITECTURE_BASELINE.md), and [the wave tracker](WAVE_TRACKER.md). Detailed evidence is in [the integration manifest](INTEGRATION_MANIFEST.json), [test matrix](TEST_MATRIX.md), and [final report](FINAL_INTEGRATION_REPORT.md). Wave reports are recorded in [WAVE_00](WAVE_00.md) through [WAVE_12](WAVE_12.md).

The separate V2 WIP snapshot at `D:\Projeler\.tmp\hpc-client-gui\v2-wip-snapshot-20261021` retains 173 modified/untracked files with fingerprint `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b`. It was preserved unchanged. The main user checkout `D:\Projeler\hpc-client-gui` was also preserved unchanged by this integration work.

No tests were reported from hosted CI. Windows and Ubuntu VM results, including failed, skipped, timed-out, and environment-blocked runs, are separated in [TEST_MATRIX.md](TEST_MATRIX.md). No push, PR, or release was performed.
