"""Shared CLI exit-code and error-emission contract for the TRUBAGUI CLI surface."""

from __future__ import annotations

import json
import sys
from enum import IntEnum


class ExitCode(IntEnum):
    """Named exit codes shared across the whole TRUBAGUI CLI surface.

    The numeric values are part of the public contract; see ``docs/cli/exit_codes.md``.
    """

    SUCCESS = 0
    OPERATION_FAILED = 1
    USAGE = 2
    CONNECTION = 3
    TIMEOUT = 124


def emit_error(message: str, *, exit_code: ExitCode, output_format: str = "text") -> None:
    """Print an actionable failure to ``sys.stderr`` (text) or as JSON on ``sys.stdout``.

    Text mode keeps the human-readable detail on stderr. JSON mode emits a
    single parseable object on stdout so callers can consume failures; the
    detail is carried in the ``message`` field and is not duplicated on stderr.
    """
    if output_format == "json":
        payload = {"error": {"message": message, "exit_code": int(exit_code)}}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stdout)
        return
    print(message, file=sys.stderr)
