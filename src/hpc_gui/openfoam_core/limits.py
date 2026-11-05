"""Finite static-scan budgets for OpenFOAM dictionaries (W65 LINT-COMPAT).

Single application-owned source for every byte/count/depth bound used by
the Linter and Case Studio engines. Production code must import limits
from here; tests use synthetic sources and never mutate this module.
"""

from __future__ import annotations

#: Strict UTF-8 byte budget for one in-memory lint input. Exact limit is
#: accepted; limit + 1 is rejected.
MAX_TEXT_BYTES = 5 * 1024 * 1024

#: Per-file budget for one case dictionary read from disk or SFTP.
MAX_DICTIONARY_BYTES = 1024 * 1024

#: Per-file budget for one constant/polyMesh boundary scan.
MAX_MESH_BOUNDARY_BYTES = 2 * 1024 * 1024

#: Total decoded-bytes budget for one local case scan.
MAX_CASE_BYTES = 8 * 1024 * 1024

#: Total file budget for one local case scan.
MAX_CASE_FILES = 256

#: Static include-graph depth budget (matches the engine analysis limit).
MAX_INCLUDE_DEPTH = 64

#: Remote (SFTP) per-file dictionary budget.
MAX_REMOTE_DICTIONARY_BYTES = 1024 * 1024

#: Remote total case budget.
MAX_REMOTE_CASE_BYTES = 8 * 1024 * 1024

#: Remote total file budget.
MAX_REMOTE_CASE_FILES = 256

#: Remote directory recursion depth budget.
MAX_REMOTE_CASE_DEPTH = 8

#: Remote directories never descended into during bounded scans.
REMOTE_CASE_SKIP_DIRS = frozenset({"postProcessing", "VTK", "processor0"})

#: Canonical documentation anchor recorded on every diagnostic.
SOURCE_DOCS = "https://doc.openfoam.com/2312/"
