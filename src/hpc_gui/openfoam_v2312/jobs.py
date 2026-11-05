"""Reviewable job drafts (W65 UNIT E, HPC-W65-JOBS-015)."""

from __future__ import annotations
from dataclasses import dataclass
from hpc_gui.openfoam_v2312.physics import KNOWN_SOLVERS
@dataclass(frozen=True)
class JobDraft:
    case_path: str = ''
    solver: str = 'simpleFoam'
    module: str = ''
    ranks: int = 1
    walltime_min: int = 60
    submit: bool = False
    def to_dict(self):
        return {'case_path': self.case_path, 'solver': self.solver, 'module': self.module, 'ranks': self.ranks, 'walltime_min': self.walltime_min, 'submit': self.submit}
    @staticmethod
    def from_dict(raw):
        return JobDraft(case_path=str(raw.get('case_path', '')), solver=str(raw.get('solver', 'simpleFoam')), module=str(raw.get('module', '')), ranks=int(raw.get('ranks', 1)), walltime_min=int(raw.get('walltime_min', 60)), submit=bool(raw.get('submit', False)))
def validate_draft(draft):
    errors = []
    if not draft.case_path:
        errors.append('empty case path')
    else:
        if chr(92) in draft.case_path:
            errors.append('case path must use forward slashes')
        if '..' in draft.case_path.split('/'):
            errors.append('case path escapes workspace')
    if draft.solver not in KNOWN_SOLVERS:
        errors.append('unknown solver: ' + draft.solver)
    if not draft.module:
        errors.append('empty environment module')
    if draft.ranks < 1:
        errors.append('job needs at least 1 rank')
    if draft.walltime_min <= 0:
        errors.append('walltime must be positive')
    if draft.submit:
        errors.append('draft must not auto-submit')
    return tuple(errors)
