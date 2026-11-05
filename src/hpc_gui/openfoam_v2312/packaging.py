'''Package lifecycle descriptors (W65 UNIT F, HPC-W65-PACK-020).'''
from __future__ import annotations
from dataclasses import dataclass
CHANNELS = ('stable', 'test')
STAGE_INSTALL = 'installed'
STAGE_UPGRADE = 'upgraded'
STAGE_ROLLBACK = 'rolled_back'
STAGE_UNINSTALL = 'uninstalled'
LIFECYCLE = (STAGE_INSTALL, STAGE_UPGRADE, STAGE_ROLLBACK, STAGE_UNINSTALL)
STATUS_COMPLETE = 'COMPLETE'
STATUS_PARTIAL = 'PARTIAL'
HEX_DIGITS = frozenset('0123456789abcdefABCDEF')
@dataclass(frozen=True)
class PackageIdentity:
    name: str = ''
    version: str = ''
    sha256: str = ''
    channel: str = 'test'
    def to_dict(self):
        return {'name': self.name, 'version': self.version, 'sha256': self.sha256, 'channel': self.channel}
    @staticmethod
    def from_dict(raw):
        return PackageIdentity(name=str(raw.get('name', '')), version=str(raw.get('version', '')), sha256=str(raw.get('sha256', '')), channel=str(raw.get('channel', 'test')))
def validate_identity(pkg):
    errors = []
    if not pkg.name:
        errors.append('empty package name')
    if not pkg.version:
        errors.append('empty package version')
    if len(pkg.sha256) != 64 or any(c not in HEX_DIGITS for c in pkg.sha256):
        errors.append('package sha must be 64 hex characters')
    if pkg.channel not in CHANNELS:
        errors.append('unknown channel: ' + pkg.channel)
    return tuple(errors)
def validate_transition(history, action, dirty_source=False):
    errors = []
    if dirty_source:
        errors.append('dirty source tree refuses lifecycle action')
        return tuple(errors)
    seen = list(history)
    if action == STAGE_INSTALL:
        if STAGE_INSTALL in seen:
            errors.append('package already installed')
    elif action == STAGE_UPGRADE:
        if STAGE_INSTALL not in seen:
            errors.append('upgrade requires installed package')
    elif action == STAGE_ROLLBACK:
        if STAGE_UPGRADE not in seen:
            errors.append('rollback requires upgraded package')
    elif action == STAGE_UNINSTALL:
        if STAGE_INSTALL not in seen:
            errors.append('uninstall requires installed package')
    else:
        errors.append('unknown lifecycle action: ' + str(action))
    return tuple(errors)
def summarize_lifecycle(history):
    order = []
    for stage in history:
        if stage in LIFECYCLE and stage not in order:
            order.append(stage)
    if order == list(LIFECYCLE):
        return STATUS_COMPLETE
    return STATUS_PARTIAL