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

`.github/workflows/release.yml` is a manually dispatched workflow that takes
the version as an input and builds both platforms:

**Linux artifacts (Ubuntu 24.04)** — restores the release dependency cache,
installs the Qt and packaging runtime, runs the source checks, validates the
Linux packaging plan, installs the Flatpak runtime and the AppImage tool,
builds and stages the artifacts, then runs a packaged CLI smoke test and an
offscreen packaged GUI smoke test before uploading.

**Windows artifacts** — builds and packages the Windows onedir ZIP.

The packaged smoke steps matter: they exercise the artifact that will actually
be published, not the source tree it was built from.

## Publishing

Artifacts and their `.sha256` files are attached to the GitHub release for the
tag. The changelog section for that version is the release note source — see
[[Release History|Release-History]].

## Verifying a published release

```bash
sha256sum -c hpc-client-gui-1.2.6-x86_64.AppImage.sha256
```

## See also

[[Building from Source|Building-from-Source]] · [[Testing and CI|Testing-and-CI]] · [[Release History|Release-History]]
