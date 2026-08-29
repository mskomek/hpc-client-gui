"""Portable local and CI checks for HPC Client GUI."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _env(*, gui: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    if gui:
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["HPC_GUI_DISABLE_WEBENGINE"] = "1"
    return env


def _run(label: str, command: list[str], *, gui: bool = False) -> int:
    printable = " ".join(command)
    print(f"[ci] {label}: {printable}", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=_env(gui=gui))
    if result.returncode:
        print(f"[ci] FAILED ({result.returncode}): {label}", file=sys.stderr)
    return result.returncode


def _python(*args: str) -> list[str]:
    return [PYTHON, *args]


def quick() -> int:
    for label, command, gui in (
        ("compile", _python("-m", "compileall", "-q", "src/hpc_gui"), False),
        ("i18n", _python("scripts/check_i18n.py"), False),
        ("smoke", _python("scripts/smoke_test.py"), True),
        ("lint", _python("-m", "ruff", "check", "src", "scripts", "tests"), False),
    ):
        if _run(label, command, gui=gui):
            return 1
    return 0


def lint() -> int:
    return _run("ruff", _python("-m", "ruff", "check", "src", "scripts", "tests"))


def docs() -> int:
    for label, script in (
        ("branding", "scripts/check_branding.py"),
        ("release surface", "scripts/check_release_surface.py"),
    ):
        if _run(label, _python(script)):
            return 1
    wiki = ROOT / "docs" / "wiki"
    if wiki.is_dir() and _run("wiki", _python("scripts/check_wiki.py")):
        return 1
    if not wiki.is_dir():
        print("[ci] wiki: SKIPPED (docs/wiki is unavailable)")
    return 0


def gui() -> int:
    if _run("GUI tests and coverage", _python("scripts/release_test_suite.py", "--coverage"), gui=True):
        return 1
    return _run("module coverage", _python("scripts/check_module_coverage.py", "coverage.xml"))


def packaging() -> int:
    return _run(
        "wheel packaging",
        _python("-m", "pytest", "tests/test_wheel_packaging.py", "-m", "packaging", "-q"),
    )


def audit() -> int:
    return _run(
        "dependency audit",
        _python("-m", "pip_audit", "-r", "requirements-dev.txt", "--progress-spinner", "off"),
    )


def release() -> int:
    return _run("release preflight", _python("scripts/release_test_suite.py"), gui=True)


def _pytest(*paths: str) -> list[str]:
    return _python("-m", "pytest", *paths, "-q", "--tb=short", "-rf")


def compat() -> int:
    return _run(
        "compatibility tests",
        _pytest(
            "tests/test_cli.py",
            "tests/test_cli_entrypoint.py",
            "tests/test_config_storage_atomic.py",
            "tests/test_profile_identity.py",
            "tests/test_profile_transfer_settings.py",
            "tests/test_slurm_models.py",
            "tests/test_slurm_script_parser.py",
            "tests/test_remote_entry_helpers.py",
            "tests/test_upload_pipelining.py",
            "tests/test_version_consistency.py",
        ),
        gui=True,
    )


def cli() -> int:
    return _run("CLI tests", _pytest("tests/test_cli.py", "tests/test_cli_entrypoint.py"), gui=True)


def ssh() -> int:
    return _run(
        "SSH/SFTP tests",
        _pytest(
            "tests/test_optional_ssh_credentials.py",
            "tests/test_slurm_ssh.py",
            "tests/test_local_transfer_gate.py",
            "tests/test_transfer_wave17.py",
            "tests/test_transfer_controller.py",
            "tests/test_profile_transfer_settings.py",
        ),
        gui=True,
    )


def windows() -> int:
    if _run(
        "Windows boundary tests",
        _pytest("tests/test_safe_download.py", "tests/test_version_consistency.py", "tests/test_startup_changelog.py"),
        gui=True,
    ):
        return 1
    if _run("Windows terminal tests", _python("-m", "unittest", "discover", "-s", "tests", "-p", "test_terminal_*.py"), gui=True):
        return 1
    return _run("SSH terminal tests", _python("-m", "unittest", "discover", "-s", "tests", "-p", "test_ssh_terminal_stream.py"), gui=True)


def macos() -> int:
    return _run(
        "macOS boundary tests",
        _pytest(
            "tests/test_platform.py",
            "tests/test_paths.py",
            "tests/test_app_updater.py",
            "tests/test_secret_store.py",
            "tests/test_macos_product_surface.py",
            "tests/test_macos_x11.py",
            "tests/test_macos_release.py",
            "tests/test_macos_packaging_spec.py",
            "tests/test_version_consistency.py",
        ),
        gui=True,
    )


def contract() -> int:
    return _run("plugin contract", _pytest("tests/test_plugin_contract.py"), gui=True)


def full() -> int:
    for target in (gui, docs, packaging, audit):
        if target():
            return 1
    return 0


def pre_push() -> int:
    print(f"[ci] platform: {platform.system()} {platform.machine()}")
    return full()


TARGETS = {
    "quick": quick,
    "full": full,
    "gui": gui,
    "lint": lint,
    "docs": docs,
    "packaging": packaging,
    "audit": audit,
    "pre-push": pre_push,
    "release": release,
    "compat": compat,
    "cli": cli,
    "ssh": ssh,
    "windows": windows,
    "macos": macos,
    "contract": contract,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=sorted(TARGETS))
    args = parser.parse_args(argv)
    return TARGETS[args.target]()


if __name__ == "__main__":
    raise SystemExit(main())
