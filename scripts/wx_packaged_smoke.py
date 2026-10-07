"""Real packaged wx artifact smoke (requires built artifact, isolates src)."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from wx_packaged_smoke_support import (
    ROOT,
    TEMP_ROOT,
    clean_room_dir as _clean_room_dir,
    current_commit,
    format_artifact_identity,
    outside_repo as _outside_repo,
    outside_source_tree as _outside_source_tree,
    plugin_commit as _plugin_commit,
    run_child as _run_child,
    sha256 as _sha256,
    start_loopback_ssh as _start_loopback_ssh,
)
from wx_fresh_user_smoke import fresh_user_env, run_fresh_user_smoke

# The parent validates the child's PTY request against the disposable server
# and finalizes shutdown only after observing the child process exit.
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from hpc_gui.wx_runtime_observation import finalize_runtime_observation

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
        runtime_webview_path = _clean_room_dir("wx-webview-")
        for temp_var in ("TMP", "TEMP", "TMPDIR"):
            env[temp_var] = str(TEMP_ROOT)
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
            # Keep the disposable cwd under .tmp and outside the source tree.
            workdir = _clean_room_dir("wx-packaged-cwd-")
            details["workdir_outside_repo"] = _outside_repo(workdir)
            details["workdir_outside_source_tree"] = _outside_source_tree(workdir)
            details["workdir_under_temp_root"] = workdir.is_relative_to(ROOT / ".tmp")
            returncode, child_stdout, child_stderr, timed_out = _run_child(
                cmd,
                cwd=str(workdir),
                env={**env, "PYTHONPATH": ""},
                timeout=timeout,
            )
            shutil.rmtree(workdir, ignore_errors=True)
            # A kill is an acceptance verdict, not a reason to throw away
            # evidence: the child may already have written its runtime payload
            # and its stdout before it was killed (HPC-W04-HARNESS-025).
            # Evidence is therefore scored on BOTH paths; only `result` below
            # still forces FAIL whenever the child timed out.
            combined = (child_stdout or "") + (child_stderr or "")
            if timed_out:
                details["timeout"] = f"artifact did not exit within {timeout}s"
                details["child_killed"] = True
                details["evidence_scored_on_timeout"] = True
                if combined:
                    # Bounded tail (fresh-user convention): the last words the
                    # child managed to write are the diagnostic ones.
                    details["output_tail"] = combined[-2000:]
            else:
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
            # The packaged process can prove that it requested a resize, but
            # only the disposable server can prove the resize reached the wire.
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if any(size[0:2] == (123, 45) for size in loopback_server.resize_sizes):
                    break
                time.sleep(0.02)
            observation = runtime.get("observation", {}) if isinstance(runtime, dict) else {}
            initial_observed = next(
                (size[0:2] for size in loopback_server.pty_sizes if size[0:2] == (96, 31)),
                None,
            )
            resized_observed = next(
                (size[0:2] for size in loopback_server.resize_sizes if size[0:2] == (123, 45)),
                None,
            )
            if not runtime_output.is_file():
                details["runtime"] = "artifact wrote no packaged runtime evidence"
            elif runtime.get("error"):
                details["runtime"] = str(runtime["error"])
            src_path = str(ROOT / "src")
            isolated = src_path not in combined
            if not isolated:
                details["isolation"] = "artifact output referenced repo src path"
            if returncode != 0 and not timed_out:
                details["exit_code"] = f"artifact exit {returncode}"
            runtime = finalize_runtime_observation(
                runtime,
                pty_initial_requested=observation.get("pty_initial_requested"),
                pty_initial_observed=initial_observed,
                pty_resize_requested=observation.get("pty_resize_requested"),
                pty_resize_observed=resized_observed,
                transport_closed=observation.get("transport_closed") is True,
                cleanup_callbacks_drained=observation.get("cleanup_callbacks_drained") is True,
                frame_destroyed=observation.get("frame_destroyed") is True,
                event_loop_exited=not timed_out and returncode is not None,
                exit_code=returncode,
                timed_out=timed_out,
                mandatory_checks=REQUIRED_CHECKS,
            )
            raw_failed_critical = [
                name for name in ("pty_resize", "clean_shutdown")
                if runtime.get("checks", {}).get(name) == "FAIL"
            ]
            if raw_failed_critical:
                details["raw_runtime_failed_checks"] = raw_failed_critical
            runtime_checks = runtime.get("checks", {})
            checks["process_started"] = "PASS"
            for name in REQUIRED_CHECKS:
                if name == "process_started":
                    continue
                checks[name] = "PASS" if runtime_checks.get(name) == "PASS" else "FAIL"
            if runtime_output.is_file():
                runtime_output.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
            if resized_observed is None or initial_observed is None:
                details["pty_resize"] = {
                    "pty_sizes": loopback_server.pty_sizes,
                    "resize_sizes": loopback_server.resize_sizes,
                }.__repr__()
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Real packaged wx smoke (isolated from src)")
    parser.add_argument("--artifact", type=Path, default=None, help="Path to built wx artifact (exe, whl, or py)")
    parser.add_argument("--platform", default=None, help="Platform label (windows|linux|macos)")
    parser.add_argument("--output", type=Path, default=None, help="Output evidence JSON path")
    parser.add_argument("--fresh-user", action="store_true",
                        help="Run PKG-GJ-01 fresh-user acceptance (isolated config root, first-run, relaunch)")
    parser.add_argument("--timeout", type=int, default=None,
                        help="Seconds before the child is killed and reaped "
                             "(default: 25 packaged, 240 fresh-user)")
    args = parser.parse_args()
    timeout = args.timeout if args.timeout is not None else (240 if args.fresh_user else 25)

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
        evidence = run_fresh_user_smoke(artifact, plat, output, timeout=timeout)
    else:
        evidence = run_packaged_smoke(artifact, plat, output, timeout=timeout)
    # Machine-readable contract: stdout carries exactly the evidence JSON so
    # `json.loads(stdout)` succeeds; the human identity header goes to stderr.
    print(evidence.get("identity_header", ""), file=sys.stderr)
    print("---", file=sys.stderr)
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
