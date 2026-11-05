'''Surface geometry import descriptors (W65 UNIT B, HPC-W65-GEOM-004).

Pure-data import safety gate for preexisting CAD and surface files. The
validators perform no filesystem access and mutate no case: callers supply
file metadata and receive deterministic error strings. Anything unverified
stays rejected, and STEP or IGES files stay converter-gated.
'''
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
KIND_STL = 'stl'
KIND_OBJ = 'obj'
KIND_VTK = 'vtk'
KIND_TRISURFACE = 'triSurface'
KIND_STEP = 'step'
KIND_IGES = 'iges'
SURFACE_KINDS = (KIND_STL, KIND_OBJ, KIND_VTK, KIND_TRISURFACE, KIND_STEP, KIND_IGES)
CAD_KINDS = frozenset({KIND_STEP, KIND_IGES})
UNIT_MM = 'mm'
UNIT_CM = 'cm'
UNIT_M = 'm'
UNIT_INCH = 'inch'
LENGTH_UNITS = (UNIT_MM, UNIT_CM, UNIT_M, UNIT_INCH)
UNIT_TO_METERS = {UNIT_MM: 0.001, UNIT_CM: 0.01, UNIT_M: 1.0, UNIT_INCH: 0.0254}
POLICY_REFUSE = 'refuse'
POLICY_RENAME = 'rename'
OVERWRITE_POLICIES = (POLICY_REFUSE, POLICY_RENAME)
MAX_SURFACE_BYTES = 524288000
@dataclass(frozen=True)
class SurfaceImport:
    '''One surface import request with its safety policy.'''
    path: str
    kind: str
    units: str
    size_bytes: int
    is_symlink: bool = False
    allow_symlink: bool = False
    target_exists: bool = False
    overwrite: str = POLICY_REFUSE
    converter_available: bool = False
    def to_dict(self) -> dict[str, Any]:
        '''Return a JSON-serializable view of this request.'''
        return {'path': self.path, 'kind': self.kind, 'units': self.units, 'size_bytes': self.size_bytes, 'is_symlink': self.is_symlink, 'allow_symlink': self.allow_symlink, 'target_exists': self.target_exists, 'overwrite': self.overwrite, 'converter_available': self.converter_available}
    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> 'SurfaceImport':
        '''Rebuild a request without touching the filesystem.'''
        return SurfaceImport(path=str(raw['path']), kind=str(raw['kind']), units=str(raw['units']), size_bytes=int(raw['size_bytes']), is_symlink=bool(raw.get('is_symlink', False)), allow_symlink=bool(raw.get('allow_symlink', False)), target_exists=bool(raw.get('target_exists', False)), overwrite=str(raw.get('overwrite', POLICY_REFUSE)), converter_available=bool(raw.get('converter_available', False)))
def validate_surface(spec: SurfaceImport) -> tuple[str, ...]:
    '''Return deterministic error strings; empty means importable.'''
    errors: list[str] = []
    if not spec.path.strip():
        errors.append('empty surface path')
    else:
        flat = spec.path.replace(chr(92), '/')
        if flat.startswith('/') or '..' in flat.split('/'):
            errors.append('surface path must stay inside the case: ' + spec.path)
    if spec.kind not in SURFACE_KINDS:
        errors.append('unknown surface kind: ' + spec.kind)
    if spec.units not in LENGTH_UNITS:
        errors.append('unknown length unit: ' + spec.units)
    if spec.size_bytes < 0:
        errors.append('negative surface size')
    elif spec.size_bytes > MAX_SURFACE_BYTES:
        errors.append('surface exceeds 500 MiB import cap')
    if spec.is_symlink and not spec.allow_symlink:
        errors.append('symlink surface requires explicit opt-in')
    if spec.kind in CAD_KINDS and not spec.converter_available:
        errors.append('STEP/IGES conversion needs an installed converter')
    if spec.overwrite not in OVERWRITE_POLICIES:
        errors.append('unknown overwrite policy: ' + spec.overwrite)
    elif spec.target_exists and spec.overwrite == POLICY_REFUSE:
        errors.append('target exists and overwrite policy is refuse')
    return tuple(errors)
def to_meters(value: float, units: str) -> float:
    '''Convert a length to meters; rejects unknown units.'''
    if units not in UNIT_TO_METERS:
        raise ValueError('unknown length unit: ' + units)
    return value * UNIT_TO_METERS[units]
def list_kinds() -> tuple[str, ...]:
    '''Return the supported surface kinds in stable order.'''
    return SURFACE_KINDS