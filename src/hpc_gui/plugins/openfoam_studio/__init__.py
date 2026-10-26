"""Case Studio plugin identity (W65 HOST-002). Version 0.3.0-w65r17-auditfix1."""

from __future__ import annotations

from .boundary import FIELD_DIMS, allowed_bc
from .physics import required_fields_for

PLUGIN_ID = "openfoam-case-studio"
PLUGIN_VERSION = "0.3.0-w65r17-auditfix1"
PLUGIN_BASE = "0.2.1"
OPENFOAM_EDITION = "OpenFOAM.com / ESI (OpenCFD)"
OPENFOAM_RELEASE = "v2312"
REQUIRES_APP = ">=1.5.9"
SCHEMA_VERSION = "w65r1"

__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "PLUGIN_BASE", "OPENFOAM_EDITION", "OPENFOAM_RELEASE", "REQUIRES_APP", "SCHEMA_VERSION", "FIELD_DIMS", "allowed_bc", "required_fields_for"]
