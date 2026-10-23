"""Small predicates shared by pure declarative validators."""

from __future__ import annotations

from typing import Any


def is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
