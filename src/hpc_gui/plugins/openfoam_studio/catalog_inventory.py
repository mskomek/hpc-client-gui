"""Source-pinned v2312 command inventory (W65 CAT-003, G03).

Honest machine-readable registry: every entry carries proof level,
availability, and an exact v2312 source-tree path. The legacy 0.2.1
eight-command catalog and all 20 typed schemas are preserved verbatim
in meaning; entries without a typed schema stay RAW-ADVANCED/UNSUPPORTED
with an exact reason. No CLI options are inferred, no action is
promoted to ACTIVE-TYPED, and no site binary is claimed: the archive
below was read read-only (tar listing + Make/files EXE targets) and
was never extracted into the repository; no GPL code is copied.

Provenance: OpenFOAM-v2312.tgz (69027976 bytes,
sha256 f113183a4d027c93939212af8967053c5f8fe76fb62e5848cb11bbcf8e829552)
tagged source OpenFOAM-v2312; method: EXE targets in */Make/files
under applications/solvers|utilities plus modules/*/applications/*.
Denominator: 122 solver EXEs + 175 utility EXEs + 8 non-EXE configs
(7 function-object configs + sample) = 305. Site/runtime discovery stays
"""

from __future__ import annotations

ARCHIVE_NAME = "OpenFOAM-v2312.tgz"
ARCHIVE_SHA256 = "f113183a4d027c93939212af8967053c5f8fe76fb62e5848cb11bbcf8e829552"
ARCHIVE_BYTES = 69027976
SOURCE_TAG = "OpenFOAM-v2312"
SOURCE_MANIFEST = "references/openfoam-source/v2312/source-index/OPENFOAM_v2312_SOURCE_MANIFEST.json"
SOLVER_EXE_COUNT = 122
UTILITY_EXE_COUNT = 175
FUNCTION_OBJECT_CONFIG_COUNT = 7
NON_EXE_CONFIG_COUNT = 8  # 7 function-object configs + sample (no standalone binary)

LEGACY_8 = (
    "blockMesh", "checkMesh", "decomposePar", "splitMeshRegions",
    "icoFoam", "chtMultiRegionSimpleFoam", "reconstructPar", "postProcess",
)

# (name, category, subcategory, kind, proof, availability, solver_family,
#  source_path relative to the OpenFOAM-v2312 tree root, explicit reason or "")
_CURATED: tuple = (
    ('blockMesh', 'mesh', 'structured', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/mesh/generation/blockMesh', ''),
    ('checkMesh', 'mesh', 'quality', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/mesh/manipulation/checkMesh', ''),
    ('surfaceFeatureExtract', 'geometry', 'feature', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/surface/surfaceFeatureExtract', ''),
    ('snappyHexMesh', 'mesh', 'surface-driven', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/mesh/generation/snappyHexMesh', ''),
    ('decomposePar', 'parallel', 'decompose', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/parallelProcessing/decomposePar', ''),
    ('reconstructPar', 'parallel', 'reconstruct', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/parallelProcessing/reconstructPar', ''),
    ('splitMeshRegions', 'mesh', 'regions', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/mesh/manipulation/splitMeshRegions', ''),
    ('createPatch', 'mesh', 'patches', 'utility', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'applications/utilities/mesh/manipulation/createPatch', ''),
    ('topoSet', 'mesh', 'zones', 'utility', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'applications/utilities/mesh/manipulation/topoSet', ''),
    ('setFields', 'init', 'fields', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/preProcessing/setFields', ''),
    ('mergeMeshes', 'mesh', 'combine', 'utility', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'applications/utilities/mesh/manipulation/mergeMeshes', ''),
    ('gmshToFoam', 'mesh', 'import', 'converter', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'applications/utilities/mesh/conversion/gmshToFoam', ''),
    ('fluentMeshToFoam', 'mesh', 'import', 'converter', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'applications/utilities/mesh/conversion/fluentMeshToFoam', ''),
    ('foamToVTK', 'post', 'export', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/postProcessing/dataConversion/foamToVTK', ''),
    ('postProcess', 'post', 'function-objects', 'utility', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'applications/utilities/postProcessing/postProcess', ''),
    ('sample', 'post', 'sampling', 'function-object-config', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'etc/caseDicts/postProcessing/graphs/sampleDict.cfg', 'no standalone v2312 binary; sampling runs via postProcess -func sampleDict (template + src/sampling)'),
    ('icoFoam', 'solver', 'incompressible-laminar', 'solver', 'V2312-SOURCE', 'ACTIVE-TYPED', 'laminar', 'applications/solvers/incompressible/icoFoam', ''),
    ('simpleFoam', 'solver', 'incompressible-rans', 'solver', 'V2312-SOURCE', 'ACTIVE-TYPED', 'rans-steady', 'applications/solvers/incompressible/simpleFoam', ''),
    ('pimpleFoam', 'solver', 'incompressible-transient', 'solver', 'V2312-SOURCE', 'ACTIVE-TYPED', 'transient', 'applications/solvers/incompressible/pimpleFoam', ''),
    ('pisoFoam', 'solver', 'incompressible-transient', 'solver', 'V2312-SOURCE', 'RAW-ADVANCED', 'transient', 'applications/solvers/incompressible/pisoFoam', ''),
    ('chtMultiRegionSimpleFoam', 'solver', 'cht', 'solver', 'V2312-SOURCE', 'ACTIVE-TYPED', 'cht', 'applications/solvers/heatTransfer/chtMultiRegionFoam/chtMultiRegionSimpleFoam', ''),
    ('chtMultiRegionFoam', 'solver', 'cht', 'solver', 'V2312-SOURCE', 'RAW-ADVANCED', 'cht', 'applications/solvers/heatTransfer/chtMultiRegionFoam', ''),
    ('buoyantSimpleFoam', 'solver', 'compressible-buoyant', 'solver', 'V2312-SOURCE', 'RAW-ADVANCED', 'buoyant', 'applications/solvers/heatTransfer/buoyantSimpleFoam', ''),
    ('rhoSimpleFoam', 'solver', 'compressible', 'solver', 'V2312-SOURCE', 'RAW-ADVANCED', 'compressible', 'applications/solvers/compressible/rhoSimpleFoam', ''),
    ('rhoPimpleFoam', 'solver', 'compressible', 'solver', 'V2312-SOURCE', 'RAW-ADVANCED', 'compressible', 'applications/solvers/compressible/rhoPimpleFoam', ''),
    ('interFoam', 'solver', 'multiphase', 'solver', 'OFFICIAL-DOC', 'RAW-ADVANCED', 'multiphase', 'applications/solvers/multiphase/interFoam', ''),
    ('reactingFoam', 'solver', 'reacting', 'solver', 'OFFICIAL-DOC', 'UNSUPPORTED', 'reacting', 'applications/solvers/combustion/reactingFoam', 'reacting/combustion family has no typed schema; unsupported until typed model exists'),
    ('potentialFoam', 'solver', 'potential', 'solver', 'V2312-SOURCE', 'RAW-ADVANCED', 'potential', 'applications/solvers/basic/potentialFoam', ''),
    ('yPlus', 'post', 'metrics', 'function-object', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'src/functionObjects/field/yPlus', ''),
    ('wallShearStress', 'post', 'metrics', 'function-object', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'src/functionObjects/field/wallShearStress', ''),
    ('forces', 'post', 'loads', 'function-object', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'src/functionObjects/forces', ''),
    ('forceCoeffs', 'post', 'loads', 'function-object', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'src/functionObjects/forces/forceCoeffs', ''),
    ('fieldAverage', 'post', 'averaging', 'function-object', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'src/functionObjects/field/fieldAverage', ''),
    ('probes', 'post', 'sampling', 'function-object', 'V2312-SOURCE', 'ACTIVE-TYPED', '', 'src/sampling/probes', ''),
    ('patchAverage', 'post', 'sampling', 'function-object', 'V2312-SOURCE', 'RAW-ADVANCED', '', 'etc/caseDicts/postProcessing/surfaceFieldValue/patchAverage', ''),
)

# Source-derived solvers: (binary name, source dir relative to tree root).
# Family/subcategory are derived deterministically from the path; every
# entry is RAW-ADVANCED (no typed schema) with V2312-SOURCE proof.
_SOURCE_SOLVERS: tuple = (
    ('DPMDyMFoam', 'applications/solvers/lagrangian/DPMFoam/DPMDyMFoam'),
    ('DPMFoam', 'applications/solvers/lagrangian/DPMFoam'),
    ('MPPICDyMFoam', 'applications/solvers/lagrangian/DPMFoam/DPMDyMFoam/MPPICDyMFoam'),
    ('MPPICFoam', 'applications/solvers/lagrangian/DPMFoam/MPPICFoam'),
    ('MPPICInterFoam', 'applications/solvers/multiphase/MPPICInterFoam'),
    ('PDRFoam', 'applications/solvers/combustion/PDRFoam'),
    ('SRFPimpleFoam', 'applications/solvers/incompressible/pimpleFoam/SRFPimpleFoam'),
    ('SRFSimpleFoam', 'applications/solvers/incompressible/simpleFoam/SRFSimpleFoam'),
    ('XiDyMFoam', 'applications/solvers/combustion/XiFoam/XiDyMFoam'),
    ('XiEngineFoam', 'applications/solvers/combustion/XiFoam/XiEngineFoam'),
    ('XiFoam', 'applications/solvers/combustion/XiFoam'),
    ('acousticFoam', 'applications/solvers/acoustic/acousticFoam'),
    ('adjointOptimisationFoam', 'applications/solvers/incompressible/adjointOptimisationFoam'),
    ('adjointShapeOptimizationFoam', 'applications/solvers/incompressible/adjointShapeOptimizationFoam'),
    ('boundaryFoam', 'applications/solvers/incompressible/boundaryFoam'),
    ('buoyantBoussinesqPimpleFoam', 'applications/solvers/heatTransfer/buoyantBoussinesqPimpleFoam'),
    ('buoyantBoussinesqSimpleFoam', 'applications/solvers/heatTransfer/buoyantBoussinesqSimpleFoam'),
    ('buoyantPbePimpleFoam', 'modules/OpenQBMM/applications/solvers/populationBalance/buoyantPbePimpleFoam'),
    ('buoyantPimpleFoam', 'applications/solvers/heatTransfer/buoyantPimpleFoam'),
    ('cavitatingDyMFoam', 'applications/solvers/multiphase/cavitatingFoam/cavitatingDyMFoam'),
    ('cavitatingFoam', 'applications/solvers/multiphase/cavitatingFoam'),
    ('chemFoam', 'applications/solvers/combustion/chemFoam'),
    ('chtMultiRegionTwoPhaseEulerFoam', 'applications/solvers/heatTransfer/chtMultiRegionFoam/chtMultiRegionTwoPhaseEulerFoam'),
    ('coalChemistryFoam', 'applications/solvers/lagrangian/coalChemistryFoam'),
    ('coldEngineFoam', 'applications/solvers/combustion/coldEngineFoam'),
    ('compressibleInterDyMFoam', 'applications/solvers/multiphase/compressibleInterFoam/compressibleInterDyMFoam'),
    ('compressibleInterFilmFoam', 'applications/solvers/multiphase/compressibleInterFoam/compressibleInterFilmFoam'),
    ('compressibleInterFoam', 'applications/solvers/multiphase/compressibleInterFoam'),
    ('compressibleInterIsoFoam', 'applications/solvers/multiphase/compressibleInterFoam/compressibleInterIsoFoam'),
    ('compressibleMultiphaseInterFoam', 'applications/solvers/multiphase/compressibleMultiphaseInterFoam'),
    ('compressiblePbeTransportFoam', 'modules/OpenQBMM/applications/solvers/compressible/explicitRhoFoam/compressiblePbeTransportFoam'),
    ('denseAGFoam', 'modules/OpenQBMM/applications/solvers/multiphase/denseAGFoam'),
    ('diluteVdfTransportFoam', 'modules/OpenQBMM/applications/solvers/velocityDistributionTransport/diluteVdfTransportFoam'),
    ('dnsFoam', 'applications/solvers/DNS/dnsFoam'),
    ('driftFluxFoam', 'applications/solvers/multiphase/driftFluxFoam'),
    ('dsmcFoam', 'applications/solvers/discreteMethods/dsmc/dsmcFoam'),
    ('electrostaticFoam', 'applications/solvers/electromagnetics/electrostaticFoam'),
    ('engineFoam', 'applications/solvers/lagrangian/sprayFoam/engineFoam'),
    ('explicitRhoFoam', 'modules/OpenQBMM/applications/solvers/compressible/explicitRhoFoam'),
    ('faParkerFukushimaFoam', 'modules/avalanche/applications/solvers/faParkerFukushimaFoam'),
    ('faSavageHutterFoam', 'modules/avalanche/applications/solvers/faSavageHutterFoam'),
    ('faTwoLayerAvalancheFoam', 'modules/avalanche/applications/solvers/faTwoLayerAvalancheFoam'),
    ('financialFoam', 'applications/solvers/financial/financialFoam'),
    ('fireFoam', 'applications/solvers/combustion/fireFoam'),
    ('icoReactingMultiphaseInterFoam', 'applications/solvers/multiphase/icoReactingMultiphaseInterFoam'),
    ('icoUncoupledKinematicParcelDyMFoam', 'applications/solvers/lagrangian/icoUncoupledKinematicParcelFoam/icoUncoupledKinematicParcelDyMFoam'),
    ('icoUncoupledKinematicParcelFoam', 'applications/solvers/lagrangian/icoUncoupledKinematicParcelFoam'),
    ('interCondensatingEvaporatingFoam', 'applications/solvers/multiphase/interCondensatingEvaporatingFoam'),
    ('interIsoFoam', 'applications/solvers/multiphase/interIsoFoam'),
    ('interMixingFoam', 'applications/solvers/multiphase/interFoam/interMixingFoam'),
    ('interPhaseChangeDyMFoam', 'applications/solvers/multiphase/interPhaseChangeFoam/interPhaseChangeDyMFoam'),
    ('interPhaseChangeFoam', 'applications/solvers/multiphase/interPhaseChangeFoam'),
    ('kinematicParcelFoam', 'applications/solvers/lagrangian/kinematicParcelFoam'),
    ('laplacianFoam', 'applications/solvers/basic/laplacianFoam'),
    ('liquidFilmFoam', 'applications/solvers/finiteArea/liquidFilmFoam'),
    ('magneticFoam', 'applications/solvers/electromagnetics/magneticFoam'),
    ('mdEquilibrationFoam', 'applications/solvers/discreteMethods/molecularDynamics/mdEquilibrationFoam'),
    ('mdFoam', 'applications/solvers/discreteMethods/molecularDynamics/mdFoam'),
    ('mhdFoam', 'applications/solvers/electromagnetics/mhdFoam'),
    ('mixingTransportFoam', 'modules/OpenQBMM/applications/solvers/mixing/mixingTransportFoam'),
    ('multiphaseEulerFoam', 'applications/solvers/multiphase/multiphaseEulerFoam'),
    ('multiphaseInterFoam', 'applications/solvers/multiphase/multiphaseInterFoam'),
    ('nonNewtonianIcoFoam', 'applications/solvers/incompressible/nonNewtonianIcoFoam'),
    ('oneWayCoupledVdfTransportFoam', 'modules/OpenQBMM/applications/solvers/velocityDistributionTransport/oneWayCoupledVdfTransportFoam'),
    ('overBuoyantPimpleDyMFoam', 'applications/solvers/heatTransfer/buoyantPimpleFoam/overBuoyantPimpleDyMFoam'),
    ('overCompressibleInterDyMFoam', 'applications/solvers/multiphase/compressibleInterFoam/overCompressibleInterDyMFoam'),
    ('overInterDyMFoam', 'applications/solvers/multiphase/interFoam/overInterDyMFoam'),
    ('overInterPhaseChangeDyMFoam', 'applications/solvers/multiphase/interPhaseChangeFoam/overInterPhaseChangeDyMFoam'),
    ('overLaplacianDyMFoam', 'applications/solvers/basic/laplacianFoam/overLaplacianDyMFoam'),
    ('overPimpleDyMFoam', 'applications/solvers/incompressible/pimpleFoam/overPimpleDyMFoam'),
    ('overPotentialFoam', 'applications/solvers/basic/potentialFoam/overPotentialFoam'),
    ('overRhoPimpleDyMFoam', 'applications/solvers/compressible/rhoPimpleFoam/overRhoPimpleDyMFoam'),
    ('overRhoSimpleFoam', 'applications/solvers/compressible/rhoSimpleFoam/overRhoSimpleFoam'),
    ('overSimpleFoam', 'applications/solvers/incompressible/simpleFoam/overSimpleFoam'),
    ('pbeFoam', 'modules/OpenQBMM/applications/solvers/populationBalance/pbeFoam'),
    ('pbeTransportFoam', 'modules/OpenQBMM/applications/solvers/populationBalance/pbeTransportFoam'),
    ('polydisperseBubbleFoam', 'modules/OpenQBMM/applications/solvers/multiphase/polydisperseBubbleFoam'),
    ('porousSimpleFoam', 'applications/solvers/incompressible/simpleFoam/porousSimpleFoam'),
    ('potentialFreeSurfaceDyMFoam', 'applications/solvers/multiphase/potentialFreeSurfaceFoam/potentialFreeSurfaceDyMFoam'),
    ('potentialFreeSurfaceFoam', 'applications/solvers/multiphase/potentialFreeSurfaceFoam'),
    ('reactingHeterogenousParcelFoam', 'applications/solvers/lagrangian/reactingParcelFoam/reactingHeterogenousParcelFoam'),
    ('reactingMultiphaseEulerFoam', 'applications/solvers/multiphase/reactingMultiphaseEulerFoam'),
    ('reactingParcelFoam', 'applications/solvers/lagrangian/reactingParcelFoam'),
    ('reactingTwoPhaseEulerFoam', 'applications/solvers/multiphase/reactingTwoPhaseEulerFoam'),
    ('rhoCentralFoam', 'applications/solvers/compressible/rhoCentralFoam'),
    ('rhoPimpleAdiabaticFoam', 'applications/solvers/compressible/rhoPimpleAdiabaticFoam'),
    ('rhoPorousSimpleFoam', 'applications/solvers/compressible/rhoSimpleFoam/rhoPorousSimpleFoam'),
    ('rhoReactingBuoyantFoam', 'applications/solvers/combustion/reactingFoam/rhoReactingBuoyantFoam'),
    ('rhoReactingFoam', 'applications/solvers/combustion/reactingFoam/rhoReactingFoam'),
    ('scalarTransportFoam', 'applications/solvers/basic/scalarTransportFoam'),
    ('shallowWaterFoam', 'applications/solvers/incompressible/shallowWaterFoam'),
    ('simpleCoalParcelFoam', 'applications/solvers/lagrangian/simpleCoalParcelFoam'),
    ('simpleReactingParcelFoam', 'applications/solvers/lagrangian/reactingParcelFoam/simpleReactingParcelFoam'),
    ('simpleSprayFoam', 'applications/solvers/lagrangian/sprayFoam/simpleSprayFoam'),
    ('solidDisplacementFoam', 'applications/solvers/stressAnalysis/solidDisplacementFoam'),
    ('solidEquilibriumDisplacementFoam', 'applications/solvers/stressAnalysis/solidEquilibriumDisplacementFoam'),
    ('solidFoam', 'applications/solvers/heatTransfer/solidFoam'),
    ('sonicDyMFoam', 'applications/solvers/compressible/sonicFoam/sonicDyMFoam'),
    ('sonicFoam', 'applications/solvers/compressible/sonicFoam'),
    ('sonicLiquidFoam', 'applications/solvers/compressible/sonicFoam/sonicLiquidFoam'),
    ('sphereSurfactantFoam', 'applications/solvers/finiteArea/sphereSurfactantFoam'),
    ('sprayDyMFoam', 'applications/solvers/lagrangian/sprayFoam/sprayDyMFoam'),
    ('sprayFoam', 'applications/solvers/lagrangian/sprayFoam'),
    ('surfactantFoam', 'applications/solvers/finiteArea/surfactantFoam'),
    ('thermoFoam', 'applications/solvers/heatTransfer/thermoFoam'),
    ('twoLiquidMixingFoam', 'applications/solvers/multiphase/twoLiquidMixingFoam'),
    ('twoPhaseEulerFoam', 'applications/solvers/multiphase/twoPhaseEulerFoam'),
    ('uncoupledKinematicParcelDyMFoam', 'applications/solvers/lagrangian/uncoupledKinematicParcelFoam/uncoupledKinematicParcelDyMFoam'),
    ('uncoupledKinematicParcelFoam', 'applications/solvers/lagrangian/uncoupledKinematicParcelFoam'),
    ('vdfTransportFoam', 'modules/OpenQBMM/applications/solvers/velocityDistributionTransport/vdfTransportFoam'),
)

# Source-derived utilities/converters: (binary name, source dir).
_SOURCE_UTILS: tuple = (
    ('PDRMesh', 'applications/utilities/mesh/advanced/PDRMesh'),
    ('PDRblockMesh', 'applications/utilities/mesh/generation/PDRblockMesh'),
    ('PDRsetFields', 'applications/utilities/preProcessing/PDR/PDRsetFields'),
    ('addr2line', 'applications/utilities/miscellaneous/OSspecific/addr2line'),
    ('adiabaticFlameT', 'applications/utilities/thermophysical/adiabaticFlameT'),
    ('ansysToFoam', 'applications/utilities/mesh/conversion/ansysToFoam'),
    ('applyBoundaryLayer', 'applications/utilities/preProcessing/applyBoundaryLayer'),
    ('attachMesh', 'applications/utilities/mesh/manipulation/attachMesh'),
    ('autoPatch', 'applications/utilities/mesh/manipulation/autoPatch'),
    ('boxTurb', 'applications/utilities/preProcessing/boxTurb'),
    ('ccmToFoam', 'applications/utilities/mesh/conversion/ccm/ccmToFoam'),
    ('cellSizeAndAlignmentGrid', 'applications/utilities/mesh/generation/foamyMesh/cellSizeAndAlignmentGrid'),
    ('cfx4ToFoam', 'applications/utilities/mesh/conversion/cfx4ToFoam'),
    ('changeDictionary', 'applications/utilities/preProcessing/changeDictionary'),
    ('checkFaMesh', 'applications/utilities/finiteArea/checkFaMesh'),
    ('chemkinToFoam', 'applications/utilities/thermophysical/chemkinToFoam'),
    ('collapseEdges', 'applications/utilities/mesh/advanced/collapseEdges'),
    ('combinePatchFaces', 'applications/utilities/mesh/advanced/combinePatchFaces'),
    ('computeMoments', 'modules/OpenQBMM/applications/utilities/computeMoments'),
    ('computeSensitivities', 'applications/utilities/postProcessing/optimisation/computeSensitivities'),
    ('createBaffles', 'applications/utilities/mesh/manipulation/createBaffles'),
    ('createBoxTurb', 'applications/utilities/preProcessing/createBoxTurb'),
    ('createExternalCoupledPatchGeometry', 'applications/utilities/preProcessing/createExternalCoupledPatchGeometry'),
    ('createROMfields', 'applications/utilities/postProcessing/miscellaneous/createROMfields'),
    ('createZeroDirectory', 'applications/utilities/preProcessing/createZeroDirectory'),
    ('cumulativeDisplacement', 'applications/utilities/postProcessing/optimisation/cumulativeDisplacement'),
    ('datToFoam', 'applications/utilities/mesh/conversion/datToFoam'),
    ('deformedGeom', 'applications/utilities/mesh/manipulation/deformedGeom'),
    ('dsmcInitialise', 'applications/utilities/preProcessing/dsmcInitialise'),
    ('engineCompRatio', 'applications/utilities/postProcessing/miscellaneous/engineCompRatio'),
    ('engineSwirl', 'applications/utilities/preProcessing/engineSwirl'),
    ('ensightToFoam', 'applications/utilities/mesh/conversion/ensightToFoam'),
    ('equilibriumCO', 'applications/utilities/thermophysical/equilibriumCO'),
    ('equilibriumFlameT', 'applications/utilities/thermophysical/equilibriumFlameT'),
    ('extrude2DMesh', 'applications/utilities/mesh/generation/extrude2DMesh'),
    ('extrudeMesh', 'applications/utilities/mesh/generation/extrude/extrudeMesh'),
    ('extrudeToRegionMesh', 'applications/utilities/mesh/generation/extrude/extrudeToRegionMesh'),
    ('faceAgglomerate', 'applications/utilities/preProcessing/faceAgglomerate'),
    ('fireToFoam', 'applications/utilities/mesh/conversion/fireToFoam'),
    ('flattenMesh', 'applications/utilities/mesh/manipulation/flattenMesh'),
    ('fluent3DMeshToFoam', 'applications/utilities/mesh/conversion/fluent3DMeshToFoam'),
    ('foamDataToFluent', 'applications/utilities/postProcessing/dataConversion/foamDataToFluent'),
    ('foamDictionary', 'applications/utilities/miscellaneous/foamDictionary'),
    ('foamFormatConvert', 'applications/utilities/miscellaneous/foamFormatConvert'),
    ('foamHasLibrary', 'applications/utilities/miscellaneous/foamHasLibrary'),
    ('foamHelp', 'applications/utilities/miscellaneous/foamHelp'),
    ('foamListRegions', 'applications/utilities/miscellaneous/foamListRegions'),
    ('foamListTimes', 'applications/utilities/miscellaneous/foamListTimes'),
    ('foamMeshToFluent', 'applications/utilities/mesh/conversion/foamMeshToFluent'),
    ('foamRestoreFields', 'applications/utilities/miscellaneous/foamRestoreFields'),
    ('foamToCcm', 'applications/utilities/mesh/conversion/ccm/foamToCcm'),
    ('foamToEnsight', 'applications/utilities/postProcessing/dataConversion/foamToEnsight'),
    ('foamToFireMesh', 'applications/utilities/mesh/conversion/foamToFireMesh'),
    ('foamToGMV', 'applications/utilities/postProcessing/dataConversion/foamToGMV'),
    ('foamToStarMesh', 'applications/utilities/mesh/conversion/foamToStarMesh'),
    ('foamToSurface', 'applications/utilities/mesh/conversion/foamToSurface'),
    ('foamToTetDualMesh', 'applications/utilities/postProcessing/dataConversion/foamToTetDualMesh'),
    ('foamUpgradeCyclics', 'applications/utilities/preProcessing/foamUpgradeCyclics'),
    ('foamyHexMesh', 'applications/utilities/mesh/generation/foamyMesh/foamyHexMesh'),
    ('foamyHexMeshBackgroundMesh', 'applications/utilities/mesh/generation/foamyMesh/foamyHexMeshBackgroundMesh'),
    ('foamyHexMeshSurfaceSimplify', 'applications/utilities/mesh/generation/foamyMesh/foamyHexMeshSurfaceSimplify'),
    ('foamyQuadMesh', 'applications/utilities/mesh/generation/foamyMesh/foamyQuadMesh'),
    ('gambitToFoam', 'applications/utilities/mesh/conversion/gambitToFoam'),
    ('generateMoments', 'modules/OpenQBMM/applications/utilities/generateMoments'),
    ('gridToSTL', 'modules/avalanche/applications/utilities/gridToSTL'),
    ('ideasUnvToFoam', 'applications/utilities/mesh/conversion/ideasUnvToFoam'),
    ('insideCells', 'applications/utilities/mesh/manipulation/insideCells'),
    ('kivaToFoam', 'applications/utilities/mesh/conversion/kivaToFoam'),
    ('lumpedPointForces', 'applications/utilities/postProcessing/lumped/lumpedPointForces'),
    ('lumpedPointMovement', 'applications/utilities/postProcessing/lumped/lumpedPointMovement'),
    ('lumpedPointZones', 'applications/utilities/postProcessing/lumped/lumpedPointZones'),
    ('makeFaMesh', 'applications/utilities/finiteArea/makeFaMesh'),
    ('mapFields', 'applications/utilities/preProcessing/mapFields'),
    ('mapFieldsPar', 'applications/utilities/preProcessing/mapFieldsPar'),
    ('mdInitialise', 'applications/utilities/preProcessing/mdInitialise'),
    ('mergeOrSplitBaffles', 'applications/utilities/mesh/manipulation/mergeOrSplitBaffles'),
    ('mirrorMesh', 'applications/utilities/mesh/manipulation/mirrorMesh'),
    ('mixtureAdiabaticFlameT', 'applications/utilities/thermophysical/mixtureAdiabaticFlameT'),
    ('modifyMesh', 'applications/utilities/mesh/advanced/modifyMesh'),
    ('moveDynamicMesh', 'applications/utilities/mesh/manipulation/moveDynamicMesh'),
    ('moveEngineMesh', 'applications/utilities/mesh/manipulation/moveEngineMesh'),
    ('moveMesh', 'applications/utilities/mesh/manipulation/moveMesh'),
    ('mshToFoam', 'applications/utilities/mesh/conversion/mshToFoam'),
    ('netgenNeutralToFoam', 'applications/utilities/mesh/conversion/netgenNeutralToFoam'),
    ('noise', 'applications/utilities/postProcessing/noise'),
    ('objToVTK', 'applications/utilities/mesh/manipulation/objToVTK'),
    ('orientFaceZone', 'applications/utilities/mesh/manipulation/orientFaceZone'),
    ('particleTracks', 'applications/utilities/postProcessing/lagrangian/particleTracks'),
    ('patchSummary', 'applications/utilities/miscellaneous/patchSummary'),
    ('pdfPlot', 'applications/utilities/postProcessing/miscellaneous/pdfPlot'),
    ('plot3dToFoam', 'applications/utilities/mesh/conversion/plot3dToFoam'),
    ('polyDualMesh', 'applications/utilities/mesh/manipulation/polyDualMesh'),
    ('postChannel', 'applications/utilities/postProcessing/miscellaneous/postChannel'),
    ('profilingSummary', 'applications/utilities/postProcessing/miscellaneous/profilingSummary'),
    ('reconstructParMesh', 'applications/utilities/parallelProcessing/reconstructParMesh'),
    ('reconstructPointDistribution', 'modules/OpenQBMM/applications/utilities/reconstructPointDistribution'),
    ('redistributePar', 'applications/utilities/parallelProcessing/redistributePar'),
    ('refineHexMesh', 'applications/utilities/mesh/advanced/refineHexMesh'),
    ('refineMesh', 'applications/utilities/mesh/manipulation/refineMesh'),
    ('refineWallLayer', 'applications/utilities/mesh/advanced/refineWallLayer'),
    ('refinementLevel', 'applications/utilities/mesh/advanced/refinementLevel'),
    ('releaseAreaMapping', 'modules/avalanche/applications/utilities/releaseAreaMapping'),
    ('removeFaces', 'applications/utilities/mesh/advanced/removeFaces'),
    ('renumberMesh', 'applications/utilities/mesh/manipulation/renumberMesh'),
    ('rotateMesh', 'applications/utilities/mesh/manipulation/rotateMesh'),
    ('selectCells', 'applications/utilities/mesh/advanced/selectCells'),
    ('setAlphaField', 'applications/utilities/preProcessing/setAlphaField'),
    ('setExprBoundaryFields', 'applications/utilities/preProcessing/setExprBoundaryFields'),
    ('setExprFields', 'applications/utilities/preProcessing/setExprFields'),
    ('setSet', 'applications/utilities/mesh/manipulation/setSet'),
    ('setTurbulenceFields', 'applications/utilities/preProcessing/setTurbulenceFields'),
    ('setsToZones', 'applications/utilities/mesh/manipulation/setsToZones'),
    ('singleCellMesh', 'applications/utilities/mesh/manipulation/singleCellMesh'),
    ('slopeMesh', 'modules/avalanche/applications/utilities/slopeMesh'),
    ('smapToFoam', 'applications/utilities/postProcessing/dataConversion/smapToFoam'),
    ('smoothSurfaceData', 'applications/utilities/preProcessing/smoothSurfaceData'),
    ('snappyRefineMesh', 'applications/utilities/mesh/advanced/snappyRefineMesh'),
    ('splitCells', 'applications/utilities/mesh/advanced/splitCells'),
    ('splitMesh', 'applications/utilities/mesh/manipulation/splitMesh'),
    ('star4ToFoam', 'applications/utilities/mesh/conversion/star4ToFoam'),
    ('steadyParticleTracks', 'applications/utilities/postProcessing/lagrangian/steadyParticleTracks'),
    ('stitchMesh', 'applications/utilities/mesh/manipulation/stitchMesh'),
    ('subsetMesh', 'applications/utilities/mesh/manipulation/subsetMesh'),
    ('surfaceAdd', 'applications/utilities/surface/surfaceAdd'),
    ('surfaceBooleanFeatures', 'applications/utilities/surface/surfaceBooleanFeatures'),
    ('surfaceCheck', 'applications/utilities/surface/surfaceCheck'),
    ('surfaceClean', 'applications/utilities/surface/surfaceClean'),
    ('surfaceCoarsen', 'applications/utilities/surface/surfaceCoarsen'),
    ('surfaceConvert', 'applications/utilities/surface/surfaceConvert'),
    ('surfaceFeatureConvert', 'applications/utilities/surface/surfaceFeatureConvert'),
    ('surfaceFind', 'applications/utilities/surface/surfaceFind'),
    ('surfaceHookUp', 'applications/utilities/surface/surfaceHookUp'),
    ('surfaceInertia', 'applications/utilities/surface/surfaceInertia'),
    ('surfaceInflate', 'applications/utilities/surface/surfaceInflate'),
    ('surfaceLambdaMuSmooth', 'applications/utilities/surface/surfaceLambdaMuSmooth'),
    ('surfaceMeshConvert', 'applications/utilities/surface/surfaceMeshConvert'),
    ('surfaceMeshExport', 'applications/utilities/surface/surfaceMeshExport'),
    ('surfaceMeshExtract', 'applications/utilities/surface/surfaceMeshExtract'),
    ('surfaceMeshImport', 'applications/utilities/surface/surfaceMeshImport'),
    ('surfaceMeshInfo', 'applications/utilities/surface/surfaceMeshInfo'),
    ('surfaceOrient', 'applications/utilities/surface/surfaceOrient'),
    ('surfacePatch', 'applications/utilities/surface/surfacePatch'),
    ('surfacePointMerge', 'applications/utilities/surface/surfacePointMerge'),
    ('surfaceRedistributePar', 'applications/utilities/surface/surfaceRedistributePar'),
    ('surfaceRefineRedGreen', 'applications/utilities/surface/surfaceRefineRedGreen'),
    ('surfaceSplitByPatch', 'applications/utilities/surface/surfaceSplitByPatch'),
    ('surfaceSplitByTopology', 'applications/utilities/surface/surfaceSplitByTopology'),
    ('surfaceSplitNonManifolds', 'applications/utilities/surface/surfaceSplitNonManifolds'),
    ('surfaceSubset', 'applications/utilities/surface/surfaceSubset'),
    ('surfaceToPatch', 'applications/utilities/surface/surfaceToPatch'),
    ('surfaceTransformPoints', 'applications/utilities/surface/surfaceTransformPoints'),
    ('temporalInterpolate', 'applications/utilities/postProcessing/miscellaneous/temporalInterpolate'),
    ('tetgenToFoam', 'applications/utilities/mesh/conversion/tetgenToFoam'),
    ('transformPoints', 'applications/utilities/mesh/manipulation/transformPoints'),
    ('viewFactorsGen', 'applications/utilities/preProcessing/viewFactorsGen'),
    ('vtkUnstructuredToFoam', 'applications/utilities/mesh/conversion/vtkUnstructuredToFoam'),
    ('wallFunctionTable', 'applications/utilities/preProcessing/wallFunctionTable'),
    ('writeMeshObj', 'applications/utilities/mesh/conversion/writeMeshObj'),
    ('writeMorpherCPs', 'applications/utilities/preProcessing/optimisation/writeMorpherCPs'),
    ('zipUpMesh', 'applications/utilities/mesh/manipulation/zipUpMesh'),
)


_REASON_TYPED = "typed schema + fixtures; see command_schemas"
_REASON_RAW = "no typed schema; raw advanced execution only with vetting, never auto-executed"

_MODULE_TAXONOMY = {
    "OpenQBMM": ("physics", "qbmm-module"),
    "avalanche": ("mesh", "avalanche-module"),
}

_UTIL_TAXONOMY = {
    "mesh": ("mesh", None),
    "surface": ("geometry", "surface"),
    "preProcessing": ("init", "pre-processing"),
    "postProcessing": ("post", None),
    "parallelProcessing": ("parallel", None),
    "thermophysical": ("physics", "thermophysical"),
    "finiteArea": ("mesh", "finite-area"),
    "miscellaneous": ("case", "misc"),
}


def _solver_taxonomy(srcdir: str) -> tuple:
    """Derive (family, subcategory) from a solver source dir (deterministic)."""
    tail = srcdir.split("/solvers/", 1)[1].split("/")
    return tail[0], tail[-2] if len(tail) > 2 else tail[0]


def _util_taxonomy(srcdir: str) -> tuple:
    """Derive (category, subcategory, kind) from a utility source dir."""
    parts = srcdir.split("/")
    if parts[0] == "modules":
        cat, sub = _MODULE_TAXONOMY[parts[1]]
        return cat, sub, "utility"
    rest = srcdir.split("/utilities/", 1)[1].split("/")
    top = rest[0]
    cat, fixed = _UTIL_TAXONOMY[top]
    if top == "mesh":
        kind = "converter" if "conversion" in rest else "utility"
        sub = rest[1] if len(rest) > 2 else "general"
        return cat, sub, kind
    sub = rest[1] if (fixed is None and len(rest) > 2) else (fixed or "general")
    return cat, sub, "utility"


DOC_BASE = "https://doc.openfoam.com/2312/tools/"
SOURCE_TAG_ALIAS = SOURCE_TAG


def _row(name, cat, sub, kind, proof, avail, family, src, reason):
    if not reason:
        reason = _REASON_TYPED if avail == "ACTIVE-TYPED" else _REASON_RAW
    return {
        "uid": "of2312:" + name, "edition": "esi", "release": "v2312",
        "category": cat, "subcategory": sub, "command_name": name,
        "kind": kind, "controlled_file": "",
        "proof_level": proof, "availability": avail,
        "solver_family": family,
        "documentation_url": DOC_BASE, "source_revision": SOURCE_TAG,
        "source_path": src, "reason": reason,
        "legacy_021": name in LEGACY_8,
    }


def inventory() -> list[dict]:
    rows = [_row(*entry) for entry in _CURATED]
    for name, src in _SOURCE_SOLVERS:
        family, sub = _solver_taxonomy(src)
        rows.append(_row(name, "solver", sub, "solver", "V2312-SOURCE",
                         "RAW-ADVANCED", family, src, ""))
    for name, src in _SOURCE_UTILS:
        cat, sub, kind = _util_taxonomy(src)
        rows.append(_row(name, cat, sub, kind, "V2312-SOURCE",
                         "RAW-ADVANCED", "", src, ""))
    rows.sort(key=lambda r: r["uid"])
    return rows


def coverage_counts() -> dict:
    rows = inventory()
    by_avail: dict[str, int] = {}
    for row in rows:
        by_avail[row["availability"]] = by_avail.get(row["availability"], 0) + 1
    return {
        "discovered_in_scope": len(rows),
        "classified": len(rows),
        "by_availability": by_avail,
        "legacy_021_preserved": len(LEGACY_8),
        "active_typed": sum(1 for r in rows if r["availability"] == "ACTIVE-TYPED"),
        "denominator": {
            "solver_exe": SOLVER_EXE_COUNT,
            "utility_exe": UTILITY_EXE_COUNT,
            "non_exe_configs": NON_EXE_CONFIG_COUNT,
        },
        "archive": {
            "name": ARCHIVE_NAME, "sha256": ARCHIVE_SHA256,
            "bytes": ARCHIVE_BYTES, "source_revision": SOURCE_TAG,
        },
        "site_binaries": "BLOCKED_ENV: no v2312 runtime on site VM; binaries_on_path all null",
        "note": "source-derived 305 (122 solver EXE + 175 utility EXE + 8 non-EXE configs); exhaustive site-binary claim BLOCKED_ENV without v2312 host",
    }
