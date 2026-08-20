# Interface Language and i18n

> Türkçe: [[Interface-Language-and-i18n-TR]]

The application ships in **Turkish** and **English**. Both are complete: every
user-visible string exists in both, and CI fails if that stops being true.

## Choosing a language

Pick the language in the application; the choice takes effect immediately —
open windows re-translate rather than requiring a restart.

Your choice is stored in `~/.truba_slurm_gui/language.json` and reused on the
next start. On first run, when nothing is stored yet, the application follows
your operating system's locale: a Turkish locale gives Turkish, anything else
gives English.

If the language file cannot be written, the application keeps running in the
selected language for this session rather than failing — the choice simply is
not remembered.

## Where the strings live

Translations are JSON catalogs at `src/hpc_gui/i18n/tr.json` and
`src/hpc_gui/i18n/en.json`, keyed by dotted names (`settings.dialog_title`,
`transfer.conflict_overwrite`). Code looks up keys rather than embedding text,
which is what makes switching languages at runtime possible.

## What is not translated

Commands, flags, file paths, exit codes, and identifiers stay as they are in
both languages — `sbatch` is `sbatch` everywhere. Output that comes from the
cluster (Slurm messages, shell output, remote errors) arrives in whatever
language the cluster produces and is shown unchanged.

That includes the command-line interface: its help text, option names, and
error messages are English, and its exit codes are the contract automation
should rely on. See [[CLI Guide|CLI-Guide]].

## For contributors

Turkish and English resources are updated **together**. `scripts/check_i18n.py`
is a blocking CI gate and fails on:

- a key present in one catalog but missing from the other,
- hardcoded user-visible text in the interface code instead of a catalog key,
- a reference to a translation key that does not exist in both catalogs.

Adding an English-only string will fail CI. See [[Contributing|Contributing]]
and [[Testing and CI|Testing-and-CI]].

The same rule applies to this wiki: every English page has a Turkish
counterpart, enforced by `scripts/check_wiki.py`.

## Additional languages

Only Turkish and English are supported today. Adding another language means a
new catalog with full key coverage plus a translated wiki mirror — a
substantial contribution rather than a configuration change.

## See also

[[Settings Reference|Settings-Reference]] · [[Contributing|Contributing]] · [[Glossary|Glossary]]
