# Contributing

Thanks for considering a contribution. Issues and pull requests go through
[GitHub](https://github.com/mskomek/hpc-client-gui).

For anything with security impact, do **not** open a public issue — use
GitHub's Private Vulnerability Reporting, described in [SECURITY.md](SECURITY.md).

## Getting set up

```bash
python -m venv .venv
. .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-dev.txt
pre-commit install
pre-commit install --hook-type pre-push
python -m hpc_gui
```

Python 3.10+ is required. On Linux you also need the Qt platform libraries
PySide6 loads at startup (`libegl1` on Ubuntu/Debian).

## Push öncesi kontrol

`main` is protected: changes land only through pull requests from short-lived
feature branches, and every required status check must pass before merging
(this applies to maintainers too). Delete your feature branch — locally and on
the remote — right after merge. Keep each pull request limited to one outcome.

Run the same checks locally that CI will run:

```text
python scripts/ci.py quick       # commit öncesi hızlı kontrol
python scripts/ci.py pre-push    # push öncesi tüm yerel kontroller
```

`pre-commit install` hızlı kontrolü commit öncesinde, `pre-commit install
--hook-type pre-push` ise `pre-push` hedefini push öncesinde otomatik çalıştırır.
Hook kurulmamış olsa bile yukarıdaki komutlar aynı kontrolleri elle çalıştırır.
`--no-verify` hook’u atlar; bu korumayı bilinçli olarak devre dışı bırakır ve CI
kontrollerinin yine geçmesi gerekir.

Hedefler:

```text
python scripts/ci.py quick       # compile, i18n, smoke, Ruff
python scripts/ci.py full        # quick + GUI/coverage + docs + packaging
python scripts/ci.py gui         # offline GUI suite and coverage.xml
python scripts/ci.py lint        # Ruff
python scripts/ci.py docs        # branding, release surface, wiki
python scripts/ci.py packaging   # wheel packaging test
python scripts/ci.py pre-push    # geliştirici platformunda full
```

GUI testleri `QT_QPA_PLATFORM=offscreen` ve `HPC_GUI_DISABLE_WEBENGINE=1` ile
çalışır. Coverage raporları `coverage.json` ve `coverage.xml` olarak oluşur;
genel eşik `%65`tir ve modül eşikleri `scripts/check_module_coverage.py` içinde
tek yerde tanımlıdır. macOS mimari kontrolleri CI matrix’inde kalır; Windows’ta
macOS testi çalıştırılmaz ve bunun yerine CI matrix sonucu beklenir.

CI’daki GUI hatasını birebir yeniden üretmek için:

```bash
python scripts/ci.py gui
```

Çalıştırıcı başarısız hedefi ve komutu açıkça yazdırır; başarısız komutlar
başarılı sayılmaz.

## GitHub main koruması

Repository Settings → Rules → Rulesets altında `Protect main` adlı aktif
branch ruleset uygulanmalıdır:

- `main` branch hedefi ve pull request zorunluluğu
- required status checks: `Quality (Python 3.11)`,
  `Compatibility (Python 3.10)`, `Compatibility (Python 3.12)`, `macOS (arm64)`,
  `macOS (x86_64)`, `Windows`, `Plugin API contract`
- merge öncesi branch’in güncel olması ve conversation resolution
- force push ve branch deletion engeli
- doğrudan `main` push engeli
- administrator bypass yalnızca bilinçli ve kayıtlı acil durumlarda

Status check adları workflow job `name` değerleridir; bunlar değiştirilecekse
ruleset aynı değişiklikte güncellenmelidir.

The test suite is offline: fake file and Slurm layers stand in for the remote
side, and no test performs a real cluster operation. Keep it that way — a test
that needs a cluster cannot run in CI.

## Rules that come up in review

**Both languages, always.** Every user-visible string must exist in Turkish and
English. `scripts/check_i18n.py` fails on key drift, on hardcoded UI text, and
on references to translation keys that do not exist. An English-only string
fails CI.

**Keep the Qt layer thin.** If logic can be tested outside a widget, it belongs
in a service under `src/hpc_gui/services/`. This is what makes the offline
suite possible.

**Keep long work off the interface thread.** Session, transfer, and process
work must not block the window.

**Quote and mock external commands.** Never assemble remote command lines from
free-form strings, and never invent cluster settings.

**Confirm destructive operations.** Anything that destroys data or changes
cluster state requires explicit confirmation — `--yes` on the command line, a
dialog in the interface.

See the [Architecture](https://github.com/mskomek/hpc-client-gui/wiki/Architecture)
wiki page for the layer split and the reasoning behind these rules.

## Documentation changes

Product documentation is canonical in `src/hpc_gui/docs/` and `README.md`.

The [wiki](https://github.com/mskomek/hpc-client-gui/wiki) is **generated** from
`docs/wiki/` in this repository and reviewed like code. Do not edit pages on
github.com — the next sync overwrites them. `scripts/check_wiki.py` enforces
link resolution, English/Turkish page parity, heading parity, sidebar
completeness, and forbidden terms.

## Licensing

From v1.2.0 the project is licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE). Contributions are made under
that license: available for noncommercial use under those terms, while
commercial use continues to require a separate license from the copyright
holder (see [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md)).

If you are contributing on behalf of an employer, confirm this is acceptable to
them before opening a pull request.
