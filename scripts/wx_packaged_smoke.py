"""Real packaged wx artifact smoke (requires built artifact, isolates src)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from artifact_identity import format_artifact_identity
except ImportError:  # pragma: no cover - evidence must never fail on helper import
    def format_artifact_identity(artifact, sha256, main_sha, plugin_sha, version, os_arch):
        return (
            f"Artifact: {artifact}\nSHA256: {sha256}\nMain SHA: {main_sha}\n"
            f"Plugin SHA: {plugin_sha}\nVersion: {version}\nOS/arch: {os_arch}"
        )

# Expected checks per gate spec
REQUIRED_CHECKS = (
    "process_started",
    "wx_runtime_started",
    "main_frame_created",
    "settings_opened",
    "terminal_readback",
    "pty_input_output",
    "pty_resize",
    "remote_file_roundtrip",
    "job_roundtrip",
    "files_surface",
    "editor_surface",
    "jobs_surface",
    "plugin_ansys_surface",
    "diagnostics_updater_surface",
    "files_controls",
    "editor_controls",
    "jobs_controls",
    "editor_roundtrip",
    "transfer_queue_render",
    "clean_shutdown",
)


def _start_loopback_ssh(output: Path):
    """Start the existing disposable SSH/SFTP fixture for the packaged app."""
    import sys as _sys

    support_root = ROOT / "tests"
    if str(support_root) not in _sys.path:
        _sys.path.insert(0, str(support_root))
    from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer

    root = tempfile.TemporaryDirectory(
        prefix="wx-packaged-ssh-",
        dir=str(output.parent),
        ignore_cleanup_errors=True,
    )
    server = MockSSHServer(Path(root.name))
    server.__enter__()
    return root, server, MOCK_USERNAME, MOCK_PASSWORD


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def current_commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)
    except Exception:
        return None
    v = r.stdout.strip()
    return v if r.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", v) else None


def _plugin_commit() -> str:
    sibling = ROOT.parent / "hpc-client-gui-plugins"
    if not (sibling / ".git").is_dir():
        return "unknown"
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=sibling, capture_output=True, text=True, check=False, timeout=10)
    except Exception:
        return "unknown"
    v = r.stdout.strip()
    return v if r.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", v) else "unknown"


def _run_child(cmd: list, *, cwd: str, env: dict, timeout: int):
    """Run a packaged GUI child; kill it on timeout so no orphan GUI lingers.

    Returns (returncode, stdout, stderr, timed_out). A timed-out child is
    killed and reaped before returning so solo-run sequencing stays clean.
    """
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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


def run_packaged_smoke(artifact: Path, platform_name: str, output: Path, timeout: int = 25) -> dict:
    commit = current_commit() or "unknown"
    artifact_name = artifact.name if artifact else "missing"
    artifact_sha = _sha256(artifact) if artifact and artifact.is_file() else "0" * 64
    checks = {name: "FAIL" for name in REQUIRED_CHECKS}
    result = "FAIL"
    details: dict[str, object] = {}
    exit_code = None
    loopback_root = None
    loopback_server = None
    output.parent.mkdir(parents=True, exist_ok=True)

    if not artifact or not artifact.is_file():
        details["artifact"] = f"artifact not found: {artifact}"
        checks = {k: "FAIL" for k in REQUIRED_CHECKS}
        result = "FAIL"
    else:
        # The artifact owns the runtime probe.  No source import or --help heuristic counts as evidence.
        env = {k: v for k, v in os.environ.items()}
        env.pop("PYTHONPATH", None)
        runtime_output = output.with_suffix(".runtime.json")
        runtime_output.unlink(missing_ok=True)
        runtime_webview_path = Path(tempfile.mkdtemp(prefix="wx-webview-", dir=str(output.parent)))
        try:
            loopback_root, loopback_server, loopback_user, loopback_password = _start_loopback_ssh(output)
            if artifact.suffix == ".py":
                cmd = [sys.executable, str(artifact), "--wx-smoke"]
            elif artifact.suffix == ".exe":
                cmd = [str(artifact), "--wx-smoke"]
            else:
                raise ValueError(f"unsupported artifact type: {artifact.suffix}")
            env["HPC_GUI_PACKAGED_SMOKE_OUTPUT"] = str(runtime_output.resolve())
            env["HPC_GUI_PACKAGED_SMOKE_SSH_HOST"] = "127.0.0.1"
            env["HPC_GUI_PACKAGED_SMOKE_SSH_PORT"] = str(loopback_server.port)
            env["HPC_GUI_PACKAGED_SMOKE_SSH_USER"] = loopback_user
            env["HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD"] = loopback_password
            env["HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS"] = str(Path(loopback_root.name) / "known_hosts")
            env["HPC_GUI_PACKAGED_SMOKE_APP_NAME"] = f"hpc-client-gui-smoke-{os.getpid()}"
            # wxPython's Edge backend honors the folder variable directly;
            # keep the browser-argument fallback for older WebView2 builds.
            env["WEBVIEW2_USER_DATA_FOLDER"] = str(runtime_webview_path.resolve())
            browser_args = env.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "").strip()
            env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
                f"{browser_args} --disable-gpu --user-data-dir={runtime_webview_path.resolve()}"
            ).strip()
            checks["process_started"] = "PASS"
            # Clean-room cwd: the packaged child must not run with the source
            # checkout as its working directory (HPC-W04-HARNESS-025). System
            # temp is outside the repo by construction.
            workdir = Path(tempfile.mkdtemp(prefix="wx-packaged-cwd-"))
            details["workdir_outside_repo"] = str(ROOT) not in str(workdir.resolve())
            returncode, child_stdout, child_stderr, timed_out = _run_child(
                cmd,
                cwd=str(workdir),
                env={**env, "PYTHONPATH": ""},
                timeout=timeout,
            )
            shutil.rmtree(workdir, ignore_errors=True)
            combined = ""
            if timed_out:
                details["timeout"] = f"artifact did not exit within {timeout}s"
                details["child_killed"] = True
            else:
                combined = (child_stdout or "") + (child_stderr or "")
                exit_code = returncode
                runtime = json.loads(runtime_output.read_text(encoding="utf-8")) if runtime_output.is_file() else {}
                runtime_checks = runtime.get("checks", {}) if isinstance(runtime, dict) else {}
                if isinstance(runtime, dict):
                    for key in ("wx_app_name", "wx_local_data_dir"):
                        if runtime.get(key):
                            details[key] = str(runtime[key])
                    for key in ("phase", "input_diagnostic", "last_line", "last_buffer", "last_screen"):
                        if key in runtime:
                            details[f"runtime_{key}"] = runtime[key]
                for name in REQUIRED_CHECKS:
                    if name in ("process_started", "clean_shutdown", "pty_resize"):
                        continue
                    if runtime_checks.get(name) == "PASS":
                        checks[name] = "PASS"
                # The packaged process can prove that it requested a resize, but
                # only the disposable server can prove the resize reached the wire.
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline:
                    if any(size[0:2] == (123, 45) for size in loopback_server.resize_sizes):
                        break
                    time.sleep(0.02)
                if any(size[0:2] == (96, 31) for size in loopback_server.pty_sizes) and any(
                    size[0:2] == (123, 45) for size in loopback_server.resize_sizes
                ):
                    checks["pty_resize"] = "PASS"
                else:
                    details["pty_resize"] = {
                        "pty_sizes": loopback_server.pty_sizes,
                        "resize_sizes": loopback_server.resize_sizes,
                    }.__repr__()
                if not runtime_output.is_file():
                    details["runtime"] = "artifact exited without packaged runtime evidence"
                elif runtime.get("error"):
                    details["runtime"] = str(runtime["error"])
                src_path = str(ROOT / "src")
                isolated = src_path not in combined
                if not isolated:
                    details["isolation"] = "artifact output referenced repo src path"
                if returncode != 0:
                    details["exit_code"] = f"artifact exit {returncode}"
                checks["clean_shutdown"] = "PASS" if returncode == 0 and isolated and runtime.get("result") == "PASS" else "FAIL"
            result = "FAIL" if timed_out else ("PASS" if all(value == "PASS" for value in checks.values()) else "FAIL")
            if result == "FAIL" and combined:
                details["output_snippet"] = combined[:2000]
        except Exception as exc:
            details["error"] = f"{type(exc).__name__}: {exc}"
            result = "FAIL"
        finally:
            # The raw in-app runtime payload is evidence: preserve it next to
            # the parent report (same convention as the fresh-user runner).
            shutil.rmtree(runtime_webview_path, ignore_errors=True)
            if loopback_server is not None:
                try:
                    loopback_server.__exit__(None, None, None)
                except Exception:
                    pass
            if loopback_root is not None:
                try:
                    loopback_root.cleanup()
                except OSError:
                    # Paramiko's disposable handler can outlive the client by
                    # a few milliseconds on Windows; preserve the evidence.
                    pass

    # Build evidence JSON per spec
    try:
        from hpc_gui import __version__ as _app_version
    except Exception:
        _app_version = "unknown"
    identity_header = format_artifact_identity(
        artifact=artifact_name,
        sha256=artifact_sha,
        main_sha=commit,
        plugin_sha=_plugin_commit(),
        version=_app_version,
        os_arch=f"{platform.system().lower()}/{platform.machine().lower()}",
    )
    evidence = {
        "schema": "wx-packaged-smoke/1",
        "identity_header": identity_header,
        "commit": commit,
        "platform": platform_name,
        "artifact": artifact_name,
        "artifact_sha256": artifact_sha,
        "result": result,
        "checks": checks,
        "details": details,
        "python": platform.python_version(),
        "platform_detail": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "isolated_from_src": "isolation" not in details,
        "manual_required": ["display", "cluster", "MFA", "X11", "DnD", "transfer-conflict"],
    }
    # Write to build/audit location expected by gate
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


# PKG-GJ-01 — Fresh-user packaged startup contract (W15).
#
# Procedure: isolated clean config root -> launch GUI artifact outside the
# repo with a clean-room env -> first-run empty state -> profile creation
# through visible controls -> loopback success + safe visible failure ->
# close -> relaunch with persisted non-secret state -> src-leakage assertion.
# A wheel can never satisfy this: it is not launchable GUI evidence.
FRESH_RUN1_CHECKS = (
    "fresh_config_root",
    "first_run_empty_state",
    "profile_via_visible_controls",
    "loopback_success_via_controls",
    "safe_visible_failure",
    "persisted_nonsecret_state",
    "no_src_leakage",
    "clean_shutdown",
)
FRESH_RUN2_CHECKS = (
    "relaunch_state_present",
    "relaunch_no_src_leakage",
    "clean_shutdown",
)
FRESH_PROFILE_NAME = "fresh-user-loopback"

#: Developer-only variables that must never leak into the packaged child env.
_FRESH_DEV_ONLY_VARS = ("PYTHONPATH", "HPC_GUI_DISABLE_WEBENGINE")


def fresh_user_env(base: dict, *, fresh_root: Path, run_index: int) -> dict:
    """Build the clean-room child environment for a PKG-GJ-01 run."""
    env = {k: v for k, v in base.items()}
    for name in _FRESH_DEV_ONLY_VARS:
        env.pop(name, None)
    env["HPC_GUI_CONFIG_ROOT"] = str(fresh_root)
    env["HPC_GUI_FRESH_USER"] = "1"
    env["HPC_GUI_FRESH_RUN"] = str(run_index)
    return env


def _fresh_launch_cmd(artifact: Path) -> list:
    if artifact.suffix == ".py":
        return [sys.executable, str(artifact), "--wx-smoke"]
    if artifact.suffix == ".exe":
        return [str(artifact), "--wx-smoke"]
    raise ValueError(
        f"fresh-user packaged startup requires a GUI-capable artifact (.py/.exe), "
        f"got {artifact.suffix or 'unknown'}: a wheel is never GUI evidence"
    )


def run_fresh_user_smoke(artifact: Path, platform_name: str, output: Path, timeout: int = 240) -> dict:
    """Execute PKG-GJ-01 against the exact artifact; bind evidence to its SHA."""
    commit = current_commit() or "unknown"
    artifact_name = artifact.name if artifact else "missing"
    artifact_sha = _sha256(artifact) if artifact and artifact.is_file() else "0" * 64
    checks = {name: "FAIL" for name in (*FRESH_RUN1_CHECKS, *FRESH_RUN2_CHECKS)}
    result = "FAIL"
    details: dict[str, object] = {}
    runs: dict[str, object] = {}
    exit_codes: list = []
    loopback_root = None
    loopback_server = None
    fresh_parent = None
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = _fresh_launch_cmd(artifact)
    except ValueError as exc:
        details["error"] = str(exc)
    else:
        if not artifact.is_file():
            details["error"] = f"artifact not found: {artifact}"
        else:
            fresh_parent = Path(tempfile.mkdtemp(prefix="hpc-fresh-user-"))
            fresh_root = fresh_parent / "config"
            workdir = fresh_parent / "work"
            workdir.mkdir(parents=True, exist_ok=True)
            if (fresh_root / "config.json").exists():
                details["error"] = "fresh root is not clean: config.json pre-exists"
            else:
                details["fresh_root"] = str(fresh_root)
                details["workdir"] = str(workdir)
                details["workdir_outside_repo"] = str(ROOT) not in str(workdir.resolve())
                try:
                    loopback_root, loopback_server, loopback_user, loopback_password = _start_loopback_ssh(output)
                    runtime_webview = Path(tempfile.mkdtemp(prefix="wx-webview-", dir=str(fresh_parent)))
                    for run_index, expected in ((1, FRESH_RUN1_CHECKS), (2, FRESH_RUN2_CHECKS)):
                        runtime_output = output.parent / f"{output.stem}.run{run_index}.runtime.json"
                        runtime_output.unlink(missing_ok=True)
                        env = fresh_user_env(os.environ, fresh_root=fresh_root, run_index=run_index)
                        env["HPC_GUI_PACKAGED_SMOKE_OUTPUT"] = str(runtime_output.resolve())
                        env["HPC_GUI_PACKAGED_SMOKE_SSH_HOST"] = "127.0.0.1"
                        env["HPC_GUI_PACKAGED_SMOKE_SSH_PORT"] = str(loopback_server.port)
                        env["HPC_GUI_PACKAGED_SMOKE_SSH_USER"] = loopback_user
                        env["HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD"] = loopback_password
                        env["HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS"] = str(Path(loopback_root.name) / "known_hosts")
                        env["HPC_GUI_PACKAGED_SMOKE_APP_NAME"] = f"hpc-fresh-user-{run_index}-{os.getpid()}"
                        env["WEBVIEW2_USER_DATA_FOLDER"] = str(runtime_webview.resolve())
                        assert "PYTHONPATH" not in env, "clean-room env leaked PYTHONPATH"
                        returncode, child_stdout, child_stderr, timed_out = _run_child(
                            cmd, cwd=str(workdir), env=env, timeout=timeout,
                        )
                        if timed_out:
                            details[f"run{run_index}_timeout"] = f"artifact did not exit within {timeout}s"
                            details[f"run{run_index}_killed"] = True
                            runs[f"run{run_index}"] = {"error": "timeout"}
                            break
                        exit_codes.append(returncode)
                        combined = (child_stdout or "") + (child_stderr or "")
                        runtime = json.loads(runtime_output.read_text(encoding="utf-8")) if runtime_output.is_file() else {}
                        runs[f"run{run_index}"] = {
                            "exit_code": returncode,
                            "runtime": runtime,
                            "output_tail": combined[-2000:],
                        }
                        if returncode != 0:
                            details[f"run{run_index}_exit"] = f"artifact exit {returncode}"
                            details[f"run{run_index}_output"] = combined[:2000]
                        runtime_checks = runtime.get("checks", {}) if isinstance(runtime, dict) else {}
                        for name in expected:
                            if runtime_checks.get(name) == "PASS":
                                checks[name] = "PASS"
                        if not runtime_output.is_file():
                            details[f"run{run_index}_runtime"] = "artifact exited without fresh-user runtime evidence"
                        elif runtime.get("error"):
                            details[f"run{run_index}_runtime"] = str(runtime["error"])
                        src_path = str(ROOT / "src")
                        if src_path in combined:
                            details["isolation"] = "artifact output referenced repo src path"
                    if not details.get("error"):
                        isolated = "isolation" not in details
                        result = "PASS" if all(v == "PASS" for v in checks.values()) and isolated else "FAIL"
                except Exception as exc:
                    details["error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    shutil.rmtree(runtime_webview, ignore_errors=True) if "runtime_webview" in locals() else None
                    if loopback_server is not None:
                        try:
                            loopback_server.__exit__(None, None, None)
                        except Exception:
                            pass
                    if loopback_root is not None:
                        try:
                            loopback_root.cleanup()
                        except OSError:
                            pass
                    details["fresh_parent_kept"] = str(fresh_parent) if fresh_parent else None

    try:
        from hpc_gui import __version__ as _app_version
    except Exception:
        _app_version = "unknown"
    identity_header = format_artifact_identity(
        artifact=artifact_name,
        sha256=artifact_sha,
        main_sha=commit,
        plugin_sha=_plugin_commit(),
        version=_app_version,
        os_arch=f"{platform.system().lower()}/{platform.machine().lower()}",
    )
    evidence = {
        "schema": "wx-fresh-user-smoke/1",
        "procedure": "PKG-GJ-01",
        "identity_header": identity_header,
        "commit": commit,
        "platform": platform_name,
        "artifact": artifact_name,
        "artifact_sha256": artifact_sha,
        "result": result,
        "checks": checks,
        "details": details,
        "runs": runs,
        "exit_codes": exit_codes,
        "python": platform.python_version(),
        "platform_detail": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "isolated_from_src": "isolation" not in details,
        "manual_required": ["display", "cluster", "MFA", "X11", "DnD", "transfer-conflict"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Real packaged wx smoke (isolated from src)")
    parser.add_argument("--artifact", type=Path, default=None, help="Path to built wx artifact (exe, whl, or py)")
    parser.add_argument("--platform", default=None, help="Platform label (windows|linux|macos)")
    parser.add_argument("--output", type=Path, default=None, help="Output evidence JSON path")
    parser.add_argument("--fresh-user", action="store_true",
                        help="Run PKG-GJ-01 fresh-user acceptance (isolated config root, first-run, relaunch)")
    args = parser.parse_args()

    # Default platform inference
    plat = args.platform
    if not plat:
        sys_plat = platform.system().lower()
        if sys_plat == "windows":
            plat = "windows"
        elif sys_plat == "darwin":
            plat = "macos"
        else:
            plat = "linux"

    # Default artifact discovery: try build/audit artifacts or dist
    artifact = args.artifact
    if not artifact:
        candidates = [
            ROOT / "dist" / "hpc-client-gui" / "hpc-client-gui.exe",
            ROOT / "dist" / "hpc-client-gui-wx.exe",
            ROOT / "build" / "wx-artifact" / f"hpc-client-gui-wx-{plat}",
            ROOT / "build" / "audit" / f"wx-artifact-{plat}.exe",
        ]
        for c in candidates:
            if c.is_file():
                artifact = c
                break
        if not artifact:
            artifact = ROOT / f"build/audit/wx-artifact-{plat}.missing"

    output = args.output or (ROOT / f"build/audit/wx-packaged-smoke-{plat}.json")

    if args.fresh_user:
        evidence = run_fresh_user_smoke(artifact, plat, output)
    else:
        evidence = run_packaged_smoke(artifact, plat, output)
    # Machine-readable contract: stdout carries exactly the evidence JSON so
    # `json.loads(stdout)` succeeds; the human identity header goes to stderr.
    print(evidence.get("identity_header", ""), file=sys.stderr)
    print("---", file=sys.stderr)
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
