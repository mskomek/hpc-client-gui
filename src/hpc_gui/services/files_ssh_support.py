"""Remote error translation helpers shared by the SSH files backend.

Used by both files_ssh.py and the SSHTextMixin in files_ssh_text.py.
"""
from __future__ import annotations
import contextlib
import errno
import re

@contextlib.contextmanager
def _translate_remote_errors(remote_path: str):
    """Re-raise a typed FileNotFoundError/PermissionError with `remote_path`
    attached as `.filename`, so callers always get a path-bearing message
    instead of paramiko's bare `[Errno N] ...` text."""
    try:
        yield
    except (FileNotFoundError, PermissionError) as exc:
        raise type(exc)(exc.errno, exc.strerror or str(exc), remote_path) from exc


_QUOTED_PATH_RE = re.compile(r"'([^']+)'")


def _raise_on_failed_run(code: int, err: str, operation: str, path: str | None = None) -> None:
    """Translate a remote shell result into a typed failure.

    A socket timeout in ``SSHClientWrapper.run`` surfaces as exit code 124;
    surface that as ``TimeoutError`` so the CLI can route it to ``TIMEOUT``.

    When `path` is given, classify a non-zero, non-timeout failure as
    ``FileNotFoundError``/``PermissionError`` by matching well-known GNU
    coreutils stderr wording, attaching whichever path the stderr text
    quotes (falling back to `path` itself when the text quotes nothing) as
    ``.filename`` so the CLI can render a path-bearing message. Omitting
    `path` preserves today's plain ``RuntimeError`` behavior exactly.
    """
    if code == 124:
        raise TimeoutError(f"{operation} timed out")
    if code == 0:
        return
    text = err.strip() or f"{operation} failed (exit={code})"
    if path is not None:
        lowered = text.lower()
        match = _QUOTED_PATH_RE.search(text)
        reported_path = match.group(1) if match else path
        if "no such file or directory" in lowered:
            raise FileNotFoundError(errno.ENOENT, text, reported_path)
        if "permission denied" in lowered:
            raise PermissionError(errno.EACCES, text, reported_path)
    raise RuntimeError(text)


