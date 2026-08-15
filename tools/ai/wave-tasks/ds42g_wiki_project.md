# DS-42G — Wiki contributor and project cluster (English)

## Outcome

Replace the stub content of exactly these eleven files under `docs/wiki/`:

`Architecture.md`, `Building-from-Source.md`, `Release-Process.md`,
`Testing-and-CI.md`, `Contributing.md`, `Licensing-and-Commercial-Use.md`,
`Support-and-Donations.md`, `Release-History.md`, `Glossary.md`,
`Slurm-Help-Library.md`, `Job-Script-Templates.md`.

Keep the existing pattern: an H1 title, then `> Türkçe: [[<Page>-TR]]`.
Do not create, rename, or delete files.

## Source of truth

- `src/hpc_gui/docs/ARCHITECTURE.md`, `CHANGELOG.md`,
  `HELP_LIBRARY_GENERIC_en.md`
- `templates/template_cpu.slurm`, `template_gpu.slurm`, `template_mpi.slurm`
- `scripts/release.ps1`, `scripts/build_release.ps1` (including `-Offline` and
  the `.cache/release` reuse behavior), `scripts/package_release.ps1`,
  `scripts/release_linux.py`, `scripts/check_i18n.py`, `scripts/smoke_test.py`,
  `scripts/linux_release_smoke.py`
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- `LICENSE`, `COMMERCIAL_LICENSE.md`, `THIRD_PARTY_NOTICES.md`,
  `SUPPORT.md`, `.github/FUNDING.yml`

## Content requirements

- `Architecture.md` summarizes the real layer split (`ui`, `services`, `ssh`,
  `config`, `core`), including the rules that Qt UI stays thin and that long
  SSH/transfer/process work stays off the GUI thread.
- `Building-from-Source.md` and `Release-Process.md` document the named scripts
  and the checksum and consistency checks.
- `Testing-and-CI.md` documents the offline test suite, the helper checks, and
  both workflows, including the preserved Windows release gate.
- `Contributing.md` states the contribution channel, the rule that Turkish and
  English resources are updated together for visible strings, and the licensing
  implication of contributing under PolyForm Noncommercial.
- `Licensing-and-Commercial-Use.md` reproduces the v1.2.0 boundary accurately:
  the pre-1.2.0 MIT grant is not revoked for already-distributed copies.
- `Slurm-Help-Library.md` and `Job-Script-Templates.md` derive from
  `HELP_LIBRARY_GENERIC_en.md` and the three bundled templates.
- `Release-History.md` links `src/hpc_gui/docs/CHANGELOG.md`; it does not
  restate or rewrite history.
- Internal wiki links use `[[Page-Name]]` and must target existing files.

## Forbidden

- Rewriting the changelog.
- Restating license terms in a way that narrows or broadens `LICENSE`.
- Documenting internal orchestration tooling: no mention of `waves/`,
  `.agent-runs/`, DeepSeek, OpenCode, or AI delegation on any page.
- Editing any file other than the eleven listed pages.

## Acceptance

- Every script and workflow named in the wiki exists at the stated path.
- License wording is consistent with `LICENSE` and `COMMERCIAL_LICENSE.md`.
- No page references internal AI-orchestration workflow or files.
- No corrupted branding token (`Lreate`, `LLI`, `conoig`, `JSnN`, `HPL`).
