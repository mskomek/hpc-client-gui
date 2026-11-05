"""Shared subprocess helpers for wx terminal parity tests."""

import pathlib
import subprocess
import sys
import textwrap

from support.subprocess_environment import project_python_environment


REPO_ROOT = pathlib.Path(__file__).parents[2]


def _run(code, timeout=15):
    env = project_python_environment(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _wrap(code):
    return textwrap.dedent(code)
