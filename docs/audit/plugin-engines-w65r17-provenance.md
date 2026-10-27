# Plugin engine source provenance (W65 R17 slice)

The canonical, separately auditable engine sources under
`src/hpc_gui/plugin_engines/openfoam_lint/` and
`src/hpc_gui/plugin_engines/openfoam_studio/` were copied byte-for-byte
from the read-only Drive candidate packages:

- `D:\MyDrive\Projeler\OpenFOAM-Plugins\openfoam-linter\0.2.0-w65r17-auditfix1\engine\openfoam_lint\*.py`
- `D:\MyDrive\Projeler\OpenFOAM-Plugins\openfoam-case-studio\0.3.0-w65r17-auditfix1\engine\openfoam_studio\*.py`

Only the plugin-specific `openfoam_lint/*.py` and `openfoam_studio/*.py`
files were copied. The candidates' `engine/hpc_gui/` duplicates were NOT
copied: their canonical host-owned sources already live in tracked
`src/hpc_gui/openfoam_core`, `src/hpc_gui/plugins/openfoam_lint`, and
`src/hpc_gui/plugins/openfoam_studio`, which the engine packages import.

The old Drive packages (ZIPs, extracted trees, manifests, checksums) and
the main-checkout files outside this slice were left unchanged. These
packages were newly committed as source in this slice; they were not
previously source-committed.

Follow-up fixes in this slice (stricter `lint_text` contract, shared
read bounds, symlink rejection, strict UTF-8 decoding) apply to the
newly tracked Linter engine API (`plugin_engines/openfoam_lint/api.py`
and its `__init__.py` exports) only.

The R17 follow-up also reports ordinary selected files that are not
supported OpenFOAM dictionaries as `OF-CASE-007`. `OF-CASE-004` remains
reserved for include targets that the static include resolver cannot
parse; this keeps the rule catalog and emitted diagnostic semantics aligned.

Not claimed: creating the Case Studio source package does NOT fix Case
Studio active dispatch. Studio stays declarative-only and fail-closed for
execution; it has no safe host loader/dispatch path in this tree.

Release pins: this slice adds no API3 production pins. The old
`auditfix1` candidate trees stay API 2. Application-owned release pins
(if any) are published separately by release engineering, never derived
from package-provided hashes; tests inject synthetic pins only.
