# WAVE 03 result — release packaging verification

## Status

**Blocked pending the x86_64 dependency fix.** Verification run
`33072931357` was executed from merge commit `75d236ce` with
`publish=false` and `macos_mode=unsigned`. No release was published.

## Observed results

| Job | Result | Finding |
| --- | --- | --- |
| macOS arm64 artifacts | passed | build, GUI smoke, staging, and artifact upload passed |
| Linux artifacts | passed | packaging and smoke checks passed |
| Windows artifacts | passed | release preflight and artifact build passed |
| macOS x86_64 artifacts | failed | packaged GUI smoke could not load cryptography |
| Final release gate | failed | correctly blocked publication because x86_64 failed |
| Publish GitHub Release | skipped | expected because gate failed and `publish=false` |

## x86_64 failure

The packaged application failed before DMG creation completed:

```text
ImportError: Symbol not found: _SSL_get0_group_name
Expected in: .../Contents/Frameworks/libssl.3.dylib
```

The failing extension was
`cryptography/hazmat/bindings/_rust.abi3.so`. The release lock used
`cryptography==50.0.0`, which is incompatible with the macOS x86_64 release
target. Develop already contains the compatibility pin
`cryptography==48.0.1` and a focused regression test.

## Verification boundary

The symlink staging optimization is validated on arm64 and in the PR checks;
the arm64 release candidate was uploaded successfully. x86_64 must be rerun
after the dependency pin reaches `main`. Only then can the two DMG sizes,
checksums, manifest, security metadata, and final release gate be accepted.

The Node.js 20 messages are deprecation annotations from GitHub Actions and
are not the cause of this failed run.

## Next action

Send only the x86_64 compatibility change through a protected PR, rerun this
verification with `publish=false`, and inspect both macOS candidate DMGs.
Do not publish v1.5.1 until the x86_64 job and final release gate pass.
