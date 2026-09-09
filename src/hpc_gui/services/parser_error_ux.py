"""Parser error UX contract for Wave 79.

Distinguishes error kinds for UI display:
    - backend_failure: command execution failed
    - parser_failure: parser could not understand the response
    - unsupported: capability not configured
    - empty_data: no data available
"""

from __future__ import annotations

from hpc_gui.services.parser_registry import ParseError, ParseResult


def format_error_for_user(error: ParseError) -> str:
    """Format a ParseError into a user-facing message."""
    if error.kind == "backend_failure":
        return f"Command failed: {error.message}"
    elif error.kind == "parser_failure":
        return "Parser could not understand the response"
    elif error.kind == "unsupported":
        return "Provider does not support this capability"
    elif error.kind == "empty_data":
        return "No data available"
    else:
        return error.message or "Unknown error"


def format_error_with_raw_hint(error: ParseError) -> str:
    """Format error with hint that raw data is still available."""
    base = format_error_for_user(error)
    return f"{base}\nThe raw scheduler response is still available."


def is_backend_error(result: ParseResult) -> bool:
    """Check if a ParseResult represents a backend/command failure."""
    return result.error is not None and result.error.kind == "backend_failure"


def is_parser_error(result: ParseResult) -> bool:
    """Check if a ParseResult represents a parser failure."""
    return result.error is not None and result.error.kind == "parser_failure"


def is_unsupported(result: ParseResult) -> bool:
    """Check if a ParseResult represents an unsupported capability."""
    return result.error is not None and result.error.kind == "unsupported"
