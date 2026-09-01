"""Conservative edits for the initial Slurm ``#SBATCH`` directive block."""

from __future__ import annotations

import re
from collections.abc import Mapping


_SBATCH_RE = re.compile(r"^(?P<prefix>\s*#\s*@?SBATCH\s+)(?P<body>.*?)(?P<newline>\r?\n)?$", re.IGNORECASE)
_SHELL_START = re.compile(r"^\s*(?:#!|#)")
_FIELDS = {
    "array": ("--array", "-a"),
    "dependency": ("--dependency", "-d"),
    "account": ("--account", "-A"),
    "partition": ("--partition", "-p"),
    "walltime": ("--time", "-t"),
    "nodes": ("--nodes", "-N"),
    "ntasks": ("--ntasks", "-n"),
    "cpus_per_task": ("--cpus-per-task", "-c"),
    "memory": ("--mem",),
    "gres": ("--gres",),
    "constraint": ("--constraint",),
}
_ALIASES = {alias: field for field, aliases in _FIELDS.items() for alias in aliases}
_RESOURCE_FIELDS = frozenset({"nodes", "ntasks", "cpus_per_task", "memory", "gres", "constraint"})


def _field(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_")
    if name.strip() in _ALIASES:
        return _ALIASES[name.strip()]
    return {
        "time": "walltime",
        "cpus": "cpus_per_task",
        "cpuspertask": "cpus_per_task",
    }.get(normalized, normalized)


def _initial_lines(text: str) -> list[tuple[int, str, str, str] ]:
    """Return (index, prefix, body, newline) for directives before shell code."""
    result = []
    started = False
    for index, line in enumerate(text.splitlines(keepends=True)):
        match = _SBATCH_RE.match(line)
        if match and not started:
            result.append((index, match.group("prefix"), match.group("body").strip(), match.group("newline") or ""))
            continue
        content = line.rstrip("\r\n")
        if not content.strip() or _SHELL_START.match(content):
            continue
        started = True
    return result


def _option(body: str) -> tuple[str, str] | None:
    body = body.split("#", 1)[0].strip()
    if not body:
        return None
    if body.startswith("--"):
        key, separator, value = body.partition("=")
        if not separator:
            parts = body.split(None, 1)
            key, value = parts[0], parts[1] if len(parts) > 1 else ""
    elif body[:2] in _ALIASES and len(body) > 2 and body[2].isspace():
        key, value = body[:2], body[2:].strip()
    else:
        return None
    return _ALIASES.get(key), value.strip()


class SlurmDirectives:
    """Immutable-style editor; every edit returns a new script string."""

    def __init__(self, text: str):
        self.text = text

    def get(self, name: str):
        field = _field(name)
        values = {}
        for index, _prefix, body, _newline in _initial_lines(self.text):
            parsed = _option(body)
            if parsed and parsed[0]:
                values[parsed[0]] = parsed[1]
        if field == "resources":
            return {key: values[key] for key in sorted(_RESOURCE_FIELDS) if key in values}
        return values.get(field)

    def set(self, name: str, value) -> str:
        field = _field(name)
        if field == "resources":
            if not isinstance(value, Mapping):
                raise TypeError("resources must be a mapping")
            result = self.text
            for key, resource_value in value.items():
                result = SlurmDirectives(result).set(str(key), resource_value)
            return result
        if field not in _FIELDS:
            raise ValueError(f"unsupported Slurm directive: {name}")
        value = str(value).strip()
        lines = self.text.splitlines(keepends=True)
        matches = [entry for entry in _initial_lines(self.text) if _option(entry[2]) and _option(entry[2])[0] == field]
        if matches:
            target = matches[-1][0]
            newline = lines[target][-2:] if lines[target].endswith("\r\n") else ("\n" if lines[target].endswith("\n") else "")
            lines[target] = f"#SBATCH {_FIELDS[field][0]}={value}{newline}"
            for index, _prefix, _body, _newline in reversed(matches[:-1]):
                del lines[index]
            return "".join(lines)
        insertion = self._insertion_index(lines)
        newline = "\r\n" if "\r\n" in self.text else "\n"
        if insertion and not lines[insertion - 1].endswith(("\n", "\r")):
            lines[insertion - 1] += newline
        lines.insert(insertion, f"#SBATCH {_FIELDS[field][0]}={value}{newline}")
        return "".join(lines)

    def remove(self, name: str) -> str:
        field = _field(name)
        if field == "resources":
            fields = _RESOURCE_FIELDS
        elif field in _FIELDS:
            fields = {field}
        else:
            raise ValueError(f"unsupported Slurm directive: {name}")
        lines = self.text.splitlines(keepends=True)
        indexes = [entry[0] for entry in _initial_lines(self.text) if (_option(entry[2]) or (None,))[0] in fields]
        for index in reversed(indexes):
            del lines[index]
        return "".join(lines)

    @staticmethod
    def _insertion_index(lines: list[str]) -> int:
        index = 0
        while index < len(lines):
            content = lines[index].rstrip("\r\n")
            if not content.strip() or _SHELL_START.match(content) or _SBATCH_RE.match(lines[index]):
                index += 1
                continue
            break
        return index


def parse_slurm_directives(text: str) -> SlurmDirectives:
    return SlurmDirectives(text)


def get_directive(text: str, name: str):
    return SlurmDirectives(text).get(name)


def set_directive(text: str, name: str, value) -> str:
    return SlurmDirectives(text).set(name, value)


def remove_directive(text: str, name: str) -> str:
    return SlurmDirectives(text).remove(name)
