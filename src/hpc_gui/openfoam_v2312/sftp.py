"""Remote case descriptors (W65 UNIT E, HPC-W65-SFTP-014)."""

from __future__ import annotations
from dataclasses import dataclass
PHASE_STAGE = 'stage'
PHASE_COMMIT = 'commit'
PHASE_REVERT = 'revert'
KNOWN_PHASES = (PHASE_STAGE, PHASE_COMMIT, PHASE_REVERT)
STATUS_COMPLETE = 'complete'
STATUS_PARTIAL = 'partial'
STATUS_EMPTY = 'empty'
HEX_DIGITS = frozenset('0123456789abcdef')
@dataclass(frozen=True)
class RemoteFile:
    path: str = ''
    digest: str = ''
    size: int = 0
    def to_dict(self):
        return {'path': self.path, 'digest': self.digest, 'size': self.size}
    @staticmethod
    def from_dict(raw):
        return RemoteFile(path=str(raw.get('path', '')), digest=str(raw.get('digest', '')), size=int(raw.get('size', 0)))
@dataclass(frozen=True)
class StageResult:
    path: str = ''
    phase: str = PHASE_STAGE
    ok: bool = True
    detail: str = ''
    def to_dict(self):
        return {'path': self.path, 'phase': self.phase, 'ok': self.ok, 'detail': self.detail}
    @staticmethod
    def from_dict(raw):
        return StageResult(path=str(raw.get('path', '')), phase=str(raw.get('phase', PHASE_STAGE)), ok=bool(raw.get('ok', True)), detail=str(raw.get('detail', '')))
def _has_escape(path):
    return '..' in path.split('/')
def validate_remote_file(item):
    errors = []
    if not item.path:
        errors.append('empty remote path')
        return tuple(errors)
    if chr(92) in item.path:
        errors.append('remote path must use forward slashes: ' + item.path)
    if _has_escape(item.path):
        errors.append('remote path escapes case root: ' + item.path)
    if item.size < 0:
        errors.append('negative file size: ' + item.path)
    if not item.digest:
        errors.append('missing digest, unverified content must not be staged: ' + item.path)
    elif len(item.digest) != 64 or any(ch not in HEX_DIGITS for ch in item.digest):
        errors.append('bad sha256 digest: ' + item.path)
    return tuple(errors)
def validate_stage(item):
    errors = []
    if not item.path:
        errors.append('empty result path')
    if item.phase not in KNOWN_PHASES:
        errors.append('unknown phase: ' + item.phase)
    if not item.ok and not item.detail:
        errors.append('failure without detail hides partial status: ' + item.path)
    return tuple(errors)
def summarize(results):
    if not results:
        return STATUS_EMPTY
    for item in results:
        if not item.ok:
            return STATUS_PARTIAL
    return STATUS_COMPLETE
