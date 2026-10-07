"""Shared process, identity, fixture and temp-root helpers for wx smoke lanes."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / ".tmp"

try:
    from artifact_identity import format_artifact_identity
except ImportError:  # pragma: no cover - evidence must survive a missing helper
    def format_artifact_identity(artifact, sha256, main_sha, plugin_sha, version, os_arch):
        return (
            f"Artifact: {artifact}\nSHA256: {sha256}\nMain SHA: {main_sha}\n"
            f"Plugin SHA: {plugin_sha}\nVersion: {version}\nOS/arch: {os_arch}"
        )


def clean_room_dir(prefix: str) -> Path:
    """Create disposable smoke state under the repository's enforced .tmp root."""
    base = TEMP_ROOT / "wx-packaged-clean-room"
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(base)))


def outside_repo(path: Path) -> bool:
    """Return whether a path is lexically outside the checkout."""
    root = Path(os.path.normcase(os.path.abspath(ROOT)))
    candidate = Path(os.path.normcase(os.path.abspath(path)))
    return not candidate.is_relative_to(root)


def outside_source_tree(path: Path) -> bool:
    """A .tmp clean-room path is allowed inside the checkout, but outside src."""
    source = Path(os.path.normcase(os.path.abspath(ROOT / "src")))
    candidate = Path(os.path.normcase(os.path.abspath(path)))
    return not candidate.is_relative_to(source)


def start_loopback_ssh(output: Path | None = None):
    """Start the disposable SSH/SFTP fixture with all fixture bytes under .tmp."""
    del output  # outputs are evidence; temporary server state always belongs to .tmp
    support_root = ROOT / "tests"
    if str(support_root) not in sys.path:
        sys.path.insert(0, str(support_root))
    from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer

    fixture_root = TEMP_ROOT / "wx-packaged-ssh"
    fixture_root.mkdir(parents=True, exist_ok=True)
    root = tempfile.TemporaryDirectory(
        prefix="wx-packaged-ssh-",
        dir=str(fixture_root),
        ignore_cleanup_errors=True,
    )
    server = MockSSHServer(Path(root.name))
    server.__enter__()
    return root, server, MOCK_USERNAME, MOCK_PASSWORD


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, check=False, timeout=10,
        )
    except Exception:
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else None


def plugin_commit() -> str:
    sibling = ROOT.parent / "hpc-client-gui-plugins"
    if not (sibling / ".git").is_dir():
        return "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=sibling, capture_output=True,
            text=True, check=False, timeout=10,
        )
    except Exception:
        return "unknown"
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else "unknown"


def run_child(cmd: list, *, cwd: str, env: dict, timeout: int):
    """Run a packaged GUI child and reap it when the acceptance deadline expires."""
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout or "", stderr or "", False
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except Exception:
            stdout, stderr = "", ""
        return proc.returncode, stdout or "", stderr or "", True
