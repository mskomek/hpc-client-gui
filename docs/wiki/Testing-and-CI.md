# Testing and CI

> Türkçe: [[Testing-and-CI-TR]]

## The test suite is offline

Tests run without a cluster. Fake file and Slurm layers stand in for the remote
side, which is why the suite can exercise transfer, editor, and job flows in
CI. No test performs a real cluster operation.

```bash
pip install -e .[test]
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

`QT_QPA_PLATFORM=offscreen` lets the Qt tests run without a display.

## Helper checks

| Script | Checks |
|---|---|
| `scripts/check_i18n.py` | Turkish/English key parity, hardcoded UI strings, and missing translation references |
| `scripts/check_branding.py` | The corrupted user-visible strings from the branding rename cannot return |
| `scripts/check_wiki.py` | Wiki link resolution, EN/TR page parity, heading parity, sidebar completeness, orphan pages, forbidden terms, and asset references |
| `scripts/smoke_test.py` | A basic application smoke test |
| `scripts/linux_release_smoke.py` | A smoke test against the packaged Linux artifacts |
| `scripts/check_release_consistency.ps1` | Version, tag, changelog, and help-file consistency for a release |

## Continuous integration

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`. Every
job is blocking.

| Job | Runner | What it runs |
|---|---|---|
| `cli` | ubuntu | Compile check, i18n drift gate, smoke test, and the CLI test suite |
| `docs` | ubuntu | The branding string gate and the wiki source gate |
| `ssh_sftp` | ubuntu | The session, transfer, and transfer-gate suites |
| `windows` | windows | The Windows boundary tests: safe download, version consistency, startup changelog |
| `gui` | ubuntu | The full offline suite, including the Qt tests, offscreen |

The `windows` job is deliberately preserved: it covers behavior that only
differs on Windows, and dropping it would leave the primary target platform
untested.

## Release CI

`.github/workflows/release.yml` is separate and manually dispatched. It builds
both platforms and runs packaged smoke tests against the real artifacts before
upload. See [[Release Process|Release-Process]].

## Before you open a pull request

```bash
PYTHONPATH=src python scripts/check_i18n.py
python scripts/check_branding.py
python scripts/check_wiki.py
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

## See also

[[Contributing|Contributing]] ·
[[Architecture|Architecture]] ·
[[Building from Source|Building-from-Source]]
