"""Safe save and static-content guards (W65 UNIT E, HPC-W65-SAFE-016)."""

from __future__ import annotations
from dataclasses import dataclass
EXEC_DIRECTIVES = ('#codeStream', '#calc', '#eval')
UNTRUSTED_SCRIPTS = ('Allrun', 'Allclean')
SHELL_RISKY = (';', '|', '&', '$', chr(96))
@dataclass(frozen=True)
class SavePolicy:
    allow_overwrite: bool = False
    require_backup: bool = True
    allow_symlink: bool = False
    def to_dict(self):
        return {'allow_overwrite': self.allow_overwrite, 'require_backup': self.require_backup, 'allow_symlink': self.allow_symlink}
    @staticmethod
    def from_dict(raw):
        return SavePolicy(allow_overwrite=bool(raw.get('allow_overwrite', False)), require_backup=bool(raw.get('require_backup', True)), allow_symlink=bool(raw.get('allow_symlink', False)))
def validate_save(path, policy, exists=False, is_symlink=False):
    errors = []
    if not path:
        errors.append('empty save path')
        return tuple(errors)
    if chr(92) in path:
        errors.append('save path must use forward slashes')
    if '..' in path.split('/'):
        errors.append('save path escapes case root')
    if is_symlink and not policy.allow_symlink:
        errors.append('symlink save needs explicit opt-in')
    if exists and not policy.allow_overwrite:
        errors.append('refuse overwrite of existing case file')
    return tuple(errors)
def validate_directive(text):
    errors = []
    for directive in EXEC_DIRECTIVES:
        if directive in text:
            errors.append('executable directive ' + directive + ' is never evaluated in static lint')
    return tuple(errors)
def validate_argv(argv):
    errors = []
    if not argv:
        errors.append('empty argv')
        return tuple(errors)
    for pos, entry in enumerate(argv):
        if not entry:
            errors.append('empty argv entry at position ' + str(pos))
        elif chr(10) in entry:
            errors.append('rejected newline in argv entry at position ' + str(pos))
        else:
            for risky in SHELL_RISKY:
                if risky in entry:
                    errors.append('rejected shell metacharacter in argv entry at position ' + str(pos))
                    break
    return tuple(errors)
def is_untrusted_script(basename):
    return basename in UNTRUSTED_SCRIPTS
