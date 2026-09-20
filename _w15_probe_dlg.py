"""Temporary W15-resume diagnostic: launch frozen fresh-user child, dump the crash
dialog text via UIAutomation, then kill. Not part of the test suite."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import wx_packaged_smoke as smoke

EXE = ROOT / "dist" / "hpc-client-gui" / "hpc-client-gui.exe"
OUT = ROOT / "build" / "audit" / "w15-resume-dlg-probe.json"
RUNTIME = ROOT / "build" / "audit" / "w15-resume-dlg-probe.run1.runtime.json"

fresh_parent = Path(tempfile.mkdtemp(prefix="hpc-dlg-probe-"))
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
    env["HPC_GUI_PACKAGED_SMOKE_APP_NAME"] = "hpc-dlg-probe"
    env["WEBVIEW2_USER_DATA_FOLDER"] = str((fresh_parent / "wv").resolve())
    env.pop("PYTHONPATH", None)
    (fresh_parent / "wv").mkdir(exist_ok=True)
    RUNTIME.unlink(missing_ok=True)
    p = subprocess.Popen([str(EXE), "--wx-smoke"], cwd=str(workdir), env=env)
    print(f"child pid={p.pid}", flush=True)
    time.sleep(20)
    dump = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(ROOT / "_w15_dump_dlg.ps1")],
        capture_output=True, text=True, timeout=60)
    print("=== DIALOG DUMP ===")
    print(dump.stdout[-6000:])
    print("=== DUMP STDERR ===")
    print((dump.stderr or "")[-1000:])
    if p.poll() is None:
        p.kill()
        print("child killed")
    else:
        print("child rc:", p.returncode)
finally:
    try:
        server.__exit__(None, None, None)
    except Exception:
        pass
    print("fresh_parent_kept:", fresh_parent)
