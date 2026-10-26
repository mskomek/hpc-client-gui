"""Context-scoped adapters for the legacy configuration facade."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Dict, Iterator


_LOAD_PROVIDER: ContextVar[Callable[[], Dict[str, Any]] | None] = ContextVar(
    "hpc_gui_settings_load_provider", default=None
)
_UPDATE_WRITER: ContextVar[
    Callable[[Dict[str, Any]], Dict[str, Any]] | None
] = ContextVar("hpc_gui_settings_update_writer", default=None)


@contextmanager
def bind_settings_facade(
    load_provider: Callable[[], Dict[str, Any]],
    update_writer: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Iterator[None]:
    """Bind facade hooks for one synchronous setting operation."""
    load_token = _LOAD_PROVIDER.set(load_provider)
    update_token = _UPDATE_WRITER.set(update_writer)
    try:
        yield
    finally:
        _UPDATE_WRITER.reset(update_token)
        _LOAD_PROVIDER.reset(load_token)


def load_settings(fallback: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Read through the facade when one is bound; otherwise use the leaf."""
    provider = _LOAD_PROVIDER.get()
    return provider() if provider is not None else fallback()


def update_settings(
    patch: Dict[str, Any],
    fallback: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    """Write through the facade when one is bound; otherwise use the leaf."""
    writer = _UPDATE_WRITER.get()
    return writer(patch) if writer is not None else fallback(patch)
