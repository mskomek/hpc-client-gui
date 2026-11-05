'''Mesh recipe descriptors (W65 UNIT B, HPC-W65-MESH-005).

Ordered mesh stage lists with deterministic ordering guards. Recipes
describe work; they never execute solvers, touch the filesystem, or claim
live runs. Non-mesh stages are rejected inside mesh scope so a solver can
never run before the mesh exists.
'''
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
STAGE_IMPORT_SURFACE = 'import-surface'
STAGE_BLOCKMESH = 'blockMesh'
STAGE_FEATURE_EXTRACT = 'surfaceFeatureExtract'
STAGE_SNAPPY = 'snappyHexMesh'
STAGE_CHECKMESH = 'checkMesh'
STAGE_IMPORT_POLYMESH = 'import-polyMesh'
STAGE_SPLIT_REGIONS = 'splitMeshRegions'
MESH_STAGES = (STAGE_IMPORT_SURFACE, STAGE_BLOCKMESH, STAGE_FEATURE_EXTRACT, STAGE_SNAPPY, STAGE_CHECKMESH, STAGE_IMPORT_POLYMESH, STAGE_SPLIT_REGIONS)
MESH_PRODUCERS = frozenset({STAGE_BLOCKMESH, STAGE_SNAPPY, STAGE_IMPORT_POLYMESH, STAGE_SPLIT_REGIONS})
NON_MESH_STAGES = frozenset({'simpleFoam', 'icoFoam', 'chtMultiRegionSimpleFoam', 'pimpleFoam', 'pisoFoam', 'postProcess'})
@dataclass(frozen=True)
class MeshRecipe:
    '''One ordered mesh recipe with its surface references.'''
    name: str
    stages: tuple[str, ...]
    surfaces: tuple[str, ...] = ()
    def to_dict(self) -> dict[str, Any]:
        '''Return a JSON-serializable view of this recipe.'''
        return {'name': self.name, 'stages': list(self.stages), 'surfaces': list(self.surfaces)}
    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> 'MeshRecipe':
        '''Rebuild a recipe, rejecting malformed stage lists.'''
        stages = raw['stages']
        if not isinstance(stages, Sequence) or isinstance(stages, (str, bytes)):
            raise ValueError('mesh stages must be a list of names')
        surfaces = raw.get('surfaces', [])
        if not isinstance(surfaces, Sequence) or isinstance(surfaces, (str, bytes)):
            raise ValueError('mesh surfaces must be a list of names')
        return MeshRecipe(name=str(raw['name']), stages=tuple(str(stage) for stage in stages), surfaces=tuple(str(surface) for surface in surfaces))
def validate_recipe(recipe: MeshRecipe, known_surfaces: tuple[str, ...] = ()) -> tuple[str, ...]:
    '''Return deterministic error strings; empty means meshable.'''
    errors: list[str] = []
    if not recipe.name.strip():
        errors.append('empty mesh recipe name')
    if not recipe.stages:
        errors.append('mesh recipe has no stages')
    for stage in recipe.stages:
        if stage in NON_MESH_STAGES:
            errors.append('non-mesh stage must not appear in a mesh recipe: ' + stage)
        elif stage not in MESH_STAGES:
            errors.append('unknown mesh stage: ' + stage)
    order = [stage for stage in recipe.stages if stage in MESH_STAGES]
    if STAGE_SNAPPY in order:
        if STAGE_FEATURE_EXTRACT not in order[:order.index(STAGE_SNAPPY)]:
            errors.append('snappyHexMesh requires surfaceFeatureExtract first')
        if not recipe.surfaces:
            errors.append('snappyHexMesh requires at least one surface')
    if STAGE_FEATURE_EXTRACT in order and not recipe.surfaces:
        errors.append('surfaceFeatureExtract requires at least one surface')
    if STAGE_CHECKMESH in order:
        first_check = order.index(STAGE_CHECKMESH)
        if not (set(order[:first_check]) & MESH_PRODUCERS):
            errors.append('checkMesh requires a mesh producing stage first')
    for surface in recipe.surfaces:
        if surface not in known_surfaces:
            errors.append('unknown surface reference: ' + surface)
    return tuple(errors)