# DS-42D — Wiki feature reference cluster (English)

## Outcome

Replace the stub content of exactly these ten files under `docs/wiki/` with
complete, verified English wiki pages:

`Connecting-and-Profiles.md`, `Remote-File-Manager.md`, `File-Transfers.md`,
`Slurm-Jobs.md`, `Job-Outputs.md`, `Script-Editor.md`,
`Terminal-and-Remote-Commands.md`, `X11-Forwarding.md`,
`Settings-Reference.md`, `Interface-Language-and-i18n.md`.

Keep the existing pattern: an H1 title, then `> Türkçe: [[<Page>-TR]]`.
Do not create, rename, or delete files.

## Source of truth

Ground every page in the actual modules under `src/hpc_gui/`:

- `login_widget`, `connection_dialog`
- `ftp_widget`, `remote_dir_panel`, `local_dir_panel`, `file_clipboard`,
  `transfer_controller`, `transfer_conflict_dialog`
- `jobs_widget`, `jobs_outputs_widget`, `slurm_ssh`, `slurm_script_parser`
- `editor_widget`
- `terminal_emulator`, `terminal_input`, `command_history_store`
- `x11_runner`, `x11_system_ssh`, `xserver_manager`, `putty_manager`
- `settings_dialog`, `core/i18n`, `i18n/en.json`

Also read `src/hpc_gui/docs/HELP_en.md` — keyboard shortcuts and setting labels
must match it (or the i18n resource string) exactly.

## Content requirements

- Document copy/move/paste, drag and drop, resumable transfer, progress and
  cancel, undo-move, and conflict resolution exactly as implemented.
- `X11-Forwarding.md` must state the two distinct paths explicitly: Windows uses
  `plink.exe -X` plus VcXsrv (downloaded only on user approval, not bundled);
  Linux uses the system OpenSSH client `ssh -X/-Y` and requires `DISPLAY`. Do
  not promise plink/VcXsrv behavior on Linux.
- `Settings-Reference.md` must enumerate every setting the settings dialog
  exposes, including the external-CLI-access toggle referenced by the CLI gate
  message in `src/hpc_gui/cli/main.py`.
- For each non-obvious behavioral claim, keep the wording traceable to a named
  source file; prefer describing observable UI behavior over internals.
- Internal wiki links use `[[Page-Name]]` and must target existing files.

## Forbidden

- Describing behavior not present in the named modules, inventing menu items,
  documenting site-specific cluster settings.
- Implying the application modifies remote HPC infrastructure.
- Any mention of `waves/`, `.agent-runs/`, DeepSeek, or internal AI
  orchestration tooling.
- Editing any file other than the ten listed pages.

## Acceptance

- Every keyboard shortcut and setting label matches `HELP_en.md` or `en.json`.
- No page documents a control that does not exist in the named modules.
- No corrupted branding token (`Lreate`, `LLI`, `conoig`, `JSnN`, `HPL`).
