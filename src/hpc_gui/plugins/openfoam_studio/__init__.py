"""Case Studio plugin identity with versioned OpenFOAM.com release profiles."""

from __future__ import annotations

from .boundary import FIELD_DIMS, allowed_bc
from .physics import required_fields_for
from hpc_gui.openfoam_core.release_support import supported_releases

PLUGIN_ID = "openfoam-case-studio"
PLUGIN_VERSION = "0.3.1-w65r19.20261027.3"
PLUGIN_BASE = "0.2.1"
OPENFOAM_EDITION = "OpenFOAM.com / ESI (OpenCFD)"
OPENFOAM_RELEASE = "v2312"
OPENFOAM_RELEASES = supported_releases()
REQUIRES_APP = ">=1.5.9"
SCHEMA_VERSION = "w65r1"

__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "PLUGIN_BASE", "OPENFOAM_EDITION", "OPENFOAM_RELEASE", "OPENFOAM_RELEASES", "REQUIRES_APP", "SCHEMA_VERSION", "FIELD_DIMS", "allowed_bc", "required_fields_for"]
