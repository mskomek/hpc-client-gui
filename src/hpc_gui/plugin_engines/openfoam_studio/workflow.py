"""Validated, draft-only command sequencing for the Visual Flow."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


class WorkflowPlan:
    """A small workflow model that accepts only catalogued draft commands."""

    def __init__(self, commands: Iterable[Mapping[str, object]]):
        self._commands: dict[str, dict[str, object]] = {}
        for item in commands:
            name = item.get("name")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
                raise ValueError("workflow catalog contains an unsafe command name")
            if item.get("execution") != "draft-only":
                raise ValueError("workflow catalog may not execute commands")
            if name in self._commands:
                raise ValueError(f"workflow catalog has duplicate command {name!r}")
            self._commands[name] = dict(item)
        self._steps: list[str] = []

    @property
    def steps(self) -> tuple[str, ...]:
        return tuple(self._steps)

    def add(self, name: str, index: int | None = None) -> int:
        if name not in self._commands:
            raise ValueError("workflow step is not in the approved command catalog")
        insertion = len(self._steps) if index is None else index
        if not isinstance(insertion, int) or not 0 <= insertion <= len(self._steps):
            raise IndexError("workflow insertion position is out of range")
        self._steps.insert(insertion, name)
        return insertion

    def remove(self, index: int) -> str:
        self._check_index(index)
        return self._steps.pop(index)

    def move(self, index: int, offset: int) -> int | None:
        self._check_index(index)
        if offset not in (-1, 1):
            raise ValueError("workflow steps move one position at a time")
        target = index + offset
        if not 0 <= target < len(self._steps):
            return None
        step = self._steps.pop(index)
        self._steps.insert(target, step)
        return target

    def labels(self) -> tuple[str, ...]:
        return tuple(
            f"{index + 1}. {name}  —  {self._commands[name]['verification_status']}"
            for index, name in enumerate(self._steps)
        )

    def command(self, name: str) -> Mapping[str, object]:
        try:
            return dict(self._commands[name])
        except KeyError as exc:
            raise ValueError("workflow step is not in the approved command catalog") from exc

    def _check_index(self, index: int) -> None:
        if not isinstance(index, int) or not 0 <= index < len(self._steps):
            raise IndexError("workflow step position is out of range")
