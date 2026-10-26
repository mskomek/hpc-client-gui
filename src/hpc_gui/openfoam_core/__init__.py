"""OpenFOAM dictionary core facade (W65 BASE-001).

Pure-Python, dependency-free reader for OpenFOAM.com v2312 dictionaries.
Never executes ``#codeStream``/``#calc``/shell templates; they are carried
as opaque raw spans. Both Case Studio and Linter import only this facade.
"""

from __future__ import annotations

from hpc_gui.openfoam_core.boundary import FIELD_DIMS, allowed_bc
from hpc_gui.openfoam_core.case_scan import classify_case_path, scan_case
from hpc_gui.openfoam_core.lexer import lex, LexToken
from hpc_gui.openfoam_core.parser import ParsedDictionary, parse_text
from hpc_gui.openfoam_core.physics import required_fields_for
from hpc_gui.openfoam_core.safe_patch import byte_identity_ok, sha256_bytes, single_token_patch

__all__ = [
    "LexToken",
    "ParsedDictionary",
    "FIELD_DIMS",
    "allowed_bc",
    "byte_identity_ok",
    "case_scan",
    "classify_case_path",
    "lex",
    "parse_text",
    "required_fields_for",
    "scan_case",
    "sha256_bytes",
    "single_token_patch",
]
