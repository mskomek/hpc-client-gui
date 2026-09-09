"""Framework-neutral parser registry for Wave 79.

Parsers are application-owned executable code. Provider/plugin configs select
parser IDs declaratively but cannot inject parser code.

Architecture:
    trusted backend adapter
        ↓
    RawCommandResult
        ├── Raw Viewer
        └── parser registry
               ↓
           parsed model
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParseError:
    """Typed parse error result — distinguishes failure modes for UI."""

    kind: str  # "backend_failure" | "parser_failure" | "unsupported" | "empty_data"
    message: str
    raw_source_id: str = ""
    detail: str = ""

    @property
    def is_terminal(self) -> bool:
        return self.kind in {"backend_failure", "unsupported"}


@dataclass(frozen=True)
class ParseResult:
    """Wrapper for parsed output with optional error."""

    data: Any = None
    error: ParseError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @classmethod
    def success(cls, data: Any) -> ParseResult:
        return cls(data=data)

    @classmethod
    def fail(cls, kind: str, message: str, raw_source_id: str = "", detail: str = "") -> ParseResult:
        return cls(error=ParseError(kind=kind, message=message, raw_source_id=raw_source_id, detail=detail))


# Type alias for parser functions: (raw_text, parser_config) -> parsed model
ParserFunc = Callable[[str, dict[str, Any] | None], Any]

# Registry of parser_id -> parser function
_REGISTRY: dict[str, ParserFunc] = {}
_BUILTINS_LOADED = False


def _ensure_builtin_parsers() -> None:
    """Load application-owned parsers before any public lookup."""
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    module = import_module("hpc_gui.services.parsers")
    register_builtins = getattr(module, "register_builtin_parsers", None)
    if callable(register_builtins):
        register_builtins()
    _BUILTINS_LOADED = True


def register_parser(parser_id: str, func: ParserFunc) -> None:
    """Register a parser function under a stable ID."""
    if not isinstance(parser_id, str) or not parser_id.strip():
        raise ValueError("parser_id must be a non-empty string")
    if not callable(func):
        raise TypeError("func must be callable")
    _REGISTRY[parser_id] = func


def get_parser(parser_id: str) -> ParserFunc | None:
    """Look up a registered parser by ID. Returns None if unknown."""
    _ensure_builtin_parsers()
    return _REGISTRY.get(parser_id)


def parse(
    parser_id: str,
    raw_text: str,
    parser_config: dict[str, Any] | None = None,
    *,
    raw_source_id: str = "",
) -> ParseResult:
    """Execute a registered parser with error handling.

    Unknown parser IDs fail closed (ParseError kind='unsupported').
    Parser exceptions become typed ParseErrors (kind='parser_failure').
    Raw text is never destroyed — errors carry the source ID for raw fallback.
    """
    _ensure_builtin_parsers()
    func = _REGISTRY.get(parser_id)
    if func is None:
        return ParseResult.fail("unsupported", f"Unknown parser: {parser_id}", raw_source_id=raw_source_id)
    try:
        result = func(raw_text, parser_config)
        return ParseResult.success(result)
    except Exception as exc:
        log.warning("Parser %s failed: %s", parser_id, exc, exc_info=True)
        return ParseResult.fail(
            "parser_failure",
            "Parser could not understand the response",
            raw_source_id=raw_source_id,
            detail=str(exc),
        )


def known_parser_ids() -> frozenset[str]:
    """Return all registered parser IDs (for testing/introspection)."""
    _ensure_builtin_parsers()
    return frozenset(_REGISTRY.keys())


def clear_registry() -> None:
    """Reset registry — for testing only."""
    global _BUILTINS_LOADED
    _REGISTRY.clear()
    _BUILTINS_LOADED = False
