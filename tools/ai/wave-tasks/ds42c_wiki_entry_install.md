# DS-42C — Wiki entry and installation cluster (English)

## Outcome

Replace the stub content of exactly these seven files under `docs/wiki/` with
complete, verified English wiki pages:

- `Home.md`
- `Quick-Start.md`
- `Compatibility-and-Support-Matrix.md`
- `Installation-Windows.md`
- `Installation-Linux.md`
- `Installation-From-Source.md`
- `Upgrading-and-Uninstalling.md`

Keep the existing first two lines' pattern: an H1 title, then the language
switch line `> Türkçe: [[<Page>-TR]]`. Do not create, rename, or delete files.

## Source of truth

Read and derive every claim from the repository:

- `README.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE`, `pyproject.toml`
- `src/hpc_gui/docs/HELP_en.md`, `src/hpc_gui/docs/WELCOME_en.md`,
  `src/hpc_gui/docs/CLI_GUIDE_en.md`
- `scripts/release_linux.py`, `scripts/build_release.ps1`,
  `scripts/package_release.ps1`, `.github/workflows/release.yml`

## Content requirements

- Windows: portable ZIP flow (Download → Extract All → run
  `hpc-client-gui.exe`), Python is not required, plink/VcXsrv are optional
  X11-only helpers that are not bundled in the EXE.
- Linux: x86_64 AppImage and `.deb`, `.sha256` verification commands, Flatpak
  as optional, `libegl1`-class Qt platform dependencies, and the fact that X11
  forwarding on Linux uses the system OpenSSH client (`ssh -X/-Y`).
- From source: Python 3.10+, venv, `pip install -e .[test]`, `python -m hpc_gui`,
  and the identical CLI entry point.
- `Quick-Start.md` reproduces the canonical "first job in 5 minutes" flow from
  `HELP_en.md` without contradicting it.
- `Compatibility-and-Support-Matrix.md` derives from the `HELP_en.md` support
  matrix and the artifacts the release tooling actually produces.
- `Home.md` must state that the wiki is generated from `docs/wiki/` in the main
  repository and must not be edited on github.com, link the canonical docs, and
  give a short navigation overview by section.
- `Upgrading-and-Uninstalling.md` must state that application data lives in
  `~/.truba_slurm_gui` (legacy directory name retained for compatibility).
- Internal wiki links use `[[Page-Name]]` form and must target a file that
  exists in `docs/wiki/`.

## Forbidden

- Unverified distro claims, ARM64 claims, package-manager repositories that do
  not exist, and any download link not present in the repository.
- Any mention of `waves/`, `.agent-runs/`, DeepSeek, or internal AI
  orchestration tooling.
- Editing any file other than the seven listed pages.

## Acceptance

- Every command block is runnable as written on the stated platform.
- Every version string matches `pyproject.toml`.
- No page promises a platform or format the project does not publish.
- No corrupted branding token (`Lreate`, `LLI`, `conoig`, `JSnN`, `HPL`).
