"""PKG-GJ-01 fresh-user workflow for the packaged wx acceptance harness."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from wx_packaged_smoke_support import (
    ROOT,
    TEMP_ROOT,
    clean_room_dir,
    current_commit,
    format_artifact_identity,
    plugin_commit,
    run_child,
    sha256,
    start_loopback_ssh,
)

FRESH_RUN1_CHECKS = (
    "fresh_config_root", "first_run_empty_state", "profile_via_visible_controls",
    "loopback_success_via_controls", "safe_visible_failure", "persisted_nonsecret_state",
    "no_src_leakage", "clean_shutdown",
)
FRESH_RUN2_CHECKS = ("relaunch_state_present", "relaunch_no_src_leakage", "clean_shutdown")
FRESH_PROFILE_NAME = "fresh-user-loopback"
_FRESH_DEV_ONLY_VARS = ("PYTHONPATH", "HPC_GUI_DISABLE_WEBENGINE")


def fresh_user_env(base: dict, *, fresh_root: Path, run_index: int) -> dict:
    """Build the clean-room child environment for a PKG-GJ-01 run."""
    env = dict(base)
    for name in _FRESH_DEV_ONLY_VARS:
        env.pop(name, None)
    for name in ("TMP", "TEMP", "TMPDIR"):
        env[name] = str(TEMP_ROOT)
    env.update({"HPC_GUI_CONFIG_ROOT": str(fresh_root), "HPC_GUI_FRESH_USER": "1",
                "HPC_GUI_FRESH_RUN": str(run_index)})
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
    """Run first-launch and relaunch journeys against one exact artifact."""
    commit = current_commit() or "unknown"
    artifact_name = artifact.name if artifact else "missing"
    artifact_sha = sha256(artifact) if artifact and artifact.is_file() else "0" * 64
    checks = {name: "FAIL" for name in (*FRESH_RUN1_CHECKS, *FRESH_RUN2_CHECKS)}
    result, details, runs, exit_codes = "FAIL", {}, {}, []
    loopback_root = loopback_server = fresh_parent = runtime_webview = None
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = _fresh_launch_cmd(artifact)
        if not artifact.is_file():
            raise FileNotFoundError(f"artifact not found: {artifact}")
    except (ValueError, OSError) as exc:
        details["error"] = f"{type(exc).__name__}: {exc}"
    else:
        fresh_parent = clean_room_dir("hpc-fresh-user-")
        fresh_root, workdir = fresh_parent / "config", fresh_parent / "work"
        workdir.mkdir(parents=True, exist_ok=True)
        details.update({
            "fresh_root": str(fresh_root),
            "workdir": str(workdir),
            "workdir_outside_repo": False,
            "workdir_outside_source_tree": True,
            "workdir_under_temp_root": workdir.is_relative_to(ROOT / ".tmp"),
        })
        try:
            loopback_root, loopback_server, loopback_user, loopback_password = start_loopback_ssh(output)
            runtime_webview = Path(tempfile.mkdtemp(prefix="wx-webview-", dir=str(fresh_parent)))
            for run_index, expected in ((1, FRESH_RUN1_CHECKS), (2, FRESH_RUN2_CHECKS)):
                runtime_output = output.parent / f"{output.stem}.run{run_index}.runtime.json"
                runtime_output.unlink(missing_ok=True)
                env = fresh_user_env(os.environ, fresh_root=fresh_root, run_index=run_index)
                env.update({
                    "HPC_GUI_PACKAGED_SMOKE_OUTPUT": str(runtime_output.resolve()),
                    "HPC_GUI_PACKAGED_SMOKE_SSH_HOST": "127.0.0.1",
                    "HPC_GUI_PACKAGED_SMOKE_SSH_PORT": str(loopback_server.port),
                    "HPC_GUI_PACKAGED_SMOKE_SSH_USER": loopback_user,
                    "HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD": loopback_password,
                    "HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS": str(Path(loopback_root.name) / "known_hosts"),
                    "HPC_GUI_PACKAGED_SMOKE_APP_NAME": f"hpc-fresh-user-{run_index}-{os.getpid()}",
                    "WEBVIEW2_USER_DATA_FOLDER": str(runtime_webview.resolve()),
                })
                if "PYTHONPATH" in env:
                    raise RuntimeError("clean-room env leaked PYTHONPATH")
                returncode, stdout, stderr, timed_out = run_child(
                    cmd, cwd=str(workdir), env=env, timeout=timeout,
                )
                combined = stdout + stderr
                runtime = {}
                if runtime_output.is_file():
                    runtime = json.loads(runtime_output.read_text(encoding="utf-8"))
                if timed_out:
                    details[f"run{run_index}_timeout"] = f"artifact did not exit within {timeout}s"
                    details[f"run{run_index}_killed"] = True
                    details[f"run{run_index}_output_tail"] = combined[-2000:]
                    runs[f"run{run_index}"] = {"error": "timeout", "runtime": runtime,
                                               "output_tail": combined[-2000:]}
                    break

                exit_codes.append(returncode)
                runs[f"run{run_index}"] = {
                    "exit_code": returncode, "runtime": runtime, "output_tail": combined[-2000:],
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
                if str(ROOT / "src") in combined:
                    details["isolation"] = "artifact output referenced repo src path"
            isolated = "isolation" not in details
            result = "PASS" if all(value == "PASS" for value in checks.values()) and isolated else "FAIL"
        except Exception as exc:
            details["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if runtime_webview is not None:
                shutil.rmtree(runtime_webview, ignore_errors=True)
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
            if fresh_parent is not None:
                shutil.rmtree(fresh_parent, ignore_errors=True)
                details["fresh_parent_cleaned"] = not fresh_parent.exists()

    try:
        from hpc_gui import __version__ as app_version
    except Exception:
        app_version = "unknown"
    identity_header = format_artifact_identity(
        artifact=artifact_name, sha256=artifact_sha, main_sha=commit,
        plugin_sha=plugin_commit(), version=app_version,
        os_arch=f"{platform.system().lower()}/{platform.machine().lower()}",
    )
    evidence = {
        "schema": "wx-fresh-user-smoke/1", "procedure": "PKG-GJ-01",
        "identity_header": identity_header, "commit": commit, "platform": platform_name,
        "artifact": artifact_name, "artifact_sha256": artifact_sha, "result": result,
        "checks": checks, "details": details, "runs": runs, "exit_codes": exit_codes,
        "python": platform.python_version(), "platform_detail": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "isolated_from_src": "isolation" not in details,
        "manual_required": ["display", "cluster", "MFA", "X11", "DnD", "transfer-conflict"],
    }
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence
