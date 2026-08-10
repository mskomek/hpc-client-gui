# WAVE_19 / DS-19B analysis

Goal: map the existing offline transfer or SFTP harness and determine the smallest CI change that gates upload, download, listing, and checksum coverage.

In scope: `.github/workflows/ci.yml`, existing transfer tests, mock servers, test helpers, and package requirements.

Forbidden: new servers, production behavior, external environment actions, release publication, and unrelated refactors.

Acceptance: identify existing tests that already cover the required operations, the exact CI command or step needed, required dependencies, and any platform or timing risks. Return evidence with paths and line references; findings only.
