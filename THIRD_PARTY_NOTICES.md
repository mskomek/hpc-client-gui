# Third-Party Notices

HPC Client GUI is licensed under the PolyForm Noncommercial License 1.0.0.
This application also bundles third-party runtime dependencies, each of which
is distributed under its own license.

## Bundled runtime dependencies

| Component | License | Notes |
| --- | --- | --- |
| PySide6 | LGPLv3 terms used by this project | Qt for Python bindings |
| shiboken6 | LGPLv3 terms used by this project | CPython bindings generator for Qt (runtime support for PySide6) |
| Qt libraries | Applicable Qt LGPL terms | Qt libraries distributed through PySide6 |
| xterm.js / @xterm/addon-fit | MIT | Vendored local terminal frontend assets; see `third_party_licenses/xterm-MIT.txt` |
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

## License texts

The `LICENSE`, `COMMERCIAL_LICENSE.md`, this notices file, and
`third_party_licenses/` all ship alongside the packaged application. If you
receive a copy of this software without them, you may obtain them from the
project's source repository.
