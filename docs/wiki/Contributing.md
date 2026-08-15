# Contributing

> Türkçe: [[Contributing-TR]]

Issues and pull requests go through
[GitHub](https://github.com/mskomek/hpc-client-gui). For anything with security
impact, use the private reporting channel instead of a public issue — see
[[Security Model|Security-Model]].

## Before you start

- Read [[Architecture|Architecture]]. Most review feedback is about code
  landing in the wrong layer.
- Run the offline suite and the helper checks locally — see
  [[Testing and CI|Testing-and-CI]]. Every CI job is blocking.

## Rules that come up in review

**Both languages, always.** Any user-visible string must exist in Turkish and
English. `scripts/check_i18n.py` fails on key drift, on hardcoded UI text, and
on references to translation keys that do not exist. Adding an English-only
string will fail CI.

**Keep the Qt layer thin.** If logic can be tested outside a widget, it belongs
in a service. This is what makes the offline suite possible.

**Keep long work off the interface thread.** Session, transfer, and process
work must not block the window.

**Quote and mock external commands.** Never assemble remote command lines from
free-form strings, and never invent cluster settings — tests must not depend on
a real cluster.

**Confirm destructive operations.** Anything that destroys data or changes
cluster state requires explicit confirmation (`--yes` on the command line, a
dialog in the interface).

## Documentation changes

Product documentation is canonical in `src/hpc_gui/docs/` and `README.md`. This
wiki is generated from `docs/wiki/` in the repository and is reviewed like
code — do not edit pages on github.com, because the next sync overwrites them.
`scripts/check_wiki.py` enforces link resolution, English/Turkish page parity,
heading parity, sidebar completeness, and forbidden terms.

## Licensing implication

The project is licensed under the **PolyForm Noncommercial License 1.0.0** from
v1.2.0 onward. Contributions are made under that license, so they are available
for noncommercial use under those terms while commercial use continues to
require a separate license from the copyright holder. If you are contributing
on behalf of an employer, confirm this is acceptable to them first. See
[[Licensing and Commercial Use|Licensing-and-Commercial-Use]].

## See also

[[Testing and CI|Testing-and-CI]] ·
[[Building from Source|Building-from-Source]] ·
[[Support and Donations|Support-and-Donations]]
