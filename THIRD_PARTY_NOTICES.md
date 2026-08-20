# Third-Party Notices

HPC Client GUI itself is licensed under the PolyForm Noncommercial License
1.0.0. Commercial use remains governed by the separate `COMMERCIAL_LICENSE.md`.
This application also bundles third-party runtime dependencies, each of which
remains distributed under its own license. No third-party component is
relicensed under the HPC Client GUI license.

## Bundled runtime dependencies

| Component | License | Notes |
| --- | --- | --- |
| PySide6 | LGPLv3 terms used by this project | Qt for Python bindings |
| shiboken6 | LGPLv3 terms used by this project | CPython bindings generator for Qt (runtime support for PySide6) |
| Qt libraries | Applicable Qt LGPL terms | Qt libraries distributed through PySide6 |
| xterm.js / @xterm/addon-fit | MIT | Vendored embedded-terminal assets; license and provenance are in `src/hpc_gui/assets/terminal/NOTICE.md` |
| paramiko | LGPL-2.1+ | SSHv2 protocol implementation |
| cryptography | Apache-2.0 / BSD | Cryptographic primitives used by paramiko |

`cryptography`'s license texts (Apache-2.0, with additional terms under the
BSD 3-Clause License) ship inside the packaged application's `_internal`
directory as part of its wheel distribution metadata.

PySide6 and shiboken6 (dual-licensed LGPLv3/GPLv3/commercial; this
application uses the LGPLv3 terms) and paramiko (LGPL-2.1+) don't ship their
full license text in their PyPI wheel metadata, so the canonical texts are
bundled directly in `third_party_licenses/`:

- `third_party_licenses/LGPL-3.0.txt` — GNU Lesser General Public License
  v3.0, covering PySide6 and shiboken6 (unmodified, obtained from
  https://www.gnu.org/licenses/lgpl-3.0.txt).
- `third_party_licenses/paramiko-LGPL-2.1.txt` — GNU Lesser General Public
  License v2.1, covering paramiko (unmodified, taken from paramiko's own
  wheel distribution).
- `src/hpc_gui/assets/terminal/NOTICE.md` — bundled xterm.js and addon-fit
  provenance plus the complete MIT license text. This file ships with the
  terminal assets in Windows and Linux packages.

LGPL-covered components may be replaced or modified under the rights granted
by the LGPL. The exact dependency and Qt runtime versions shipped in each
binary release are recorded in the generated `THIRD_PARTY_VERSIONS.txt`
manifest, and the machine-readable dependency inventory is in
`SBOM.cdx.json`. Corresponding-source information for Qt and PySide6
components is described in `QT_LGPL_SOURCE_OFFER.md`.

## License texts

The `LICENSE`, `COMMERCIAL_LICENSE.md`, this notices file,
`QT_LGPL_SOURCE_OFFER.md`, `THIRD_PARTY_VERSIONS.txt`, and
`SBOM.cdx.json`, and
`third_party_licenses/` all ship alongside the packaged application. If you
receive a copy of this software without them, obtain the missing notices from
the corresponding source or release materials before redistributing it.
