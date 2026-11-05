"""OpenFOAM dictionary core facade (W65 LINT-COMPAT).

Pure-Python, dependency-free reader for OpenFOAM.com v2312 dictionaries.
Never executes ``#codeStream``/``#calc``/shell templates; they are carried
as opaque tokens. Both Case Studio and Linter import only this facade.

Legacy ``parse_text`` keeps its historical dict-shaped contract for
API1/API2 clients; new engines use ``parse_dictionary`` and friends.
"""

from __future__ import annotations

from hpc_gui.openfoam_core.boundary import FIELD_DIMS, allowed_bc
from hpc_gui.openfoam_core.case_scan import classify_case_path, scan_case
from hpc_gui.openfoam_core.decoded import DecodedSource, preferred_newline
from hpc_gui.openfoam_core.document import (
    Diagnostic,
    Entry,
    ParsedDictionary,
    Token,
    parse_dictionary,
)
from hpc_gui.openfoam_core.files import (
    DiscoveredFile,
    FilePayload,
    discover_case_files,
    discover_mesh_boundaries,
    read_dictionary_file,
    scan_remote_dictionaries,
    scan_remote_mesh_boundaries,
)
from hpc_gui.openfoam_core.lexer import LexToken, lex
from hpc_gui.openfoam_core.limits import (
    MAX_CASE_BYTES,
    MAX_CASE_FILES,
    MAX_DICTIONARY_BYTES,
    MAX_INCLUDE_DEPTH,
    MAX_MESH_BOUNDARY_BYTES,
    MAX_REMOTE_CASE_BYTES,
    MAX_REMOTE_CASE_DEPTH,
    MAX_REMOTE_CASE_FILES,
    MAX_REMOTE_DICTIONARY_BYTES,
    MAX_TEXT_BYTES,
    REMOTE_CASE_SKIP_DIRS,
    SOURCE_DOCS,
)
from hpc_gui.openfoam_core.parser import ParseIssue, parse_text
from hpc_gui.openfoam_core.paths import (
    is_dictionary_name,
    is_mesh_boundary_path,
    safe_relative_path,
)
from hpc_gui.openfoam_core.physics import required_fields_for
from hpc_gui.openfoam_core.regions import (
    RegionGroup,
    RegionProperties,
    parse_mesh_boundary_names,
    parse_region_properties,
)
from hpc_gui.openfoam_core.safe_patch import byte_identity_ok, sha256_bytes, single_token_patch

__all__ = [
    "DecodedSource",
    "Diagnostic",
    "DiscoveredFile",
    "Entry",
    "FIELD_DIMS",
    "FilePayload",
    "LexToken",
    "MAX_CASE_BYTES",
    "MAX_CASE_FILES",
    "MAX_DICTIONARY_BYTES",
    "MAX_INCLUDE_DEPTH",
    "MAX_MESH_BOUNDARY_BYTES",
    "MAX_REMOTE_CASE_BYTES",
    "MAX_REMOTE_CASE_DEPTH",
    "MAX_REMOTE_CASE_FILES",
    "MAX_REMOTE_DICTIONARY_BYTES",
    "MAX_TEXT_BYTES",
    "ParseIssue",
    "ParsedDictionary",
    "REMOTE_CASE_SKIP_DIRS",
    "RegionGroup",
    "RegionProperties",
    "SOURCE_DOCS",
    "Token",
    "allowed_bc",
    "byte_identity_ok",
    "classify_case_path",
    "discover_case_files",
    "discover_mesh_boundaries",
    "is_dictionary_name",
    "is_mesh_boundary_path",
    "lex",
    "parse_dictionary",
    "parse_mesh_boundary_names",
    "parse_region_properties",
    "parse_text",
    "preferred_newline",
    "read_dictionary_file",
    "required_fields_for",
    "safe_relative_path",
    "scan_case",
    "scan_remote_dictionaries",
    "scan_remote_mesh_boundaries",
    "sha256_bytes",
    "single_token_patch",
]
