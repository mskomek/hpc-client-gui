"""Temporary W15-resume diagnostic: run the fresh-user child flow from SOURCE with
the same clean-room env so the startup traceback lands on stderr."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import wx_packaged_smoke as smoke

ENTRY = ROOT / "src" / "hpc_gui" / "__main__.py"
OUT = ROOT / "build" / "audit" / "w15-resume-src-probe.json"
RUNTIME = ROOT / "build" / "audit" / "w15-resume-src-probe.run1.runtime.json"

fresh_parent = Path(tempfile.mkdtemp(prefix="hpc-src-probe-"))
fresh_root = fresh_parent / "config"
workdir = fresh_parent / "work"
workdir.mkdir(parents=True, exist_ok=True)

loopback_root, server, user, password = smoke._start_loopback_ssh(OUT)
print(f"fixture port={server.port} user={user}", flush=True)
try:
    env = smoke.fresh_user_env(os.environ, fresh_root=fresh_root, run_index=1)
    env["HPC_GUI_PACKAGED_SMOKE_OUTPUT"] = str(RUNTIME.resolve())
    env["HPC_GUI_PACKAGED_SMOKE_SSH_HOST"] = "127.0.0.1"
    env["HPC_GUI_PACKAGED_SMOKE_SSH_PORT"] = str(server.port)
    env["HPC_GUI_PACKAGED_SMOKE_SSH_USER"] = user
    env["HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD"] = password
    env["HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS"] = str(Path(loopback_root.name) / "known_hosts")
    env["HPC_GUI_PACKAGED_SMOKE_APP_NAME"] = "hpc-src-probe"
    env["WEBVIEW2_USER_DATA_FOLDER"] = str((fresh_parent / "wv").resolve())
    env.pop("PYTHONPATH", None)
    (fresh_parent / "wv").mkdir(exist_ok=True)
    RUNTIME.unlink(missing_ok=True)
    p = subprocess.run(
        [sys.executable, str(ENTRY), "--wx-smoke"], cwd=str(workdir), env=env,
        capture_output=True, text=True, timeout=120)
    print("rc:", p.returncode)
    print("=== STDOUT ===")
    print(p.stdout[-3000:])
    print("=== STDERR ===")
    print(p.stderr[-5000:])
    print("RUNTIME:", RUNTIME.read_text(encoding="utf-8")[:1500] if RUNTIME.is_file() else "<absent>")
finally:
    try:
        server.__exit__(None, None, None)
    except Exception:
        pass
    print("fresh_parent_kept:", fresh_parent)
