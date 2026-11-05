'''Live-run result descriptors (W65 UNIT F, HPC-W65-RUNTIME-018).'''
from __future__ import annotations
from dataclasses import dataclass
from hpc_gui.openfoam_v2312.physics import KNOWN_SOLVERS
STATUS_EXECUTED_OK = 'EXECUTED_OK'
STATUS_EXECUTED_FAIL = 'EXECUTED_FAIL'
STATUS_BLOCKED_ENV = 'BLOCKED_ENV'
STATUS_UNPROVEN = 'UNPROVEN_NO_HASH'
HEX_DIGITS = frozenset('0123456789abcdefABCDEF')
@dataclass(frozen=True)
class LiveRunSpec:
    case_path: str = ''
    solver: str = 'simpleFoam'
    argv: tuple = ()
    ranks: int = 1
    def to_dict(self):
        return {'case_path': self.case_path, 'solver': self.solver, 'argv': list(self.argv), 'ranks': self.ranks}
    @staticmethod
    def from_dict(raw):
        return LiveRunSpec(case_path=str(raw.get('case_path', '')), solver=str(raw.get('solver', 'simpleFoam')), argv=tuple(str(a) for a in raw.get('argv', ())), ranks=int(raw.get('ranks', 1)))
def validate_spec(spec):
    errors = []
    if not spec.case_path:
        errors.append('empty case path')
    if spec.solver not in KNOWN_SOLVERS:
        errors.append('unknown solver: ' + spec.solver)
    if spec.ranks < 1:
        errors.append('run needs at least 1 rank')
    for entry in spec.argv:
        if not entry:
            errors.append('empty argv entry')
        elif chr(10) in entry or chr(13) in entry:
            errors.append('argv entry carries newline')
    return tuple(errors)
@dataclass(frozen=True)
class LiveRunResult:
    case_path: str = ''
    solver: str = 'simpleFoam'
    executed: bool = False
    exit_code: int = 0
    stdout_tail: str = ''
    stderr_tail: str = ''
    binary_hash: str = ''
    def to_dict(self):
        return {'case_path': self.case_path, 'solver': self.solver, 'executed': self.executed, 'exit_code': self.exit_code, 'stdout_tail': self.stdout_tail, 'stderr_tail': self.stderr_tail, 'binary_hash': self.binary_hash}
    @staticmethod
    def from_dict(raw):
        return LiveRunResult(case_path=str(raw.get('case_path', '')), solver=str(raw.get('solver', 'simpleFoam')), executed=bool(raw.get('executed', False)), exit_code=int(raw.get('exit_code', 0)), stdout_tail=str(raw.get('stdout_tail', '')), stderr_tail=str(raw.get('stderr_tail', '')), binary_hash=str(raw.get('binary_hash', '')))
def validate_result(result):
    errors = []
    if not result.case_path:
        errors.append('empty case path')
    if result.solver not in KNOWN_SOLVERS:
        errors.append('unknown solver: ' + result.solver)
    if result.executed and not result.binary_hash:
        errors.append('executed run without binary hash is unproven')
    if result.binary_hash and (len(result.binary_hash) != 64 or any(c not in HEX_DIGITS for c in result.binary_hash)):
        errors.append('binary hash must be 64 hex characters')
    return tuple(errors)
def summarize_result(result):
    if not result.executed:
        return STATUS_BLOCKED_ENV
    if not result.binary_hash:
        return STATUS_UNPROVEN
    if result.exit_code == 0:
        return STATUS_EXECUTED_OK
    return STATUS_EXECUTED_FAIL
def is_proven(result):
    return result.executed and bool(result.binary_hash) and result.exit_code == 0