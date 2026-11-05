"""OpenFOAM linter rule packs (W65 UNIT E, HPC-W65-LINT-013)."""

from __future__ import annotations
from dataclasses import dataclass
FAMILY_DICT = 'OF-DICT'
FAMILY_CASE = 'OF-CASE'
FAMILY_CTRL = 'OF-CTRL'
FAMILY_SOLVER = 'OF-SOLVER'
FAMILY_BC = 'OF-BC'
FAMILY_MESH = 'OF-MESH'
FAMILY_CROSS = 'OF-CROSS'
FAMILY_PAR = 'OF-PAR'
FAMILY_HPC = 'OF-HPC'
FAMILY_SEC = 'OF-SEC'
KNOWN_FAMILIES = (FAMILY_DICT, FAMILY_CASE, FAMILY_CTRL, FAMILY_SOLVER, FAMILY_BC, FAMILY_MESH, FAMILY_CROSS, FAMILY_PAR, FAMILY_HPC, FAMILY_SEC)
LEVEL_STATIC = 'STATIC'
LEVEL_CONTEXTUAL = 'CONTEXTUAL'
LEVEL_RUNTIME = 'RUNTIME'
KNOWN_LEVELS = (LEVEL_STATIC, LEVEL_CONTEXTUAL, LEVEL_RUNTIME)
SEVERITY_ERROR = 'error'
SEVERITY_WARNING = 'warning'
SEVERITY_INFO = 'info'
KNOWN_SEVERITIES = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)
CERTAINTY_HIGH = 'high'
CERTAINTY_MEDIUM = 'medium'
CERTAINTY_LOW = 'low'
KNOWN_CERTAINTIES = (CERTAINTY_HIGH, CERTAINTY_MEDIUM, CERTAINTY_LOW)
RULE_FAMILY = {
    'OF-DICT-001': FAMILY_DICT,
    'OF-CASE-001': FAMILY_CASE,
    'OF-CTRL-001': FAMILY_CTRL,
    'OF-SOLVER-001': FAMILY_SOLVER,
    'OF-BC-001': FAMILY_BC,
    'OF-MESH-001': FAMILY_MESH,
    'OF-CROSS-001': FAMILY_CROSS,
    'OF-PAR-001': FAMILY_PAR,
    'OF-HPC-001': FAMILY_HPC,
    'OF-SEC-001': FAMILY_SEC,
}
KNOWN_RULES = tuple(RULE_FAMILY)
RULE_LEVELS = {
    'OF-DICT-001': LEVEL_STATIC,
    'OF-CASE-001': LEVEL_STATIC,
    'OF-CTRL-001': LEVEL_STATIC,
    'OF-SOLVER-001': LEVEL_STATIC,
    'OF-BC-001': LEVEL_STATIC,
    'OF-MESH-001': LEVEL_STATIC,
    'OF-CROSS-001': LEVEL_STATIC,
    'OF-PAR-001': LEVEL_STATIC,
    'OF-HPC-001': LEVEL_CONTEXTUAL,
    'OF-SEC-001': LEVEL_STATIC,
}
@dataclass(frozen=True)
class LintRule:
    rule_id: str = 'OF-DICT-001'
    family: str = FAMILY_DICT
    severity: str = SEVERITY_ERROR
    level: str = LEVEL_STATIC
    title: str = 'rule'
    def to_dict(self):
        return {'rule_id': self.rule_id, 'family': self.family, 'severity': self.severity, 'level': self.level, 'title': self.title}
    @staticmethod
    def from_dict(raw):
        return LintRule(rule_id=str(raw.get('rule_id', 'OF-DICT-001')), family=str(raw.get('family', FAMILY_DICT)), severity=str(raw.get('severity', SEVERITY_ERROR)), level=str(raw.get('level', LEVEL_STATIC)), title=str(raw.get('title', 'rule')))
@dataclass(frozen=True)
class LintFinding:
    rule_id: str = 'OF-DICT-001'
    severity: str = SEVERITY_ERROR
    certainty: str = CERTAINTY_HIGH
    path: str = ''
    line: int = 1
    column: int = 0
    message: str = ''
    def to_dict(self):
        return {'rule_id': self.rule_id, 'severity': self.severity, 'certainty': self.certainty, 'path': self.path, 'line': self.line, 'column': self.column, 'message': self.message}
    @staticmethod
    def from_dict(raw):
        return LintFinding(rule_id=str(raw.get('rule_id', 'OF-DICT-001')), severity=str(raw.get('severity', SEVERITY_ERROR)), certainty=str(raw.get('certainty', CERTAINTY_HIGH)), path=str(raw.get('path', '')), line=int(raw.get('line', 1)), column=int(raw.get('column', 0)), message=str(raw.get('message', '')))
def validate_rule(rule):
    errors = []
    if not rule.rule_id:
        errors.append('empty rule id')
        return tuple(errors)
    if rule.family not in KNOWN_FAMILIES:
        errors.append('unknown rule family: ' + rule.family)
    elif not rule.rule_id.startswith(rule.family):
        errors.append('rule id does not match family: ' + rule.rule_id)
    if rule.severity not in KNOWN_SEVERITIES:
        errors.append('unknown severity: ' + rule.severity)
    if rule.level not in KNOWN_LEVELS:
        errors.append('unknown level: ' + rule.level)
    if not rule.title:
        errors.append('empty rule title')
    return tuple(errors)
def validate_finding(finding):
    errors = []
    if finding.rule_id not in RULE_FAMILY:
        errors.append('unknown rule id: ' + finding.rule_id)
    if finding.severity not in KNOWN_SEVERITIES:
        errors.append('unknown severity: ' + finding.severity)
    if finding.certainty not in KNOWN_CERTAINTIES:
        errors.append('unknown certainty: ' + finding.certainty)
    if not finding.path:
        errors.append('empty finding path')
    if finding.line < 1:
        errors.append('finding line must be at least 1')
    if finding.column < 0:
        errors.append('finding column must not be negative')
    if not finding.message:
        errors.append('empty finding message')
    return tuple(errors)
def list_rules():
    return KNOWN_RULES
def rule_level(rule_id):
    return RULE_LEVELS.get(rule_id, '')
