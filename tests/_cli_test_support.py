from __future__ import annotations

import argparse
import errno
import hashlib
import json
import socket
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hpc_gui.cli.errors import ExitCode
from hpc_gui.cli.main import _run_doctor, run_cli
from hpc_gui.cli.session import CLIConnectionError, CLISession
from hpc_gui.services.connection_diagnostics import run_connection_diagnostics
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.sftp_smoke import STAGES as SMOKE_STAGES
from hpc_gui.services.sftp_smoke import run_sftp_smoke
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo


@pytest.fixture(autouse=True)
def _remote_cli_access_enabled():
    """Let pre-existing remote-command tests run without tripping the gate.

    The production default for ``cli_external_access_enabled`` is off; every
    legacy test below exercises a remote-session command (``files``, ``jobs``,
    ``profile test``, ``doctor connection``/``smoke``) and predates the access
    gate.  Enabling the toggle here keeps those tests focused on their own
    behaviour.  The access-gate tests explicitly re-patch the getter to
    ``False`` to exercise the real off-by-default behaviour.
    """
    with patch("hpc_gui.cli.main.get_cli_external_access_enabled", return_value=True):
        yield


@pytest.fixture(autouse=True)
def _isolated_cli_config(tmp_path):
    """Keep CLI tests hermetic from the developer machine's real config.

    Profile-derived system settings must never leak a saved default profile
    into exact-command assertions. Each test gets its own empty config.json;
    tests that patch ``_config_path`` or ``load_profiles`` themselves are
    unaffected.
    """
    with patch(
        "hpc_gui.config._storage_core._config_path",
        return_value=tmp_path / "config.json",
    ):
        yield

__all__ = [
    "argparse", "errno", "hashlib", "json", "socket", "Path",
    "SimpleNamespace", "MagicMock", "patch", "pytest", "ExitCode",
    "_run_doctor", "run_cli", "CLIConnectionError", "CLISession",
    "run_connection_diagnostics", "RemoteEntry", "SSHFilesBackend", "SMOKE_STAGES",
    "run_sftp_smoke", "SSHClientWrapper", "SSHConnInfo",
    "_remote_cli_access_enabled", "_isolated_cli_config",
]
