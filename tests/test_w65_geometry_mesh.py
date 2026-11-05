'''Focused UNIT B regression tests for W65 geometry and mesh (W65).'''
from __future__ import annotations
import pytest
from hpc_gui.openfoam_v2312 import geometry, mesh
def _surface(**overrides):
    base = {'path': 'constant/triSurface/wing.stl', 'kind': 'stl', 'units': 'mm', 'size_bytes': 1024}
    base.update(overrides)
    return geometry.SurfaceImport(**base)
def _recipe(**overrides):
    base = {'name': 'wing', 'stages': ('import-surface', 'blockMesh', 'surfaceFeatureExtract', 'snappyHexMesh', 'checkMesh'), 'surfaces': ('wing.stl',)}
    base.update(overrides)
    return mesh.MeshRecipe(**base)
@pytest.mark.unit
def test_valid_surface_import_passes() -> None:
    assert geometry.validate_surface(_surface()) == ()
@pytest.mark.unit
def test_oversize_surface_is_rejected() -> None:
    errors = geometry.validate_surface(_surface(size_bytes=geometry.MAX_SURFACE_BYTES + 1))
    assert any('import cap' in error for error in errors)
@pytest.mark.unit
def test_symlink_needs_opt_in() -> None:
    assert any('symlink' in error for error in geometry.validate_surface(_surface(is_symlink=True)))
    assert geometry.validate_surface(_surface(is_symlink=True, allow_symlink=True)) == ()
@pytest.mark.unit
def test_step_needs_converter() -> None:
    assert any('converter' in error for error in geometry.validate_surface(_surface(kind='step', path='cad/wing.step')))
    assert geometry.validate_surface(_surface(kind='step', path='cad/wing.step', converter_available=True)) == ()
@pytest.mark.unit
def test_unknown_kind_and_unit_rejected() -> None:
    errors = geometry.validate_surface(_surface(kind='glb', units='parsec'))
    assert any('kind' in error for error in errors)
    assert any('unit' in error for error in errors)
@pytest.mark.unit
def test_path_escape_rejected() -> None:
    assert any('inside the case' in error for error in geometry.validate_surface(_surface(path='../evil.stl')))
    assert any('inside the case' in error for error in geometry.validate_surface(_surface(path='/abs/evil.stl')))
@pytest.mark.unit
def test_refuse_policy_blocks_existing_target() -> None:
    assert any('refuse' in error for error in geometry.validate_surface(_surface(target_exists=True)))
    assert geometry.validate_surface(_surface(target_exists=True, overwrite='rename')) == ()
@pytest.mark.unit
def test_unit_conversion() -> None:
    assert geometry.to_meters(1000.0, 'mm') == pytest.approx(1.0)
    assert geometry.to_meters(2.0, 'inch') == pytest.approx(0.0508)
    with pytest.raises(ValueError):
        geometry.to_meters(1.0, 'parsec')
@pytest.mark.unit
def test_surface_roundtrip() -> None:
    spec = _surface(is_symlink=True, allow_symlink=True)
    assert geometry.SurfaceImport.from_dict(spec.to_dict()) == spec
@pytest.mark.unit
def test_valid_mesh_recipe_passes() -> None:
    assert mesh.validate_recipe(_recipe(), known_surfaces=('wing.stl',)) == ()
@pytest.mark.unit
def test_solver_stage_rejected_from_mesh() -> None:
    errors = mesh.validate_recipe(_recipe(stages=('blockMesh', 'simpleFoam', 'checkMesh')), known_surfaces=('wing.stl',))
    assert any('non-mesh stage' in error for error in errors)
@pytest.mark.unit
def test_snappy_guards() -> None:
    assert any('surfaceFeatureExtract first' in error for error in mesh.validate_recipe(_recipe(stages=('blockMesh', 'snappyHexMesh', 'checkMesh')), known_surfaces=('wing.stl',)))
    assert any('at least one surface' in error for error in mesh.validate_recipe(_recipe(surfaces=())))
@pytest.mark.unit
def test_checkmesh_needs_producer_first() -> None:
    errors = mesh.validate_recipe(_recipe(stages=('checkMesh',)))
    assert any('producing stage first' in error for error in errors)
@pytest.mark.unit
def test_unknown_stage_and_surface_rejected() -> None:
    errors = mesh.validate_recipe(_recipe(stages=('blockMesh', 'teleportMesh'), surfaces=('ghost.stl',)), known_surfaces=('wing.stl',))
    assert any('unknown mesh stage' in error for error in errors)
    assert any('unknown surface reference' in error for error in errors)
@pytest.mark.unit
def test_recipe_roundtrip_and_malformed() -> None:
    recipe = _recipe()
    assert mesh.MeshRecipe.from_dict(recipe.to_dict()) == recipe
    with pytest.raises(ValueError):
        mesh.MeshRecipe.from_dict({'name': 'x', 'stages': 'blockMesh'})