# WAVE_19 / DS-19A analysis

Goal: map the existing CI workflow and offline test commands needed to add the repository's unit and integration suite to CI.

In scope: `.github/workflows/ci.yml`, existing test configuration, offline tests, and focused CI helper scripts.

Forbidden: production application behavior, external environment actions, release publication, and unrelated refactors.

Acceptance: identify the smallest CI-only change, the correct source-path setup, useful failure-output handling, and exact commands that can run offline. Report evidence with file paths and line references; return findings only.
