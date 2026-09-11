"""Real packaged wx artifact smoke (requires built artifact, isolates src)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Expected checks per gate spec
REQUIRED_CHECKS = ("process_started", "wx_runtime_started", "main_frame_created", "terminal_readback", "clean_shutdown")


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


def run_packaged_smoke(artifact: Path, platform_name: str, output: Path, timeout: int = 25) -> dict:
    commit = current_commit() or "unknown"
    artifact_name = artifact.name if artifact else "missing"
    artifact_sha = _sha256(artifact) if artifact and artifact.is_file() else "0" * 64
    checks = {name: "FAIL" for name in REQUIRED_CHECKS}
    result = "FAIL"
    details: dict[str, str] = {}
    exit_code = None
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
        try:
            if artifact.suffix == ".py":
                cmd = [sys.executable, str(artifact), "--wx-smoke"]
            elif artifact.suffix == ".exe":
                cmd = [str(artifact), "--wx-smoke"]
            else:
                raise ValueError(f"unsupported artifact type: {artifact.suffix}")
            env["HPC_GUI_PACKAGED_SMOKE_OUTPUT"] = str(runtime_output.resolve())
            checks["process_started"] = "PASS"
            proc = subprocess.run(
                cmd,
                cwd=ROOT,
                env={**env, "PYTHONPATH": ""},
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = proc.returncode
            combined = (proc.stdout or "") + (proc.stderr or "")
            runtime = json.loads(runtime_output.read_text(encoding="utf-8")) if runtime_output.is_file() else {}
            runtime_checks = runtime.get("checks", {}) if isinstance(runtime, dict) else {}
            for name in ("wx_runtime_started", "main_frame_created", "terminal_readback"):
                if runtime_checks.get(name) == "PASS":
                    checks[name] = "PASS"
            if not runtime_output.is_file():
                details["runtime"] = "artifact exited without packaged runtime evidence"
            elif runtime.get("error"):
                details["runtime"] = str(runtime["error"])
            src_path = str(ROOT / "src")
            isolated = src_path not in combined
            if not isolated:
                details["isolation"] = "artifact output referenced repo src path"
            if proc.returncode != 0:
                details["exit_code"] = f"artifact exit {proc.returncode}"
            checks["clean_shutdown"] = "PASS" if proc.returncode == 0 and isolated and runtime.get("result") == "PASS" else "FAIL"
            result = "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL"
            if result == "FAIL" and combined:
                details["output_snippet"] = combined[:2000]
        except subprocess.TimeoutExpired:
            details["timeout"] = f"artifact did not exit within {timeout}s"
        except Exception as exc:
            details["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            runtime_output.unlink(missing_ok=True)

    # Build evidence JSON per spec
    evidence = {
        "schema": "wx-packaged-smoke/1",
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

    evidence = run_packaged_smoke(artifact, plat, output)
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
