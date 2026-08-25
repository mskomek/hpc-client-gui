# Release Process

> Türkçe: [[Release-Process-TR]]

## Consistency gate

`scripts/check_release_consistency.ps1` runs before a release is allowed to
proceed and fails on any mismatch:

- The version in `pyproject.toml`, the package's `__version__`, and the CLI's
  `CLI_VERSION` must all agree with the requested version.
- The release tag must match the requested version.
- `build/windows/version_info.txt` fields — including the version tuple — must
  match.
- The changelog must contain a section for `v<version>`.
- Every required help file must be present.

A release that would ship inconsistent version strings or a missing changelog
entry stops here rather than being published.

## Building the artifacts

```powershell
.\scripts\build_release.ps1 -Version 1.2.6
.\scripts\package_release.ps1 -Version 1.2.6
```

Linux artifacts are produced by `scripts/release_linux.py`, which validates the
AppImage desktop entry, the `AppRun` launcher, and the `.deb` control file
before packaging. See [[Building from Source|Building-from-Source]].

Artifacts land in `dist/releases/v<version>`, each with a `.sha256`.

## The release workflow

`.github/workflows/release.yml` is a manually dispatched workflow with three
inputs: the `version`, an explicit `publish` switch (default `false`, so a
normal dry run never publishes), and a `macos_mode` choice (`signed` by
default, or `unsigned`). It builds all three platforms:

**Linux artifacts (Ubuntu 24.04)** — restores the release dependency cache,
installs the Qt and packaging runtime, runs the shared release preflight test
suite (`scripts/release_test_suite.py`), validates the Linux packaging plan,
installs the Flatpak runtime and the AppImage tool, builds and stages the
artifacts, then runs a packaged CLI smoke test and an offscreen packaged GUI
smoke test before uploading.

**Windows artifacts** — runs the same shared preflight suite, then builds and
packages the Windows onedir ZIP.

**macOS arm64 / x86_64 artifacts** — always build unsigned candidates with the
DevTools-excluded PyInstaller spec, run packaged smoke tests from inside the
built `.app`, record a sorted bundle-size report, and enforce the compressed
DMG size budget (600 MiB by default).

In signed mode, dedicated jobs sign, notarize, and staple each architecture's
candidate; a verification job then mounts both DMGs and checks checksums,
`codesign --verify --deep --strict`, and `spctl --assess` before any metadata
is generated. In unsigned mode, a separate inventory job verifies checksums
and generates disclosure notes instead — it never executes signing tools.

The packaged smoke steps matter: they exercise the artifact that will actually
be published, not the source tree it was built from.

## The final gate

A `release-gate` job evaluates every required job result against the selected
mode (`scripts/release_gate.py`): the four build jobs must succeed in every
mode; signed mode additionally requires both signing jobs plus the signed
verification to succeed, while unsigned mode requires those jobs to be
skipped and the unsigned inventory check to pass. Missing, failed, cancelled,
or unexpectedly skipped results fail the gate. `publish-release` needs the
gate, so publication is impossible until everything above it succeeded.

## Release security metadata

Every verified candidate emits `RELEASE_SECURITY.json`: release version,
source commit, macOS mode (`signed-notarized` or `unsigned`), Developer ID /
notarization / stapling / Gatekeeper outcomes, and the artifact architecture
list. It ships in `MANIFEST.json`, as a release asset, and in the attested
subjects. Unsigned releases also get prominent warning notes explaining that
Gatekeeper may block first launch and that SHA-256/provenance are not
substitutes for Apple code signing. Signed notes may claim signing only after
the verification job succeeded.

## Publishing

Artifacts, their `.sha256` files, `MANIFEST.json`, and `RELEASE_SECURITY.json`
are attached to the GitHub release for the tag. The generated
`RELEASE_NOTES.md` (changelog section plus mode disclosure) is the release
note body — see [[Release History|Release-History]].

## Verifying a published release

```bash
sha256sum -c hpc-client-gui-<version>-x86_64.AppImage.sha256
```

## See also

[[Building from Source|Building-from-Source]] · [[Testing and CI|Testing-and-CI]] · [[Release History|Release-History]]
