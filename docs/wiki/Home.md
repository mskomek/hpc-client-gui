# HPC Client GUI Wiki

> Türkçe: [[Home-TR]]

HPC Client GUI is an independent, **client-side** desktop application for SSH,
Slurm, and optional X11 workflows on Slurm-based HPC clusters. It connects,
browses and transfers files, monitors scheduler jobs, and launches remote
graphical applications. It does **not** modify remote HPC infrastructure.

## How this wiki works

This wiki is **generated** from `docs/wiki/` in the
[main repository](https://github.com/mskomek/hpc-client-gui) and mirrored by
`scripts/sync_wiki.py`. Do not edit pages on github.com — those edits are
overwritten by the next sync. Open a pull request against `docs/wiki/` instead.

Product behavior is canonical in `src/hpc_gui/docs/` (`HELP_en.md`,
`CLI_GUIDE_en.md`, `ARCHITECTURE.md`, `CHANGELOG.md`) and in the repository
`README.md`. Pages here summarize and cross-link that content.

## Start here

- [[Quick Start|Quick-Start]] — install, connect, and submit a first job.
- [[Compatibility and Support Matrix|Compatibility-and-Support-Matrix]] — what
  is supported on which platform.
- [[Cluster Requirements|Cluster-Requirements]] — will it work on my
  cluster?
- [[FAQ|FAQ]] — short answers, grouped by symptom.

## Install

[[Windows|Installation-Windows]] · [[Linux|Installation-Linux]] · [[From source|Installation-From-Source]] · [[Upgrading and uninstalling|Upgrading-and-Uninstalling]]

## Use the application

[[Connecting and Profiles|Connecting-and-Profiles]] · [[Remote File Manager|Remote-File-Manager]] · [[File Transfers|File-Transfers]] · [[Slurm Jobs|Slurm-Jobs]] · [[Job Outputs|Job-Outputs]] · [[Script Editor|Script-Editor]] · [[Terminal and Remote Commands|Terminal-and-Remote-Commands]] · [[X11 Forwarding|X11-Forwarding]] · [[Plugins|Plugins]] · [[Settings Reference|Settings-Reference]] · [[Interface Language and i18n|Interface-Language-and-i18n]]

## Automate

[[CLI Guide|CLI-Guide]] · [[Scripting Examples|Scripting-Examples]]

## Operate and troubleshoot

[[Logs and Diagnostics|Logs-and-Diagnostics]] · [[Crash Reports and Send Logs|Crash-Reports-and-Send-Logs]] · [[Troubleshooting|Troubleshooting]] · [[Security Model|Security-Model]] · [[Data and Privacy|Data-and-Privacy]]

## Slurm

[[Slurm Help Library|Slurm-Help-Library]] · [[Job Script Templates|Job-Script-Templates]]

## Project

[[Architecture|Architecture]] · [[Building from Source|Building-from-Source]] · [[Release Process|Release-Process]] · [[Testing and CI|Testing-and-CI]] · [[Contributing|Contributing]] · [[Licensing and Commercial Use|Licensing-and-Commercial-Use]] · [[Support and Donations|Support-and-Donations]] · [[Release History|Release-History]] · [[Glossary|Glossary]]
