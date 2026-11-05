"""CURRENT_ABILITY_MATRIX builder (W65 UNIT A, HPC-W65-BASE-001)."""
from __future__ import annotations
from dataclasses import dataclass
STATUS_DONE = "DONE"
STATUS_PARTIAL = "PARTIAL"
STATUS_MISSING = "MISSING"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNCERTAIN = "UNCERTAIN"
VALID_STATUSES = frozenset({STATUS_DONE, STATUS_PARTIAL, STATUS_MISSING, STATUS_BLOCKED, STATUS_UNCERTAIN})
OWNER_UNIT_A = "W65-UNIT-A"
OWNER_UNIT_B = "W65-UNIT-B"
OWNER_UNIT_C = "W65-UNIT-C"
OWNER_UNIT_D = "W65-UNIT-D"
OWNER_UNIT_E = "W65-UNIT-E"
OWNER_UNIT_F = "W65-UNIT-F"
VERSION_SOURCE_TREE = "tree audit at develop merge 6b2003e5"
@dataclass(frozen=True)
class AbilityRow:
    feature_id: str
    source_path: str
    current_behavior: str
    gui_evidence: str
    unit_evidence: str
    packaged_vm_evidence: str
    version_source: str
    status: str
    owner: str
    delta: str
    def to_dict(self):
        return {"feature_id": self.feature_id, "source_path": self.source_path, "current_behavior": self.current_behavior, "gui_evidence": self.gui_evidence, "unit_evidence": self.unit_evidence, "packaged_vm_evidence": self.packaged_vm_evidence, "version_source": self.version_source, "status": self.status, "owner": self.owner, "delta": self.delta}
def _row(feature_id, source_path, behavior, status, delta, gui="none", unit="none", vm="none", owner=OWNER_UNIT_A):
    return AbilityRow(feature_id, source_path, behavior, gui, unit, vm, VERSION_SOURCE_TREE, status, owner, delta)
def build_matrix():
    inv = "hpc_gui.openfoam_v2312.inventory"
    unit_c = "tests/test_w65_physics_numerics_solver.py"
    return (
        _row("HPC-W65-BASE-001", inv, "9-command P0 inventory present, all draft-only and raw", STATUS_PARTIAL, "typed schemas and live runs deferred", unit="tests/test_w65_inventory.py"),
        _row("HPC-W65-HOST-002", "hpc_gui.plugins.linter_tools", "linter tool lazy loader present; no Case Studio engine", STATUS_PARTIAL, "studio adapter deferred to UNIT A follow-up"),
        _row("HPC-W65-CAT-003", inv, "P0 names classified raw with provenance; broader v2312 families not yet inventoried", STATUS_PARTIAL, "broaden catalog per UNIT A follow-up", unit="tests/test_w65_inventory.py"),
        _row("HPC-W65-GEOM-004", "hpc_gui.openfoam_v2312.geometry", "surface import descriptors with safety gate; no CAD auto-conversion", STATUS_PARTIAL, "live import deferred; UNIT F reactivation", unit="tests/test_w65_geometry_mesh.py", owner=OWNER_UNIT_B),
        _row("HPC-W65-MESH-005", "hpc_gui.openfoam_v2312.mesh", "mesh recipes with ordering guards; no solver execution", STATUS_PARTIAL, "dictionary generation deferred; UNIT F reactivation", unit="tests/test_w65_geometry_mesh.py", owner=OWNER_UNIT_B),
        _row("HPC-W65-PHYS-006", "hpc_gui.openfoam_v2312.physics", "solver-family physics contexts with CHT and region guards; no live runs", STATUS_PARTIAL, "live behavior deferred; UNIT F reactivation", unit=unit_c, owner=OWNER_UNIT_C),
        _row("HPC-W65-BC-007", "hpc_gui.openfoam_v2312.bc", "patch and field BC descriptors with dimension checks; no case writes", STATUS_PARTIAL, "template generation deferred; UNIT F reactivation", unit=unit_c, owner=OWNER_UNIT_C),
        _row("HPC-W65-NUM-008", "hpc_gui.openfoam_v2312.numerics", "controlDict and solver-entry schemas with range guards; no dictionary writes", STATUS_PARTIAL, "dictionary generation deferred; UNIT F reactivation", unit=unit_c, owner=OWNER_UNIT_C),
        _row("HPC-W65-SOLV-009", "hpc_gui.openfoam_v2312.solver", "ordered run pipelines with mesh-before-solve guards; draft only", STATUS_PARTIAL, "live execution deferred; UNIT F reactivation", unit=unit_c, owner=OWNER_UNIT_C),
        _row("HPC-W65-POST-010", "hpc_gui.openfoam_v2312.postprocess", "post views with tool and artifact guards; absent artifacts reported missing", STATUS_PARTIAL, "live parsing deferred; UNIT F reactivation", unit="tests/test_w65_post_flow_studio.py", owner=OWNER_UNIT_D),
        _row("HPC-W65-FLOW-011", "hpc_gui.openfoam_v2312.flow", "ordered DAG with producer guards and legacy command import; no execution", STATUS_PARTIAL, "template fixtures deferred to UNIT F", unit="tests/test_w65_post_flow_studio.py", owner=OWNER_UNIT_D),
        _row("HPC-W65-UI-012", "hpc_gui.openfoam_v2312.studio", "studio page descriptors with action and required-page guards; no widgets", STATUS_PARTIAL, "headed GUI deferred; UNIT F reactivation", unit="tests/test_w65_post_flow_studio.py", owner=OWNER_UNIT_D),
        _row("HPC-W65-LINT-013", "hpc_gui.openfoam_v2312.linter", "rule packs with levels, severity, and certainty; positive and negative fixtures; no second engine", STATUS_PARTIAL, "live rule growth deferred; UNIT F reactivation", unit="tests/test_w65_lint_sftp_jobs_safety.py", owner=OWNER_UNIT_E),
        _row("HPC-W65-SFTP-014", "hpc_gui.openfoam_v2312.sftp", "per-file digest and stage, commit, and revert descriptors with partial status; no transfers", STATUS_PARTIAL, "live transfer deferred; UNIT F reactivation", unit="tests/test_w65_lint_sftp_jobs_safety.py", owner=OWNER_UNIT_E),
        _row("HPC-W65-JOBS-015", "hpc_gui.openfoam_v2312.jobs", "reviewable job drafts with solver, module, and rank guards; no auto-submit", STATUS_PARTIAL, "live submission deferred; UNIT F reactivation", unit="tests/test_w65_lint_sftp_jobs_safety.py", owner=OWNER_UNIT_E),
        _row("HPC-W65-SAFE-016", "hpc_gui.openfoam_v2312.safety", "save policies with traversal, symlink, directive, and argv guards", STATUS_PARTIAL, "live save deferred; UNIT F reactivation", unit="tests/test_w65_lint_sftp_jobs_safety.py", owner=OWNER_UNIT_E),
        _row("HPC-W65-VM-017", "no guest run in this unit", "Windows 11 and Ubuntu guest acceptance not executed; 2026-11-05 probes: Windows11 Off local and Kole, no v2312 binary on host PATH", STATUS_BLOCKED, "BLOCKED_ENV, reactivation is UNIT F guest execution"),
        _row("HPC-W65-RUNTIME-018", "no live run in this unit", "no v2312 binary execution performed here; 2026-11-05 host probe found no OpenFOAM binaries on PATH", STATUS_BLOCKED, "BLOCKED_ENV, reactivation is UNIT F live runs"),
        _row("HPC-W65-REG-019", "tests/test_w65_inventory.py", "inventory, geometry, mesh, physics, numerics, post, flow, studio, lint, sftp, jobs, safety, runtime, packaging, and evidence regression tests; broader suites untouched", STATUS_PARTIAL, "extend per unit", unit="tests/test_w65_inventory.py"),
        _row("HPC-W65-PACK-020", "hpc_gui.openfoam_v2312.packaging", "install, upgrade, rollback, and uninstall lifecycle guards with hash binding; no package built or verified", STATUS_PARTIAL, "descriptors only; package build outstanding", unit="tests/test_w65_runtime_packaging_evidence.py", owner=OWNER_UNIT_F),
        _row("HPC-W65-EVID-021", "this matrix plus inventory fixture", "matrix rows, checked-in fixture, and verdict computation", STATUS_PARTIAL, "verdict logic bound; live evidence outstanding", unit="tests/test_w65_runtime_packaging_evidence.py"),
        _row("HPC-W65-CLOSE-022", "controller closeout pending", "P0 plus P1 scope incomplete; wave stays pending", STATUS_BLOCKED, "reactivation is full P0 plus P1 acceptance"),
    )
def validate_matrix(rows):
    seen = set()
    for row in rows:
        if row.feature_id in seen:
            raise ValueError("duplicate feature id " + row.feature_id)
        seen.add(row.feature_id)
        if row.status not in VALID_STATUSES:
            raise ValueError("bad status for " + row.feature_id)
    expected = tuple(row.feature_id for row in build_matrix())
    actual = tuple(row.feature_id for row in rows)
    if actual != expected:
        raise ValueError("matrix order drift detected")
def to_dicts():
    return [row.to_dict() for row in build_matrix()]
