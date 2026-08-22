# Publication Kit

Copy-paste ready material for presenting HPC Client GUI externally. Nothing on
this page may be posted or submitted anywhere without the owner's explicit
per-item approval (see "Approval boundary").

## Canonical name

`HPC Client GUI` (repository: `mskomek/hpc-client-gui`, package: `hpc-client-gui`)

## Short description (≤ 90 chars)

> Cross-platform desktop SSH/SFTP/Slurm client for HPC clusters. No server-side service.

## One-sentence pitch

HPC Client GUI is a cross-platform desktop application that gives researchers
SSH access, an SFTP file manager with resumable transfers, Slurm job
monitoring, and an integrated terminal — using only standard cluster access,
with nothing to install on the server side.

## Catalog description (≈90 words)

HPC Client GUI is a desktop client for Slurm-based HPC systems on Windows and
Linux. It combines SSH session management, an SFTP file browser with
resumable/cancellable transfers and conflict handling, Slurm job monitoring
and basic operations (`squeue`/`sacct`/`scontrol` views), a script editor with
submit/run-in-terminal actions, and an embedded SSH terminal. The client talks
to clusters over standard SSH/SFTP only — no server-side daemon or database is
required. Packaged releases ship as a portable Windows ZIP plus Linux
AppImage/deb/Flatpak artifacts with SHA-256 checksums, `MANIFEST.json`, and
signed build-provenance attestations. Licensed under PolyForm Noncommercial
1.0.0; commercial use requires a separate license.

## Community post template (150–250 words)

> **HPC Client GUI — Windows/Linux desktop client for Slurm clusters (feedback welcome)**
>
> I maintain HPC Client GUI, a desktop client for Slurm-based HPC systems:
> SSH session management, an SFTP file manager with resumable transfers and
> conflict prompts, Slurm job monitoring through `squeue`/`sacct`/
> `scontrol` views, a job-script editor, and an embedded terminal. It works
> over plain SSH/SFTP, so there is no server-side service to install — if you
> can SSH to your cluster, the client should work.
>
> Platforms: Windows (portable ZIP, no Python needed) and Linux
> (AppImage/deb/Flatpak). X11 forwarding exists as an optional helper path on
> Windows and via system OpenSSH on Linux. Current limitations are documented
> in the README/wiki rather than hidden.
>
> I am looking for feedback from people on other Slurm sites: which defaults
> feel wrong, which scheduler outputs break parsing, what a first-time user
> misses. Compatibility reports from non-TRUBA clusters are especially useful
> and there is a read-only validation kit for exactly that.
>
> License: PolyForm Noncommercial 1.0.0 (free for research/personal use;
> commercial use needs a separate license).
>
> Repository and issues: https://github.com/mskomek/hpc-client-gui

## Feature bullets

- SSH session management (password/key auth, strict host-key option)
- SFTP remote file manager: browse, copy/move/paste, drag & drop, resume,
  progress/cancel, undo-move
- Parallel transfers with per-file isolated SFTP channels and pipelined writes
- Slurm job monitoring and basic operations (`squeue`, `sacct`, `scontrol`,
  submit, cancel)
- Job-script editor with submit / run-in-terminal actions
- Embedded SSH terminal
- Optional X11 forwarding (plink/VcXsrv helpers on Windows; system OpenSSH on Linux)
- CLI for profiles, diagnostics, files, and jobs (`python -m hpc_gui`)
- Turkish/English UI
- Site command overrides via system templates (TRUBA preset included as an example adapter)

## Platforms / install formats

| platform | formats | notes |
|---|---|---|
| Windows 10/11 x86_64 | portable one-dir ZIP (+ `.sha256`) | no Python required |
| Linux x86_64 | AppImage, `.deb`, Flatpak (+ `.sha256`) | Qt runtime bundled |

Every release also publishes `MANIFEST.json` (size+SHA-256 inventory) and
signed build-provenance attestations — see `docs/VERIFYING_RELEASES.md`.

## Technical requirements

- Client: Windows 10+/modern Linux desktop; PySide6 runtime is bundled in packages
- Cluster: standard OpenSSH server + SFTP subsystem; Slurm commands on PATH for job features
- Optional X11: plink.exe + VcXsrv (Windows), system `ssh -X/-Y` (Linux)

## License disclosure (use verbatim where required)

> HPC Client GUI is licensed under the PolyForm Noncommercial License 1.0.0.
> Free for personal, academic, educational, public-research, and other
> permitted noncommercial use. Commercial use requires a separate license
> from the author. Releases before v1.2.0 were distributed under MIT.

Not OSI-approved open source; please do not describe it as "open source"
without this qualification.

## TRUBA disclaimer (include wherever TRUBA is mentioned)

> TRUBA compatibility means the client targets the same standard SSH + Slurm
> interfaces used by TRUBA centers. HPC Client GUI is an independent project
> and is not affiliated with, endorsed by, or officially connected to TRUBA,
> TÜBİTAK, UHeM, or any university/HPC center.

## Screenshots / demo

- Hero overview: `docs/wiki/assets/overview.png`
- Files/Jobs/editor/settings assets live beside it; all are generated offline
  from fabricated data (`scripts/capture_wiki_screenshots.py`).

## Issue / support links

- Issues: https://github.com/mskomek/hpc-client-gui/issues
- Security policy: https://github.com/mskomek/hpc-client-gui/security/policy
- Support notes: `SUPPORT.md`

## Compatibility wording rules

- Say **designed for** standard SSH + Slurm systems.
- Say **expected compatible** when untested but plausible.
- Reserve **verified on** for environments with a saved sanitized report from
  `docs/COMPATIBILITY_VALIDATION.md`. Today: none published yet.

## Keywords / topics (GitHub metadata)

Current repository topics already cover the suggested families:
`hpc slurm ssh sftp remote-computing scientific-computing desktop-app windows
linux pyside6 x11 truba` plus `slurm-job-scheduler slurm-workload-manager
ssh-client sftp-client hpc-client slurm-gui cluster`.

Recommended GitHub description (current text already matches):

> Cross-platform desktop client for Slurm HPC clusters — SSH, SFTP, remote
> files, job management, CLI and optional X11.

Optional trims (synonym reduction, apply only if the owner wants fewer tags):
drop `slurm-job-scheduler` or `slurm-workload-manager` (keep `slurm`), drop
`sftp-client`/`ssh-client` (keep `ssh`/`sftp`). Do not add more synonyms.

## Catalog target register (researched 2026-08-22; do not submit without approval)

| target | category | likely fit | license constraints to check | submission method | status | notes |
|---|---|---|---|---|---|---|
| dstdev/awesome-hpc | GitHub awesome list (HPC software/tools) | good — explicitly collects software/tools | list license not stated; PR contribution | PR adding one line under software/tools section | candidate | ~268★; verify section placement first |
| trevor-vincent/awesome-high-performance-computing | GitHub awesome list (resources) | moderate — list is education/resource heavy; software entries exist | check CONTRIBUTING/practice via recent PRs | PR | candidate | 1.3k★; pick exact subsection |
| Research Software Directory (research-software-directory.org) | research-software catalog | good if framed as research software | RSD asks for open/reusable software; confirm PolyForm Noncommercial acceptance + maintainer expectations | sign-in web form ("add software"), then curation | candidate | run by NL eScience Center; entry fields map to kit sections |
| helmholtz.software (RSD instance) | research-software catalog | **not eligible** | restricted to Helmholtz-affiliated employees | n/a | excluded | affiliation requirement documented on site |
| r/HPC (Reddit) | community discussion | good for the feedback post | subreddit self-promotion rules; disclose authorship | manual post by owner | candidate | use Community post template verbatim |

### Tailored submission blocks

**dstdev/awesome-hpc (PR body sketch)**

> Adds [HPC Client GUI](https://github.com/mskomek/hpc-client-gui) under the
> tools/software section: a cross-platform desktop SSH/SFTP/Slurm client for
> HPC clusters (Windows portable ZIP; Linux AppImage/deb/Flatpak). Works over
> standard SSH only — no server-side component. PolyForm Noncommercial 1.0.0.

**Research Software Directory (entry fields mapping)**

- Title/subtitle: HPC Client GUI — desktop SSH/SFTP/Slurm client for HPC clusters
- Description: reuse "Catalog description" above
- Repository: https://github.com/mskomek/hpc-client-gui
- License: PolyForm Noncommercial 1.0.0 (state plainly during review)
- Screenshots: hero asset path above
- Contact/maintainer: repository owner

**r/HPC post**

- Use the "Community post template" unmodified; answer rule questions about
  affiliation honestly (independent project).

## Adoption evidence tracker

Record outcomes here as they happen (append-only, dated). No telemetry exists
in the app; numbers come from the owner manually.

```markdown
### <date> — <what>
- kind: compat-report | external issue | download stats | catalog submission
- detail: <cluster label / issue link / counts / target + outcome>
- artifact: docs/compat-reports/<slug>.md (if any)
```

## Approval boundary

For every external action: owner sees the exact final text → owner picks the
destination → current rules/links re-checked → only then is it published by an
authorized person/tool. No automated submissions exist in this repository.
