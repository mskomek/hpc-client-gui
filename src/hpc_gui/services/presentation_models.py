"""Toolkit-neutral presentation models and lifecycle-safe event delivery."""

from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class StatusViewModel:
    state: str
    label: str
    detail: str = ""


@dataclass(frozen=True)
class ListItemViewModel:
    id: str
    label: str
    detail: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class ProgressViewModel:
    current: int
    total: int
    label: str = ""


@dataclass(frozen=True)
class DialogRequest:
    kind: str
    title: str
    message: str
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class Notification:
    level: str
    message: str


class EventBus:
    """Publish events without retaining bound-method views after disposal."""

    def __init__(self) -> None:
        self._listeners: list[weakref.ReferenceType[Any]] = []

    def subscribe(self, callback: Callable[[Any], None]) -> Callable[[], None]:
        reference = weakref.WeakMethod(callback) if getattr(callback, "__self__", None) is not None else weakref.ref(callback)
        self._listeners.append(reference)

        def unsubscribe() -> None:
            self._listeners[:] = [item for item in self._listeners if item is not reference]

        return unsubscribe

    def publish(self, event: Any) -> None:
        alive = []
        for reference in self._listeners:
            callback = reference()
            if callback is not None:
                callback(event)
                alive.append(reference)
        self._listeners = alive


__all__ = [
    "DialogRequest", "EventBus", "ListItemViewModel", "Notification",
    "ProgressViewModel", "StatusViewModel",
]
