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

GitHub Actions CI is intentionally disabled. The former workflow is preserved
at `docs/ci-disabled/ci.yml`, outside `.github/workflows/`, so normal pushes
and pull requests do not create CI runs. Repository validation is currently
performed locally; see `docs/REMEDIATION_STATUS_2026-09-11.md`.

No CI job is claimed to be passing after this change.

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

[[Contributing|Contributing]] · [[Architecture|Architecture]] · [[Building from Source|Building-from-Source]]
