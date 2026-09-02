"""Read the maintained pointer contract as structured help data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GestureHelpRow:
    id: str
    surface: str
    gesture: str
    behavior: str


_ROW = re.compile(r"^\| (GUI-[A-Z]+-\d{3}) \| (.*?) \| (.*?) \| (.*?) \|$")


def load_gesture_help(contract: Path | None = None) -> tuple[GestureHelpRow, ...]:
    path = contract or Path(__file__).parents[3] / "docs" / "v2" / "GUI_POINTER_INTERACTION_CONTRACT.md"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if match:
            rows.append(GestureHelpRow(*match.groups()))
    return tuple(rows)
